"""Expose the loopback-only PixelMend sidecar HTTP boundary."""

from io import BytesIO
import re
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile, status

from .assets import AssetCapacityError, AssetInUseError, AssetNotFoundError, AssetStore
from .auth import require_session_token
from .capabilities import collect_capabilities
from .imageio import ImageIOError
from .imageio import MAX_SOURCE_BYTES
from .jobs import JobQueue
from .job_api import job_router


def create_app(*, session_token: str) -> FastAPI:
    """Create a production sidecar app with its private session asset store."""
    assets = AssetStore()
    queue = JobQueue(assets)

    @asynccontextmanager
    async def lifespan(app):
        try:
            async with queue:
                yield
        finally:
            assets.close()

    app = FastAPI(title="PixelMend Engine", docs_url=None, redoc_url=None,
                  openapi_url=None, lifespan=lifespan)
    token_dependency = require_session_token(session_token)
    app.include_router(job_router(queue, assets, token_dependency))

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

    @app.get("/capabilities")
    def capabilities(_: None = Depends(token_dependency)) -> dict[str, object]:
        """Expose observed device facts without deriving unsupported budgets."""
        return collect_capabilities().as_dict()

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
