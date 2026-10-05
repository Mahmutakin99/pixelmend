import json,time
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from pixelmend_engine.generative_api import generative_router
from pixelmend_engine.job_api import job_router
from pixelmend_engine.auth import require_session_token
from pixelmend_engine.jobs import JobQueue
from test_generative_service import fixtures,payload

TOKEN='a'*64


def test_authenticated_generation_routes_reuse_job_results_and_never_accept_paths(tmp_path):
    from contextlib import asynccontextmanager
    service,manager,owner,assets,host,coordinator=fixtures(tmp_path)
    queue=JobQueue(assets,generative_service=service,coordinator=coordinator)
    @asynccontextmanager
    async def life(app):
        await manager.start()
        async with queue:yield
        await manager.close()
    app=FastAPI(lifespan=life);auth=require_session_token(TOKEN)
    app.include_router(generative_router(queue,service,auth));app.include_router(job_router(queue,assets,auth))
    with TestClient(app) as client:
        assert client.post('/generative/jobs',json=payload()).status_code==401
        headers={'X-PixelMend-Token':TOKEN}
        assert client.post('/generative/preflight',headers=headers,json=payload()).json()['ready']
        bad=client.post('/generative/jobs',headers=headers,json=payload(model_dir='/private/model'))
        assert bad.status_code==422 and '/private' not in bad.text
        posted=client.post('/generative/jobs',headers=headers,json=payload())
        assert posted.status_code==201,posted.text
        id=posted.json()['job_id']
        for _ in range(100):
            state=client.get('/jobs/'+id,headers=headers).json()
            if state['status'] in {'completed','failed','cancelled'}:break
            time.sleep(.01)
        assert state['status']=='completed'
        result=state['result_ids'][0]
        assert client.get(f'/jobs/{id}/results/{result}',headers=headers).headers['content-type']=='image/png'
        adopted=client.post(f'/jobs/{id}/results/{result}/asset',headers=headers)
        assert adopted.status_code==201
        assert client.delete('/jobs/'+id,headers=headers).status_code==204
        assert queue.jobs=={}


@pytest.mark.parametrize('body',[
 b'{"operation":"text_to_image","operation":"text_edit"}',
 b'[]',b'{"prompt":NaN}',b'{"operation":"text_to_image","prompt":"\\ud800","profile":"low-resource"}',
])
def test_malformed_json_and_unicode_are_rejected_without_content(tmp_path,body):
    service,manager,owner,assets,host,coordinator=fixtures(tmp_path)
    app=FastAPI();app.include_router(generative_router(JobQueue(assets,generative_service=service),service,require_session_token(TOKEN)))
    with TestClient(app) as client:
        response=client.post('/generative/preflight',headers={'X-PixelMend-Token':TOKEN,'Content-Type':'application/json'},content=body)
        assert response.status_code==422
        assert owner.requests==[]

def test_memory_query_skips_selection_work_but_job_admission_keeps_it(tmp_path):
    from io import BytesIO
    from PIL import Image
    service,manager,owner,assets,host,_=fixtures(tmp_path)
    buffer=BytesIO();Image.new('RGB',(512,512)).save(buffer,format='PNG');buffer.seek(0)
    from pixelmend_engine.imageio import load_image
    asset=assets.adopt_image(load_image(buffer))
    edit=payload(operation='text_edit',asset_id=asset.asset_id,selection_strokes=[],paint_strokes=[])
    edit.pop('aspect')
    queue=JobQueue(assets,generative_service=service)
    app=FastAPI();app.include_router(generative_router(queue,service,require_session_token(TOKEN)))
    with TestClient(app) as client:
        headers={'X-PixelMend-Token':TOKEN}
        report=client.post('/generative/memory',headers=headers,json=edit)
        assert report.status_code==200 and report.json()['ready']
        full=client.post('/generative/preflight',headers=headers,json=edit)
        assert not full.json()['ready'] and full.json()['reason']['code']=='selection_empty'
        job=client.post('/generative/jobs',headers=headers,json=edit)
        assert job.status_code!=201
        assert owner.requests==[]
