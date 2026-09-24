"""Authenticated job transport; no filesystem paths cross this boundary."""

import asyncio
from dataclasses import asdict
from io import BytesIO
import json

import numpy as np
from PIL import Image, UnidentifiedImageError
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from starlette.concurrency import run_in_threadpool

from .assets import AssetNotFoundError, AssetCapacityError
from .imageio import MAX_SOURCE_BYTES, encode_export, encode_preview_png
from .strokes import StrokeValidationError, rasterize_selection
from .jobs import TERMINAL
from .policy import ResourceLimitError, admit_image_job, inference_settings
from .model_manager import ModelManagerError
from .model_catalog import AI_MODELS, UPSCALE_MODELS, DEFAULT_MODEL_CATALOG


def job_router(queue, assets, auth):
    router = APIRouter(dependencies=[Depends(auth)])

    @router.get('/jobs/preflight')
    async def preflight(asset_id: str, model_id: str, intent: str = 'resize',
                        target_width: int | None = None, target_height: int | None = None,
                        resource_mode: str = 'automatic'):
        """Advisory admission; submit repeats all mutable checks before work starts."""
        try:
            image = assets.get_image(asset_id)
        except AssetNotFoundError:
            raise HTTPException(404, 'asset not found') from None
        entry = next((item for item in DEFAULT_MODEL_CATALOG if item.id == model_id), None)
        if entry is None:
            raise HTTPException(404, 'model not found')
        if intent not in {'resize', 'preserve_size'} or resource_mode not in {'automatic', 'low-resource'}:
            raise HTTPException(422, 'invalid job intent or resource mode')
        if entry.operation == 'remove':
            if intent != 'resize' or target_width is not None or target_height is not None:
                raise HTTPException(422, 'removal uses source dimensions')
            target = (image.width, image.height)
        elif intent == 'preserve_size':
            target = (image.width, image.height)
        else:
            if target_width is None or target_height is None:
                raise HTTPException(422, 'target dimensions required')
            target = (target_width, target_height)
        inference_settings(resource_mode)
        view = next(item for item in queue.model_manager.list_models()['models'] if item['id'] == model_id)
        reason = None
        if not view['published']:
            reason = {'code': 'unpublished', 'message': 'Model kalite ve kaynak kabulünü henüz geçmedi.'}
        elif view['state'] == 'absent':
            reason = {'code': 'model_absent', 'message': 'Model kurulmalı ve gerçek işlemle sınanmalı.'}
        elif view['state'] != 'ready':
            reason = view['error'] or {'code': 'model_not_ready', 'message': f"Model durumu: {view['state']}"}
        resource_reason = None
        try:
            if entry.operation == 'upscale':
                admit_image_job(image, target, ai=True,
                    result_bytes=sum(job.result_bytes for job in queue.jobs.values()))
        except ResourceLimitError as error:
            resource_reason = {'code': error.code, 'message': str(error)}
            reason = reason or resource_reason
        return {'model_id': model_id, 'revision': view['revision'], 'ready': reason is None,
                'reason': reason, 'resource_reason': resource_reason,
                'installation_available': view['published'],
                'state': view['state'], 'provider': (view['probe'] or {}).get('selected_provider'),
                'input_width': image.width, 'input_height': image.height,
                'output_width': target[0], 'output_height': target[1]}

    def lookup(job_id):
        try:
            return queue.get(job_id)
        except KeyError:
            raise HTTPException(404, 'job not found')

    def result(job_id, result_id):
        try:
            return lookup(job_id).results[result_id]
        except KeyError:
            raise HTTPException(404, 'result not found')

    @router.post('/jobs', status_code=201)
    async def submit(asset_id: str = Form(...), algorithms: str = Form(...),
                     mask: UploadFile | None = File(None), selection_strokes: str | None = Form(None), scale: int = Form(1),
                     target_width: int | None = Form(None), target_height: int | None = Form(None),
                     model_id: str | None = Form(None), intent: str = Form('resize'),
                     resource_mode: str = Form('automatic')):
        """Bound compressed mask input and decode against the canonical source size."""
        try:
            selected = json.loads(algorithms)
            if not isinstance(selected, list) or any(not isinstance(a, str) for a in selected):
                raise ValueError('algorithms must be a string list')
            image = assets.get_image(asset_id)
            if intent not in {'resize', 'preserve_size'}:
                raise ValueError('invalid intent')
            if model_id is not None and (len(selected) != 1 or AI_MODELS.get(selected[0]) != model_id):
                raise ValueError('model does not match algorithm')
            if intent == 'preserve_size':
                if len(selected) != 1 or selected[0] not in UPSCALE_MODELS:
                    raise ValueError('preserve size requires AI enhancement')
                target_width, target_height = image.width, image.height
            if mask and selection_strokes:
                raise ValueError('choose either a mask or selection strokes')
            raw = await mask.read(MAX_SOURCE_BYTES + 1) if mask else b''
            if len(raw) > MAX_SOURCE_BYTES:
                raise HTTPException(413, 'mask too large')

            def decode():
                with Image.open(BytesIO(raw), formats=['PNG']) as decoded:
                    if decoded.size != (image.width, image.height):
                        raise ValueError('mask dimensions must match the source')
                    # Browser canvases export RGBA. Alpha denotes coverage even
                    # for black strokes or erased pixels with residual RGB data.
                    if decoded.mode in {'RGBA', 'LA'}:
                        coverage = np.asarray(decoded.getchannel('A'))
                    elif decoded.mode in {'1', 'L'}:
                        coverage = np.asarray(decoded.convert('L'))
                    else:
                        raise ValueError('mask must be grayscale or have alpha')
                    return np.where(coverage >= 128, 255, 0).astype(np.uint8)

            canonical = await run_in_threadpool(decode) if mask else None
            if selection_strokes is not None:
                canonical = await run_in_threadpool(
                    rasterize_selection, json.loads(selection_strokes), image.width, image.height)
            job = queue.submit(asset_id, selected, canonical, scale, target_width, target_height, resource_mode)
        except AssetNotFoundError:
            raise HTTPException(404, 'asset not found')
        except ModelManagerError as error:
            raise HTTPException(error.status_code, {'code': error.code, 'message': str(error)}) from error
        except ResourceLimitError as error:
            raise HTTPException(422, str(error)) from error
        except (ValueError, StrokeValidationError, UnidentifiedImageError, OSError):
            raise HTTPException(422, 'İşlem, model, maske veya çıktı ölçüsü geçersiz.')
        finally:
            if mask:
                await mask.close()
        return {'job_id': job.job_id}

    @router.get('/jobs/{job_id}')
    async def status(job_id: str):
        return lookup(job_id).snapshot()

    @router.post('/jobs/{job_id}/cancel')
    async def cancel(job_id: str):
        lookup(job_id)
        return queue.cancel(job_id).snapshot()

    @router.delete('/jobs/{job_id}', status_code=204)
    async def delete(job_id: str):
        lookup(job_id)
        try:
            queue.delete(job_id)
        except ValueError:
            raise HTTPException(409, 'job is still active')
        return Response(status_code=204)

    @router.get('/jobs/{job_id}/events')
    async def events(job_id: str, last_event_id: int = Header(0)):
        job = lookup(job_id)
        if last_event_id < 0 or last_event_id > len(job.events):
            raise HTTPException(409, 'refresh job snapshot')

        async def stream():
            cursor = last_event_id
            ticks = 0
            while True:
                for event in job.events[cursor:]:
                    cursor = event['id']
                    yield f"id: {cursor}\nevent: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"
                if job.status in TERMINAL:
                    return
                if ticks % 50 == 0:
                    yield ': heartbeat\n\n'
                ticks += 1
                await asyncio.sleep(.1)

        return StreamingResponse(stream(), media_type='text/event-stream',
                                 headers={'Cache-Control': 'no-store'})

    @router.get('/jobs/{job_id}/results/{result_id}')
    async def read_result(job_id: str, result_id: str, format: str = 'PNG'):
        image = result(job_id, result_id)
        if format not in {'PNG', 'JPEG', 'WEBP', 'TIFF'}:
            raise HTTPException(422, 'unsupported format')
        data = await run_in_threadpool(encode_export, image, format)
        return Response(data, media_type=f'image/{format.lower()}')

    @router.post('/jobs/{job_id}/results/{result_id}/asset', status_code=201)
    async def continue_editing(job_id: str, result_id: str):
        image = result(job_id, result_id)

        try:
            return asdict(await run_in_threadpool(assets.adopt_image, image))
        except AssetCapacityError:
            raise HTTPException(507, 'Düzenleme belleği dolu. Kullanılmayan görselleri kapatın.')

    return router
