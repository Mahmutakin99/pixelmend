"""Mandatory in the Mac acceptance command (PIXELMEND_REAL_MODELS=1)."""
import asyncio
import os
from io import BytesIO
import numpy as np
from PIL import Image
import pytest
from pixelmend_engine.assets import AssetStore
from pixelmend_engine.jobs import JobQueue
from pixelmend_engine.main import _probe_model
from pixelmend_engine.model_manager import ModelManager
from pixelmend_engine.paths import get_models_dir

pytestmark = pytest.mark.skipif(os.environ.get('PIXELMEND_REAL_MODELS') != '1', reason='explicit real model acceptance')


def test_real_models_queue_preserves_alpha_and_reports_actual_artifacts():
    async def scenario():
        manager=ModelManager(get_models_dir(),prober=_probe_model)
        await manager.start()
        assert all(m['state']=='ready' for m in manager.list_models()['models'])
        rgba=np.zeros((16,24,4),np.uint8)
        rgba[:,:,:3]=np.random.default_rng(42).integers(0,255,(16,24,3),dtype=np.uint8)
        rgba[:,:,3]=np.arange(24,dtype=np.uint8)[None,:]*10
        data=BytesIO();Image.fromarray(rgba).save(data,format='PNG');data.seek(0)
        store=AssetStore();asset=store.import_image(data)
        mask=np.zeros((16,24),np.uint8);mask[6:10,10:14]=255
        try:
            async with JobQueue(store,model_manager=manager) as queue:
                lama=queue.submit(asset.asset_id,['lama'],mask)
                await queue.join();assert lama.status=='completed',lama.error
                image=next(iter(lama.results.values()))
                np.testing.assert_array_equal(image.rgb[mask==0],rgba[:,:,:3][mask==0])
                np.testing.assert_array_equal(image.alpha,rgba[:,:,3])
                ai=queue.submit(asset.asset_id,['realesrgan_x4plus'],scale=2)
                await queue.join();assert ai.status=='completed',ai.error
                image=next(iter(ai.results.values()))
                assert image.rgb.shape==(32,48,3)
                expected=np.asarray(Image.fromarray(rgba[:,:,3]).resize((48,32),Image.Resampling.LANCZOS))
                np.testing.assert_array_equal(image.alpha,expected)
                for job,algorithm in [(lama,'lama'),(ai,'realesrgan_x4plus')]:
                    detail=job.snapshot()['result_details'][0]
                    assert detail['algorithm']==algorithm
                    assert detail['model_revision']==job.model_path.parent.name
                    assert detail['provider']=='CPUExecutionProvider'
                    event=next(e for e in job.events if e['event']=='result')
                    assert event['data']['model_revision']==detail['model_revision']
        finally:
            await manager.close();store.close()
    asyncio.run(scenario())
