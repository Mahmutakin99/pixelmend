import asyncio
from io import BytesIO
from threading import Event

import numpy as np
from PIL import Image
import pytest

from pixelmend_engine.assets import AssetStore, AssetInUseError


def test_inpaint_boundary_restores_unselected_rgb_and_preserves_alpha(monkeypatch):
    from pixelmend_engine.imageio import ImageAsset
    from pixelmend_engine.jobs import process
    import pixelmend_engine.jobs as jobs

    class DirtyAdapter:
        def __init__(self, method):
            pass

        def run(self, rgb, mask):
            return np.full_like(rgb, 17)

    monkeypatch.setattr(jobs, 'OpenCVInpaint', DirtyAdapter)
    rgb = np.arange(6 * 7 * 3, dtype=np.uint8).reshape(6, 7, 3)
    alpha = np.arange(6 * 7, dtype=np.uint8).reshape(6, 7)
    mask = np.zeros((6, 7), np.uint8); mask[0, 0] = 255
    image = ImageAsset(rgb, alpha, None, ())
    output = process(image, mask, 'opencv_telea', 1)
    np.testing.assert_array_equal(output.rgb[mask == 0], rgb[mask == 0])
    np.testing.assert_array_equal(output.alpha, alpha)
    assert output.rgb[0, 0].tolist() == [17, 17, 17]


def source(store):
    data = BytesIO()
    Image.new('RGB', (9, 9), 'white').save(data, format='PNG')
    return store.import_image(data).asset_id


def test_real_inpaint_result_replay_and_source_release():
    from pixelmend_engine.jobs import JobQueue

    async def scenario():
        store = AssetStore()
        asset_id = source(store)
        mask = np.zeros((9, 9), dtype=np.uint8)
        mask[4, 4] = 255
        async with JobQueue(store) as queue:
            job = queue.submit(asset_id, ['opencv_telea', 'opencv_ns'], mask)
            await queue.join()
            assert job.status == 'completed'
            assert len(job.results) == 2
            events = queue.events_after(job.job_id, 0)
            assert [e['event'] for e in events].count('completed') == 1
            assert len([e for e in events if e['event'] == 'result']) == 2
            assert queue.events_after(job.job_id, events[-1]['id']) == []
            store.delete(asset_id)
            queue.delete(job.job_id)
            with pytest.raises(KeyError):
                queue.get(job.job_id)
    asyncio.run(scenario())


def test_cancel_native_work_retains_source_until_return_and_drops_late_result():
    from pixelmend_engine.jobs import JobQueue

    started, release = Event(), Event()

    def slow(image, mask, algorithm, scale):
        started.set()
        assert release.wait(3)
        return image

    async def scenario():
        store = AssetStore()
        asset_id = source(store)
        async with JobQueue(store, processor=slow) as queue:
            job = queue.submit(asset_id, ['opencv_telea'], np.full((9, 9), 255, np.uint8))
            assert await asyncio.to_thread(started.wait, 2)
            queue.cancel(job.job_id)
            queue.cancel(job.job_id)
            with pytest.raises(AssetInUseError):
                store.delete(asset_id)
            release.set()
            await queue.join()
            assert job.status == 'cancelled'
            assert job.results == {}
            assert [e['event'] for e in job.events].count('cancelled') == 1
            store.delete(asset_id)
    try:
        asyncio.run(scenario())
    finally:
        release.set()


def test_lanczos_job_has_scaled_dimensions_and_rejects_mixed_tasks():
    from pixelmend_engine.jobs import JobQueue

    async def scenario():
        store = AssetStore()
        asset_id = source(store)
        async with JobQueue(store) as queue:
            with pytest.raises(ValueError):
                queue.submit(asset_id, ['lanczos', 'opencv_telea'], scale=2)
            job = queue.submit(asset_id, ['lanczos'], scale=2)
            await queue.join()
            assert job.status == 'completed'
            image = next(iter(job.results.values()))
            assert (image.width, image.height) == (18, 18)
    asyncio.run(scenario())


def test_lanczos_accepts_explicit_safe_output_dimensions():
    from pixelmend_engine.jobs import JobQueue

    async def scenario():
        store = AssetStore()
        asset_id = source(store)
        async with JobQueue(store) as queue:
            job = queue.submit(asset_id, ['lanczos'], target_width=15, target_height=12)
            await queue.join()
            assert job.status == 'completed'
            image = next(iter(job.results.values()))
            assert (image.width, image.height) == (15, 12)
            with pytest.raises(ValueError):
                queue.submit(asset_id, ['lanczos'], target_width=20000, target_height=10001)
            with pytest.raises(ValueError):
                queue.submit(asset_id, ['lanczos'], target_width=15)
    asyncio.run(scenario())


