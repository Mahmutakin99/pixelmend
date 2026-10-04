"""Authenticated, discriminated generative requests; existing jobs carry results."""
import json

from fastapi import APIRouter,Depends,HTTPException,Request
from starlette.concurrency import run_in_threadpool

from .assets import AssetNotFoundError
from .generative_process import RuntimeErrorCode,_unique
from .generative_service import GenerativeRequest
from .model_manager import ModelManagerError

MAX_REQUEST=16*1024**2


def _invalid_constant(_):raise ValueError()


async def parse_request(request):
    raw=bytearray()
    async for chunk in request.stream():
        if len(raw)+len(chunk)>MAX_REQUEST:raise HTTPException(413,'Üretim isteği çok büyük.')
        raw.extend(chunk)
    try:
        return GenerativeRequest.parse(json.loads(raw,object_pairs_hook=_unique,parse_constant=_invalid_constant))
    except RuntimeErrorCode as error:
        raise HTTPException(422,{'code':error.code,'message':str(error)}) from None
    except (ValueError,UnicodeError,TypeError):
        error=RuntimeErrorCode('invalid_request')
        raise HTTPException(422,{'code':error.code,'message':str(error)}) from None


def generative_router(queue,service,auth):
    router=APIRouter(prefix='/generative',dependencies=[Depends(auth)])
    @router.post('/preflight')
    async def preflight(request:Request):
        parsed=await parse_request(request)
        try:
            return await run_in_threadpool(service.preflight,parsed,
                result_bytes=sum(job.result_bytes for job in queue.jobs.values()),result_budget=queue.result_budget)
        except AssetNotFoundError:raise HTTPException(404,'Kaynak görsel bulunamadı.') from None
    @router.post('/jobs',status_code=201)
    async def submit(request:Request):
        parsed=await parse_request(request)
        try:
            await run_in_threadpool(service.ensure_ready,parsed,
                result_bytes=sum(job.result_bytes for job in queue.jobs.values()),result_budget=queue.result_budget)
            return queue.submit_generative(parsed).snapshot()
        except AssetNotFoundError:raise HTTPException(404,'Kaynak görsel bulunamadı.') from None
        except ModelManagerError as error:
            raise HTTPException(error.status_code,{'code':error.code,'message':str(error)}) from None
        except ValueError:raise HTTPException(409,'İş kuyruğu dolu. Önceki sonuçları kapatın.') from None
    return router
