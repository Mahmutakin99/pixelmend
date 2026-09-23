"""Expose the loopback-only PixelMend sidecar HTTP boundary."""

from io import BytesIO
import re
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile, status

from .assets import AssetCapacityError, AssetInUseError, AssetNotFoundError, AssetStore
from .auth import require_session_token
from .capabilities import collect_capabilities
from .imageio import ImageIOError, ImageAsset
from .strokes import StrokeValidationError, render_paint
from .imageio import MAX_SOURCE_BYTES
from .jobs import JobQueue
from .job_api import job_router
from .model_api import model_router
from .model_manager import ModelManager
from .paths import get_models_dir, get_coreml_cache_dir, cleanup_stale_sessions, create_session_dir
from .policy import POLICY


def create_app(*, session_token: str, diagnostics: bool = False) -> FastAPI:
    """Create a production sidecar app with its private session asset store."""
    assets = AssetStore()
    manager = ModelManager(get_models_dir(), prober=_probe_model)
    queue = JobQueue(assets, model_manager=manager)
    session_dir = None

    @asynccontextmanager
    async def lifespan(app):
        nonlocal session_dir
        try:
            cleanup_stale_sessions()
            session_dir = create_session_dir()
            await manager.start()
            async with queue:
                yield
        finally:
            await manager.close()
            assets.close()
            if session_dir is not None:
                import shutil
                shutil.rmtree(session_dir, ignore_errors=True)

    app = FastAPI(title="PixelMend Engine", docs_url=None, redoc_url=None,
                  openapi_url=None, lifespan=lifespan)
    token_dependency = require_session_token(session_token)
    app.include_router(job_router(queue, assets, token_dependency))
    app.include_router(model_router(manager, token_dependency))
    if diagnostics:
        from .diagnostics import diagnostic_router
        app.include_router(diagnostic_router(queue, assets, token_dependency))

    @app.middleware('http')
    async def validate_request_boundary(request, call_next):
        """Reject browser origins and DNS rebinding before parsing any payload."""
        host = request.headers.get('host', '')
        if 'origin' in request.headers or not re.fullmatch(
            r'(127\.0\.0\.1|localhost)(:[0-9]{1,5})?', host
        ):
            return Response(status_code=403)
        return await call_next(request)

    @app.get("/health")
    def health(_: None = Depends(token_dependency)) -> dict[str, str]:
        """Confirm the authenticated sidecar is ready to accept requests."""
        return {"status": "ok"}

    @app.post('/shutdown')
    async def shutdown(_: None = Depends(token_dependency)):
        callback = getattr(app.state, 'request_shutdown', None)
        if callback is None:
            raise HTTPException(503, 'Server shutdown hook unavailable')
        callback()
        return {'status': 'stopping'}

    @app.get("/capabilities")
    def capabilities(_: None = Depends(token_dependency)) -> dict[str, object]:
        """Expose observed device facts without deriving unsupported budgets."""
        report = collect_capabilities().as_dict()
        report['policy'] = POLICY.as_dict()
        return report

    @app.post("/assets", status_code=status.HTTP_201_CREATED)
    async def import_asset(
        image: UploadFile = File(...),
        _: None = Depends(token_dependency),
    ) -> dict[str, object]:
        """Normalize an uploaded image once without retaining its client filename."""
        try:
            raw = await image.read(MAX_SOURCE_BYTES + 1)
            if len(raw) > MAX_SOURCE_BYTES:
                raise HTTPException(413, 'image too large')
            imported = await run_in_threadpool(assets.import_image, BytesIO(raw))
        except ImageIOError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
        except AssetCapacityError:
            raise HTTPException(507, 'asset capacity exceeded')
        finally:
            await image.close()
        return {
            "asset_id": imported.asset_id,
            "width": imported.width,
            "height": imported.height,
            "warnings": list(imported.warnings),
        }

    @app.get("/assets/{asset_id}/preview")
    def get_asset_preview(
        asset_id: str,
        _: None = Depends(token_dependency),
    ) -> Response:
        """Return only a normalized PNG preview for an existing opaque asset id."""
        try:
            preview = assets.preview_bytes(asset_id)
        except AssetNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="asset not found") from error
        return Response(content=preview, media_type="image/png")

    @app.get('/assets/{asset_id}/export')
    def export_asset(asset_id: str, format: str = 'PNG', _: None = Depends(token_dependency)) -> Response:
        """Stream full normalized pixels for native save without a renderer canvas."""
        from .imageio import encode_export
        if format not in {'PNG', 'JPEG', 'WEBP', 'TIFF'}:
            raise HTTPException(422, 'unsupported format')
        try:
            return Response(encode_export(assets.get_image(asset_id), format), media_type=f'image/{format.lower()}')
        except AssetNotFoundError as error:
            raise HTTPException(404, 'asset not found') from error

    @app.post('/assets/{asset_id}/rendered', status_code=status.HTTP_201_CREATED)
    async def render_asset(asset_id: str, payload: dict, _: None = Depends(token_dependency)) -> dict[str, object]:
        """Create an opaque session asset by rendering paint vectors at native resolution."""
        try:
            source = assets.get_image(asset_id)
            strokes = payload.get('paint_strokes')
            if not isinstance(strokes, list):
                raise StrokeValidationError('paint_strokes must be a list')
            rgb = await run_in_threadpool(render_paint, source.rgb, strokes)
            # A rendered result is an opaque edit layer baked into normalized source pixels.
            imported = await run_in_threadpool(assets.adopt_image, ImageAsset(
                rgb=rgb, alpha=source.alpha, metadata=source.metadata, warnings=source.warnings))
        except AssetNotFoundError as error:
            raise HTTPException(404, 'asset not found') from error
        except AssetCapacityError:
            raise HTTPException(507, 'Düzenleme belleği dolu. Kullanılmayan görselleri kapatın.')
        except StrokeValidationError as error:
            raise HTTPException(422, str(error)) from error
        return {'asset_id': imported.asset_id, 'width': imported.width, 'height': imported.height,
                'warnings': list(imported.warnings)}

    @app.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_asset(
        asset_id: str,
        _: None = Depends(token_dependency),
    ) -> Response:
        """Dispose one idle session asset without accepting filesystem paths."""
        try:
            assets.delete(asset_id)
        except AssetInUseError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="asset is in use") from error
        except AssetNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="asset not found") from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


