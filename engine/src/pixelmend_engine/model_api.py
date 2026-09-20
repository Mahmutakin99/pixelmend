"""Authenticated model snapshots, lifecycle actions and coalesced state events."""

import json

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse

from .model_manager import ModelManagerError


def model_router(manager, auth):
    router = APIRouter(prefix='/models', dependencies=[Depends(auth)])

    @router.get('')
    async def models():
        return manager.list_models()

    @router.get('/events')
    async def events():
        async def stream():
            async for snapshot in manager.events():
                if snapshot is None:
                    yield ': heartbeat\n\n'
                else:
                    yield f'event: models\ndata: {json.dumps(snapshot)}\n\n'
        return StreamingResponse(stream(), media_type='text/event-stream',
                                 headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})

    @router.post('/{model_id}/{action}')
    async def mutate(model_id: str, action: str, payload: dict | None = Body(default=None)):
        if action not in {'install', 'install-local', 'cancel', 'retry', 'probe'}:
            raise HTTPException(404, 'Unknown model action.')
        try:
            if action == 'install-local':
                if not payload or not isinstance(payload.get('path'), str):
                    raise HTTPException(422, 'Local file selection is required.')
                return await manager.install_local(model_id, payload['path'])
            return await getattr(manager, action)(model_id)
        except ModelManagerError as error:
            raise HTTPException(error.status_code, {'code': error.code, 'message': str(error)}) from None

    @router.delete('/{model_id}')
    async def delete(model_id: str):
        try:
            return await manager.delete(model_id)
        except ModelManagerError as error:
            raise HTTPException(error.status_code, {'code': error.code, 'message': str(error)}) from None

    return router
