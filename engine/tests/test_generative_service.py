import asyncio
from io import BytesIO
import hashlib
from pathlib import Path
import threading

import numpy as np
from PIL import Image
import pytest

from pixelmend_engine.assets import AssetStore, AssetInUseError
from pixelmend_engine.compute import ComputeCoordinator
from pixelmend_engine.generative_packages import PackageDefinition,PackageManager,PackagePart
from pixelmend_engine.model_package import ModelPackageManifest,ModelPackageFile
from pixelmend_engine.generative_service import GenerativeRequest,GenerativeService,IMAGE_PACKAGE,TRANSLATION_PACKAGE
from pixelmend_engine.generative_process import RuntimeErrorCode
from pixelmend_engine.jobs import JobQueue

GIB=1024**3

def payload(**overrides):
    return {'operation':'text_to_image','prompt':'Bir beyaz kedi oluştur.','prompt_language':'tr',
            'profile':'low-resource','aspect':'square','seed':42}|overrides


def fixtures(tmp_path):
    coordinator=ComputeCoordinator();catalog=[]
    for id,runtime,operations in [(IMAGE_PACKAGE,'mlx',('text_edit','text_to_image')),
                                  (TRANSLATION_PACKAGE,'torch-cpu',('translate',))]:
        file=ModelPackageFile('model.safetensors',1,hashlib.sha256(b'x').hexdigest())
        manifest=ModelPackageManifest(id,'a'*40,'Apache-2.0','https://example.test',(file,))
        profiles=tuple({'profile':p,'hardware_class':'Mac16,10','working_memory_bytes':4*GIB} for p in ['low-resource','balanced']) if runtime=='mlx' else ()
        catalog.append(PackageDefinition(manifest,'Fixture',runtime,operations,'fixture/source','b'*40,
            (PackagePart(file.path,0,file.size_bytes,file.sha256,file.path),),profiles))
        target=tmp_path/'models'/id/manifest.revision;target.mkdir(parents=True)
        (target/file.path).write_bytes(b'x')
    manager=PackageManager(tmp_path/'models',catalog=catalog,coordinator=coordinator)
    host={'platform_supported':True,'runtime_installed':True,'hardware_class':'Mac16,10',
          'available_memory_bytes':12*GIB,'disk_free_bytes':GIB}
    class Owner:
        def __init__(self):self.requests=[];self.active_pid=None
        def run(self,request,cancel,progress,timeout):
            self.requests.append(request)
            if request['operation']=='translate':
                progress({'event':'stage','stage':'translating'});return {'english':'Create a white cat.'}
            assert not cancel.is_set()
            progress({'event':'stage','stage':'generating'})
            for i in range(4):
                progress({'event':'progress','completed':i+1,'total':4})
                if cancel.is_set():raise InterruptedError()
            path=Path(request['session_dir'])/'output.png'
            if request['image_phase']=='denoise':
                import json,struct
                size=2*128*(request['height']//16)*(request['width']//16)
                header=json.dumps({'packed_latents':{'dtype':'BF16','shape':[1,128,request['height']//16,request['width']//16],'data_offsets':[0,size]}}).encode()
                latent=Path(request['session_dir'])/'latents.safetensors'
                latent.write_bytes(struct.pack('<Q',len(header))+header+bytes(size));latent.chmod(0o600)
            else:
                Image.new('RGB',(request['width'],request['height']),(17,29,41)).save(path);path.chmod(0o600)
            return {'seed':request['seed'],'width':request['width'],'height':request['height'],
                    'image_phase':request['image_phase'],'versions':{'mlx':'fixture'},'child_wall_seconds':.001,
                    'stage_seconds':{'generating':.001},'mlx_peak_bytes':1,'child_peak_rss_bytes':2}
    owner=Owner();assets=AssetStore()
    service=GenerativeService(assets,manager,owner,session_parent=lambda:tmp_path/'sessions',host_provider=lambda:host)
    return service,manager,owner,assets,host,coordinator


@pytest.mark.parametrize('overrides',[
 {'prompt':''},{'prompt':'ğ'*1001},{'seed':True},{'seed':-1},{'seed':2**32},
 {'profile':'automatic'},{'aspect':'cinema'},{'width':4096},{'model_dir':'/private/model'},
 {'operation':'video'},{'prompt_language':'auto'},{'english_override':'  '},
 {'asset_id':'a'*32},{'operation':'text_edit'},
])
def test_request_is_discriminated_bounded_and_has_no_path_or_custom_size(overrides):
    with pytest.raises(RuntimeErrorCode):GenerativeRequest.parse(payload(**overrides))
    assert GenerativeRequest.parse(payload(prompt='🐈'*1000)).prompt=='🐈'*1000


@pytest.mark.parametrize('profile,aspect,size',[
 ('low-resource','square',(512,512)),('low-resource','landscape',(640,480)),
 ('low-resource','portrait',(480,640)),('balanced','square',(768,768)),
 ('balanced','landscape',(1024,768)),('balanced','portrait',(768,1024)),
])
def test_text_generation_without_source_uses_exact_dimensions_and_releases_leases(tmp_path,profile,aspect,size):
    async def check():
        service,manager,owner,assets,host,coordinator=fixtures(tmp_path)
        await manager.start()
        async with JobQueue(assets,generative_service=service,coordinator=coordinator) as queue:
            request=GenerativeRequest.parse(payload(profile=profile,aspect=aspect))
            assert service.preflight(request)['ready']
            job=queue.submit_generative(request)
            assert job.asset_id is None
            assert all(v['in_use']==1 for v in manager.list_models()['models'])
            await queue.join();assert job.status=='completed',job.error
            result=next(iter(job.results.values()));assert (result.width,result.height)==size
            assert result.alpha is None
            detail=job.snapshot()['result_details'][0]
            assert detail['seed']==42 and detail['runtime']=='mlx' and detail['provider'] is None
            assert detail['original_prompt']==request.prompt and detail['used_prompt']=='Create a white cat.'
            assert [r['operation'] for r in owner.requests]==['translate','generate','generate']
            assert all(v['in_use']==0 for v in manager.list_models()['models'])
            assert not list((tmp_path/'sessions').iterdir())
            adopted=assets.adopt_image(result);queue.delete(job.job_id);assets.delete(adopted.asset_id)
            assert assets.used_bytes==0
        await manager.close()
    asyncio.run(check())


def test_profile_admission_repeats_at_execution_after_memory_falls(tmp_path):
    async def check():
        service,manager,owner,assets,host,coordinator=fixtures(tmp_path);await manager.start()
        async with JobQueue(assets,generative_service=service,coordinator=coordinator) as queue:
            request=GenerativeRequest.parse(payload())
            assert service.preflight(request)['ready']
            job=queue.submit_generative(request);host['available_memory_bytes']=GIB
            await queue.join()
            assert job.status=='failed' and job.error['code']=='memory_insufficient'
            assert owner.requests==[] and job.results=={}
            assert all(v['in_use']==0 for v in manager.list_models()['models'])
        await manager.close()
    asyncio.run(check())


def test_unaccepted_hardware_profile_is_not_silently_replaced(tmp_path):
    service,manager,owner,assets,host,coordinator=fixtures(tmp_path)
    host['hardware_class']='Mac14,12'
    result=service.preflight(GenerativeRequest.parse(payload(profile='balanced')))
    assert not result['ready'] and result['reason']['code']=='profile_not_accepted'
    assert result['profile']=='balanced' and result['width']==768
    assert owner.requests==[]


def test_text_edit_retains_source_paint_mask_alpha_and_drops_cancelled_candidate(tmp_path):
    async def check():
        service,manager,owner,assets,host,coordinator=fixtures(tmp_path);await manager.start()
        raw=BytesIO();Image.new('RGBA',(400,400),(0,0,0,127)).save(raw,format='PNG');id=assets.import_image(raw).asset_id
        stroke={'mode':'draw','points':[{'x':200,'y':200}],'size':160,'opacity':1,'color':'#ff0000','hardness':1}
        request=GenerativeRequest.parse({'operation':'text_edit','asset_id':id,'prompt':'Add a cat.',
            'prompt_language':'en','profile':'low-resource','seed':7,'selection_strokes':[stroke],'paint_strokes':[]})
        async with JobQueue(assets,generative_service=service,coordinator=coordinator) as queue:
            job=queue.submit_generative(request)
            with pytest.raises(AssetInUseError):assets.delete(id)
            await queue.join();assert job.status=='completed',job.error
            result=next(iter(job.results.values()));source=assets.get_image(id)
            assert result.rgb[0,0].tolist()==source.rgb[0,0].tolist()
            np.testing.assert_array_equal(result.alpha,source.alpha)
            assert len(owner.requests)==2 and all(r['operation']=='edit' for r in owner.requests)
            assert all(v['in_use']==0 for v in manager.list_models()['models'])
            queue.delete(job.job_id)
            # Cancel while queued: no child or candidate may be published.
            cancelled=queue.submit_generative(request);queue.cancel(cancelled.job_id)
            await queue.join();assert cancelled.status=='cancelled' and cancelled.results=={}
            assert len(owner.requests)==2 and not list((tmp_path/'sessions').iterdir())
        assets.delete(id);await manager.close()
    asyncio.run(check())


def test_preflight_rejects_disk_and_result_or_asset_capacity(tmp_path):
    service,manager,owner,assets,host,coordinator=fixtures(tmp_path)
    request=GenerativeRequest.parse(payload())
    host['disk_free_bytes']=1
    assert service.preflight(request)['reason']['code']=='disk_insufficient'
    host['disk_free_bytes']=GIB
    assert service.preflight(request,result_bytes=1024**3)['reason']['code']=='result_budget'
    assets.max_assets=0
    assert service.preflight(request)['reason']['code']=='asset_capacity'


def test_translation_loaded_flag_clears_before_image_child(tmp_path):
    async def check():
        service,manager,owner,assets,host,coordinator=fixtures(tmp_path)
        original=owner.run
        def run(request,cancel,progress,timeout):
            if request['operation']=='generate':
                assert not manager._views[TRANSLATION_PACKAGE]['loaded']
                progress({'event':'stage','stage':'loading_image_model'})
                assert manager._views[IMAGE_PACKAGE]['loaded']
            return original(request,cancel,progress,timeout)
        owner.run=run
        await manager.start()
        async with JobQueue(assets,generative_service=service,coordinator=coordinator) as queue:
            job=queue.submit_generative(GenerativeRequest.parse(payload()));await queue.join()
            assert job.status=='completed',job.error
        await manager.close()
    asyncio.run(check())

def test_preflight_reports_dynamic_available_and_required_memory_without_loading(tmp_path):
    service,manager,owner,assets,host,_=fixtures(tmp_path)
    request=GenerativeRequest.parse(payload())
    host['available_memory_bytes']=GIB
    report=service.preflight(request)
    assert report['available_memory_bytes']==GIB
    assert report['required_available_memory_bytes']>GIB
    assert report['reason']['code']=='memory_insufficient'
    assert 'Düşük kaynak profilini seçin' not in report['reason']['message']
    host['available_memory_bytes']=12*GIB
    assert service.preflight(request)['ready'] is True
    assert owner.requests==[]

def test_successful_generation_clears_old_deferred_loading_warning(tmp_path):
    async def check():
        service,manager,owner,assets,host,_=fixtures(tmp_path);await manager.start()
        for id in manager.catalog:manager._change(id,last_check={'status':'deferred','code':'memory_insufficient'})
        request=GenerativeRequest.parse(payload());reservations=service.reserve(request)
        try:await asyncio.to_thread(service.execute,request,reservations,threading.Event(),lambda _:None)
        finally:
            for reservation in reservations:reservation.release()
        assert all(view['last_check'] is None for view in manager.list_models()['models'])
        await manager.close()
    asyncio.run(check())

def test_successful_translation_clears_its_warning_even_when_image_memory_changes(tmp_path):
    async def check():
        service,manager,owner,assets,host,_=fixtures(tmp_path);await manager.start()
        for id in manager.catalog:manager._change(id,last_check={'status':'deferred','code':'memory_insufficient'})
        run=owner.run
        def translate(*args,**kwargs):
            result=run(*args,**kwargs);host['available_memory_bytes']=GIB;return result
        owner.run=translate
        request=GenerativeRequest.parse(payload());reservations=service.reserve(request)
        try:
            with pytest.raises(RuntimeErrorCode,match='bellek'):
                await asyncio.to_thread(service.execute,request,reservations,threading.Event(),lambda _:None)
        finally:
            for reservation in reservations:reservation.release()
        views={v['id']:v for v in manager.list_models()['models']}
        assert views[TRANSLATION_PACKAGE]['last_check'] is None
        assert views[IMAGE_PACKAGE]['last_check']['status']=='deferred'
        await manager.close()
    asyncio.run(check())


def test_confirmed_host_identity_survives_transient_sysctl_failure_with_live_ram(tmp_path,monkeypatch):
    from types import SimpleNamespace
    import pixelmend_engine.generative_service as module
    service,_,owner,_,_,_=fixtures(tmp_path)
    owner.executable=Path(__file__)
    memory=SimpleNamespace(total=16*GIB,available=12*GIB)
    monkeypatch.setattr(module.psutil,'virtual_memory',lambda:memory)
    monkeypatch.setattr(module,'generative_capabilities',lambda *_:{'platform_supported':True,'runtime_installed':True})
    observed=iter(['Mac16,10',None,None])
    monkeypatch.setattr(module,'_mac_sysctl',lambda _:next(observed,None))
    service.host_provider=service._host
    request=GenerativeRequest.parse(payload())
    assert service.preflight(request)['ready']
    memory.available=GIB
    denied=service.preflight(request)
    assert denied['reason']['code']=='memory_insufficient'
    assert denied['available_memory_bytes']==GIB
    memory.available=12*GIB
    assert service.preflight(request)['ready']


def test_unknown_host_identity_is_retried_without_assuming_an_accepted_device(tmp_path,monkeypatch):
    import pixelmend_engine.generative_service as module
    service,_,owner,_,_,_=fixtures(tmp_path)
    owner.executable=Path(__file__)
    monkeypatch.setattr(module,'generative_capabilities',lambda *_:{'platform_supported':True,'runtime_installed':True})
    observed=iter([None,'Mac16,10'])
    monkeypatch.setattr(module,'_mac_sysctl',lambda _:next(observed,None))
    service.host_provider=service._host
    request=GenerativeRequest.parse(payload())
    assert service.preflight(request)['reason']['code']=='profile_not_accepted'
    # RAM/disk remain real; inspect profile selection without assuming resources.
    host=service._host()
    assert host['hardware_class']=='Mac16,10'
    assert service._profile(request,host) is not None


def test_delayed_unknown_host_query_cannot_erase_concurrently_confirmed_identity(tmp_path,monkeypatch):
    import pixelmend_engine.generative_service as module
    service,_,owner,_,_,_=fixtures(tmp_path)
    owner.executable=Path(__file__)
    entered=threading.Event();release=threading.Event();delayed=[]
    def query(_):
        if threading.current_thread().name=='delayed-host-query':
            entered.set()
            assert release.wait(2)
            return None
        return 'Mac16,10'
    monkeypatch.setattr(module,'_mac_sysctl',query)
    thread=threading.Thread(target=lambda:delayed.append(service._host()),name='delayed-host-query')
    thread.start()
    try:
        assert entered.wait(2)
        assert service._host()['hardware_class']=='Mac16,10'
    finally:
        release.set();thread.join(2)
    assert not thread.is_alive()
    assert delayed[0]['hardware_class']=='Mac16,10'