def _probe_model(manifest, path):
    """Run a real session before advertising a downloaded model as usable."""
    import time
    import numpy as np
    import onnxruntime as ort
    from .models.lama_onnx import LamaInpaint
    from .models.migan_onnx import MIGANInpaint
    from .models.realesrgan_onnx import RealESRGANUpscale

    from .execution_profile import provider_candidates, runtime_providers, select_fastest, provider_is_active
    candidates = provider_candidates(tuple(ort.get_available_providers()), get_coreml_cache_dir() / manifest.revision)
    timings = []
    execution = {}
    for candidate in candidates:
        provider = candidate[0] if isinstance(candidate, tuple) else candidate
        try:
            if manifest.model_id in {'realesrgan-x4plus', 'realesrgan-general-x4v3'}:
                adapter = RealESRGANUpscale(path, providers=runtime_providers(provider, get_coreml_cache_dir() / manifest.revision))
                if not provider_is_active(adapter.session.get_providers(), provider):
                    raise ValueError('requested provider was not activated')
                probe_pixels = np.zeros((144, 144, 3), dtype=np.uint8)
                value = adapter.run(probe_pixels)
                if value.shape != (576, 576, 3):
                    raise ValueError('unexpected upscale output')
            elif manifest.model_id == 'lama':
                adapter = LamaInpaint(model_path=path, providers=runtime_providers(provider, get_coreml_cache_dir() / manifest.revision))
                if not provider_is_active(adapter.session.get_providers(), provider):
                    raise ValueError('requested provider was not activated')
                value = adapter.run(np.zeros((16, 16, 3), dtype=np.uint8), np.pad(np.full((2, 2), 255, np.uint8), 7))
                if value.shape != (16, 16, 3):
                    raise ValueError('unexpected inpaint output')
            elif manifest.model_id == 'migan-512-places2':
                adapter = MIGANInpaint(model_path=path, providers=runtime_providers(provider, get_coreml_cache_dir() / manifest.revision))
                if not provider_is_active(adapter.session.get_providers(), provider):
                    raise ValueError('requested provider was not activated')
                probe_pixels = np.zeros((64, 64, 3), dtype=np.uint8)
                probe_mask = np.zeros((64, 64), dtype=np.uint8)
                probe_mask[24:40, 24:40] = 255
                value = adapter.run(probe_pixels, probe_mask)
                if value.shape != (64, 64, 3) or not np.array_equal(value[probe_mask == 0], probe_pixels[probe_mask == 0]):
                    raise ValueError('unexpected MI-GAN output')
            else:
                continue
            evidence = adapter.evidence.value
            if provider not in evidence.get('providers', {}):
                raise ValueError('requested provider did not execute profiled nodes')
            execution[provider] = evidence
            # Ignore compilation and graph capture cost when selecting a provider.
            # The durable Core ML cache makes the first run a poor steady-state signal.
            started = time.monotonic()
            if manifest.model_id in {'realesrgan-x4plus', 'realesrgan-general-x4v3'}:
                adapter.run(probe_pixels)
            elif manifest.model_id == 'migan-512-places2':
                adapter.run(probe_pixels, probe_mask)
            else:
                adapter.run(np.zeros((16, 16, 3), dtype=np.uint8), np.pad(np.full((2, 2), 255, np.uint8), 7))
            timings.append((time.monotonic() - started, provider))
        except Exception:
            continue
    if not timings:
        raise ValueError('no usable provider')
    return {'selected_provider': select_fastest(timings), 'providers': [p for _, p in timings], 'execution': execution}
