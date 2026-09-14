import asyncio
from io import BytesIO
from threading import Event

import numpy as np
from PIL import Image
import pytest

from pixelmend_engine.assets import AssetStore, AssetInUseError


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
                queue.submit(asset_id, ['lanczos'], target_width=10000, target_height=6000)
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
            job = queue.submit(asset_id, ['lama'], np.full((9, 9), 255, np.uint8))
            await queue.join()
            state = job.snapshot()
            assert state['status'] == 'failed'
            assert state['error']['code'] == 'model_missing'
            assert 'LaMa' in state['error']['message']
            assert '/private' not in str(state)
    asyncio.run(scenario())
