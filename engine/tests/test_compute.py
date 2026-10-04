from concurrent.futures import ThreadPoolExecutor
import threading
import time

import pytest

from pixelmend_engine.compute import ComputeCoordinator


def test_heavy_work_serializes_and_queued_user_job_blocks_new_probe():
    coordinator=ComputeCoordinator();first_started=threading.Event();release=threading.Event()
    order=[];active=[0];maximum=[0];mutex=threading.Lock()
    def work(label,kind,blocking=False):
        with coordinator.operation(kind):
            with mutex:active[0]+=1;maximum[0]=max(maximum[0],active[0]);order.append(label)
            if blocking:first_started.set();assert release.wait(2)
            time.sleep(.01)
            with mutex:active[0]-=1
    with ThreadPoolExecutor(3) as threads:
        first=threads.submit(work,'running-probe','probe',True);assert first_started.wait(2)
        ticket=coordinator.reserve_job()
        probe=threads.submit(work,'new-probe','probe')
        job=threads.submit(work,'user-job','job')
        release.set();first.result(2);job.result(2)
        assert not probe.done()
        ticket.release();probe.result(2)
    assert maximum==[1]
    assert order==['running-probe','user-job','new-probe']
    assert coordinator.pending_jobs==0


def test_cancelled_waiter_never_owns_compute_slot():
    coordinator=ComputeCoordinator();cancel=threading.Event();entered=threading.Event()
    with coordinator.operation('job'):
        def wait():
            entered.set()
            with coordinator.operation('probe',cancel):pytest.fail('cancelled waiter acquired')
        with ThreadPoolExecutor(1) as executor:
            task=executor.submit(wait);assert entered.wait(1);cancel.set()
            with pytest.raises(InterruptedError):task.result(1)
    with coordinator.operation('job'):pass


def test_job_ticket_is_idempotent():
    coordinator=ComputeCoordinator();ticket=coordinator.reserve_job()
    ticket.release();ticket.release()
    assert coordinator.pending_jobs==0


def test_onnx_lifecycle_and_existing_job_queue_share_the_compute_slot(tmp_path):
    import asyncio,hashlib
    from io import BytesIO
    import numpy as np
    from PIL import Image
    from pixelmend_engine.assets import AssetStore
    from pixelmend_engine.jobs import JobQueue
    from pixelmend_engine.model_manager import ModelManager
    from pixelmend_engine.model_catalog import ModelCatalogEntry
    from pixelmend_engine.model_store import ModelManifest
    async def scenario():
        coordinator=ComputeCoordinator();started=threading.Event();release=threading.Event()
        job_started=threading.Event();release_job=threading.Event();second_started=threading.Event();order=[]
        entries=[ModelCatalogEntry(id,id,ModelManifest(id,'owner/repo','a'*40,'model.onnx',1,
            hashlib.sha256(b'x').hexdigest(),'Apache-2.0','https://example.test')) for id in ['first','second']]
        def probe(manifest,path):
            order.append(manifest.model_id)
            if manifest.model_id=='first':started.set();assert release.wait(3)
            else:second_started.set()
            return {'selected_provider':'CPUExecutionProvider','providers':['CPUExecutionProvider']}
        def processor(image,*_):
            order.append('job');job_started.set();assert release_job.wait(3);return image
        manager=ModelManager(tmp_path,catalog=entries,prober=probe,
            downloader=lambda m,path,*_:path.write_bytes(b'x'),coordinator=coordinator)
        await manager.start();await manager.install('first');assert await asyncio.to_thread(started.wait,2)
        store=AssetStore();png=BytesIO();Image.new('RGB',(9,9)).save(png,format='PNG');asset=store.import_image(png).asset_id
        try:
            async with JobQueue(store,processor=processor,model_manager=manager,coordinator=coordinator) as jobs:
                job=jobs.submit(asset,['opencv_telea'],np.full((9,9),255,np.uint8))
                await manager.install('second');release.set()
                assert await asyncio.to_thread(job_started.wait,2)
                assert order==['first','job']
                release_job.set();await jobs.join();assert job.status=='completed'
            assert await asyncio.to_thread(second_started.wait,2)
            await manager.close();assert order==['first','job','second']
            assert coordinator.pending_jobs==0
        finally:release.set();release_job.set();await manager.close()
    asyncio.run(scenario())