def test_missing_model_failure_is_explained_in_polling_snapshot():
    from pixelmend_engine.jobs import JobQueue
    from pixelmend_engine.model_store import ModelFileMissingError
    from pathlib import Path

    def missing(*args):
        raise ModelFileMissingError(Path('/private/not-for-renderer/model.onnx'))

    async def scenario():
        store = AssetStore()
        asset_id = source(store)
        async with JobQueue(store, processor=missing) as queue:
            job = queue.submit(asset_id, ['opencv_telea'], np.full((9, 9), 255, np.uint8))
            await queue.join()
            state = job.snapshot()
            assert state['status'] == 'failed'
            assert state['error']['code'] == 'model_missing'
            assert 'LaMa' in state['error']['message']
            assert '/private' not in str(state)
    asyncio.run(scenario())


def test_lama_without_manager_is_rejected_before_queueing():
    from pixelmend_engine.jobs import JobQueue
    from pixelmend_engine.model_manager import ModelManagerError
    async def scenario():
        store = AssetStore()
        asset_id = source(store)
        async with JobQueue(store) as queue:
            with pytest.raises(ModelManagerError, match='ready'):
                queue.submit(asset_id, ['lama'], np.full((9, 9), 255, np.uint8))
            assert not queue.jobs
            store.delete(asset_id)
    asyncio.run(scenario())


def test_lama_lease_pins_selected_path_until_cancelled_native_call_finishes(tmp_path):
    from dataclasses import replace
    from pixelmend_engine.jobs import JobQueue
    from pixelmend_engine.model_manager import ModelManager, ModelManagerError
    from pixelmend_engine.model_catalog import ModelCatalogEntry
    from test_model_manager import fixture_entry, download, probe, settle
    original = fixture_entry()
    entry = ModelCatalogEntry('lama','LaMa fixture',replace(original.manifest,model_id='lama'))
    started, release = Event(), Event()
    def slow(image, mask, algorithm, scale):
        assert algorithm == 'lama'
        started.set()
        assert release.wait(5)
        return image
    async def scenario():
        manager=ModelManager(tmp_path,catalog=[entry],downloader=download,prober=probe)
        await manager.install('lama');assert await settle(manager)=='ready'
        store=AssetStore();asset_id=source(store)
        try:
            async with JobQueue(store,processor=slow,model_manager=manager) as queue:
                job=queue.submit(asset_id,['lama'],np.full((9,9),255,np.uint8))
                assert job.model_path.parent.name==entry.manifest.revision
                assert job.provider=='CPUExecutionProvider'
                assert await asyncio.to_thread(started.wait,2)
                queue.cancel(job.job_id)
                with pytest.raises(ModelManagerError,match='in use'): await manager.delete('lama')
                release.set();await queue.join()
                assert job.status=='cancelled' and not job.results
                assert manager.list_models()['models'][0]['in_use']==0
                state=job.snapshot()
                assert state['model_revision']==entry.manifest.revision
                assert state['provider']=='CPUExecutionProvider'
                assert job.events[0]['data']['algorithms']==['lama']
        finally:
            release.set();await manager.close()
    asyncio.run(scenario())


def test_idle_worker_drops_finished_job_and_pixels():
    import gc, weakref
    from pixelmend_engine.jobs import JobQueue
    async def scenario():
        store = AssetStore()
        asset_id = source(store)
        async with JobQueue(store) as queue:
            job = queue.submit(asset_id, ['lanczos'], scale=2)
            await queue.join()
            refs = [weakref.ref(job), weakref.ref(store.get_image(asset_id).rgb), weakref.ref(next(iter(job.results.values())).rgb)]
            queue.delete(job.job_id); store.delete(asset_id); del job
            await asyncio.sleep(0); gc.collect()
            assert all(ref() is None for ref in refs)
    asyncio.run(scenario())


def test_multiple_ai_algorithms_rejected_before_model_lease():
    from pixelmend_engine.jobs import JobQueue
    async def scenario():
        store = AssetStore(); asset_id = source(store)
        async with JobQueue(store) as queue:
            with pytest.raises(ValueError, match='one AI'):
                queue.submit(asset_id, ['lama', 'migan_512_places2'], np.full((9,9),255,np.uint8))
            assert queue.jobs == {}
            store.delete(asset_id)
    asyncio.run(scenario())
