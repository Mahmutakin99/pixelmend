from pixelmend_engine.fallback import may_retry_cpu
from pixelmend_engine.model_manager import ModelManagerError
from pixelmend_engine.models.realesrgan_onnx import InferenceCancelled


def test_only_native_accelerator_failure_retries_same_model_once():
    failure_type = type('Fail', (Exception,), {'__module__':'onnxruntime.capi.onnxruntime_pybind11_state'})
    error = failure_type('device lost')
    assert may_retry_cpu(error, 'CoreMLExecutionProvider', False)
    assert not may_retry_cpu(error, 'CPUExecutionProvider', False)
    assert not may_retry_cpu(error, 'CoreMLExecutionProvider', True)
    assert not may_retry_cpu(InferenceCancelled(), 'CoreMLExecutionProvider', False)
    assert not may_retry_cpu(ValueError('bad pixels'), 'CoreMLExecutionProvider', False)
    assert not may_retry_cpu(ModelManagerError('hash_mismatch', 'changed artifact'), 'CoreMLExecutionProvider', False)
    assert may_retry_cpu(ModelManagerError('provider_unavailable','device missing'), 'CoreMLExecutionProvider', False)


def test_queue_records_cpu_retry_without_changing_the_model(monkeypatch):
    import asyncio
    from contextlib import contextmanager
    from pathlib import Path
    from io import BytesIO
    import numpy as np
    from PIL import Image
    import pixelmend_engine.jobs as jobs
    from pixelmend_engine.assets import AssetStore
    from types import SimpleNamespace
    import pixelmend_engine.fallback as fallback
    monkeypatch.setattr(fallback.psutil, 'virtual_memory', lambda: SimpleNamespace(available=8*1024**3))
    providers = []
    failure_type = type('Fail', (Exception,), {'__module__':'onnxruntime.capi.onnxruntime_pybind11_state'})
    def native(image, mask, algorithm, scale, target_size=None, **options):
        providers.append((algorithm, options['provider'], options['model_path']))
        if options['provider'] != 'CPUExecutionProvider':
            raise failure_type('device lost')
        return image
    class Manager:
        @contextmanager
        def lease(self, model):
            yield Path('/verified/revision/model.onnx')
        def selected_provider(self, model):
            return 'CoreMLExecutionProvider'
    monkeypatch.setattr(jobs, 'process', native)
    async def run():
        store = AssetStore()
        data = BytesIO()
        Image.new('RGB',(9,9)).save(data,format='PNG')
        asset = store.import_image(BytesIO(data.getvalue()))
        async with jobs.JobQueue(store,processor=native,model_manager=Manager()) as queue:
            job = queue.submit(asset.asset_id,['lama'],np.full((9,9),255,np.uint8))
            await queue.join()
            assert job.status == 'completed', job.error
            assert job.snapshot()['result_details'][0]['fallback_reason'] == 'accelerator_execution_failed'
            assert job.provider == 'CPUExecutionProvider'
        assert [p[1] for p in providers] == ['CoreMLExecutionProvider','CPUExecutionProvider']
        assert providers[0][0] == providers[1][0] == 'lama'
        assert providers[0][2] == providers[1][2]
        store.close()
    asyncio.run(run())
