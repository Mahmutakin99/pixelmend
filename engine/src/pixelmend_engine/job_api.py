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

from .assets import AssetNotFoundError
from .imageio import MAX_SOURCE_BYTES, encode_export, encode_preview_png
from .jobs import TERMINAL


def job_router(queue, assets, auth):
    router = APIRouter(dependencies=[Depends(auth)])

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
                     mask: UploadFile | None = File(None), scale: int = Form(1)):
        """Bound compressed mask input and decode against the canonical source size."""
        try:
            selected = json.loads(algorithms)
            if not isinstance(selected, list) or any(not isinstance(a, str) for a in selected):
                raise ValueError('algorithms must be a string list')
            image = assets.get_image(asset_id)
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
            job = queue.submit(asset_id, selected, canonical, scale)
        except AssetNotFoundError:
            raise HTTPException(404, 'asset not found')
        except (ValueError, UnidentifiedImageError, OSError):
            raise HTTPException(422, 'Geçersiz veya boş maske. Görselde bir alan boyayıp tekrar deneyin.')
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

        def copy_asset():
            return assets.import_image(BytesIO(encode_preview_png(image)))

        return asdict(await run_in_threadpool(copy_asset))

    return router
