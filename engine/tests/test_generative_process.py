import json
import os
import sys
import threading
import time

import pytest

from pixelmend_engine.generative_process import RuntimeOwner, RuntimeErrorCode


def executable(tmp_path,body):
    path=tmp_path/'runtime'
    path.write_text(f'#!{sys.executable}\n'+body)
    path.chmod(0o700)
    return path


def test_waits_for_exit_after_result_and_keeps_prompt_off_argv(tmp_path):
    path=executable(tmp_path,"""import sys,json,time
request=json.loads(sys.stdin.readline())
assert len(sys.argv)==1
print(json.dumps({'event':'stage','stage':'translating'}),flush=True)
print(json.dumps({'event':'result','english':'Add a cat.'}),flush=True)
time.sleep(.15)
""")
    owner=RuntimeOwner(path);stages=[];start=time.monotonic()
    result=owner.run({'operation':'translate','prompt':'private synthetic'},threading.Event(),stages.append,timeout=2)
    assert result['english']=='Add a cat.' and time.monotonic()-start>=.15
    assert stages==[{'event':'stage','stage':'translating'}]
    assert owner.active_pid is None
    owner.close()


@pytest.mark.parametrize('body',[
    "print('not JSON',flush=True)",
    "print('x'*65537,flush=True)",
    "print('{\"event\":\"result\",\"english\":\"a\"}',flush=True);print('{\"event\":\"result\",\"english\":\"b\"}',flush=True)",
    "import sys;sys.exit(9)",
    "print('{\"event\":\"error\",\"code\":\"a private prompt or path\"}',flush=True)",
])
def test_invalid_protocol_and_crash_have_content_free_errors(tmp_path,body):
    owner=RuntimeOwner(executable(tmp_path,body))
    with pytest.raises(RuntimeErrorCode) as error:
        owner.run({'operation':'translate'},threading.Event(),lambda _:None,timeout=2)
    assert error.value.code in {'runtime_crashed','output_invalid'}
    assert 'private' not in str(error.value)
    assert owner.active_pid is None


def test_timeout_terminates_and_reaps_owned_child(tmp_path):
    path=executable(tmp_path,'import time\ntime.sleep(30)')
    owner=RuntimeOwner(path,cooperative_seconds=.05,terminate_seconds=.05)
    start=time.monotonic()
    with pytest.raises(RuntimeErrorCode) as error:
        owner.run({'operation':'generate'},threading.Event(),lambda _:None,timeout=.1)
    assert error.value.code=='timeout'
    assert time.monotonic()-start<1 and owner.active_pid is None


@pytest.mark.skipif(os.name=='nt',reason='POSIX group ownership')
def test_cancel_escalates_for_uncooperative_native_call_and_cleans_helper(tmp_path):
    path=executable(tmp_path,"""import os,signal,sys,time,json
signal.signal(signal.SIGTERM,signal.SIG_IGN)
signal.signal(signal.SIGINT,signal.SIG_IGN)
pid=os.fork()
if pid==0:
    while True:time.sleep(.1)
print(json.dumps({'event':'stage','stage':'loading_image_model'}),flush=True)
while True:time.sleep(.1)
""")
    owner=RuntimeOwner(path,cooperative_seconds=.05,terminate_seconds=.05)
    cancel=threading.Event();start=time.monotonic()
    with pytest.raises(InterruptedError):
        owner.run({'operation':'generate'},cancel,lambda _:cancel.set(),timeout=2)
    assert time.monotonic()-start<1 and owner.active_pid is None


def test_close_prevents_new_children_and_cancels_active_request(tmp_path):
    path=executable(tmp_path,"import time,json\nprint(json.dumps({'event':'stage','stage':'generating'}),flush=True)\ntime.sleep(30)")
    owner=RuntimeOwner(path,cooperative_seconds=.05,terminate_seconds=.05)
    entered=threading.Event();errors=[]
    def run():
        try:owner.run({'operation':'generate'},threading.Event(),lambda _:entered.set(),timeout=5)
        except InterruptedError:errors.append('cancelled')
    thread=threading.Thread(target=run);thread.start();assert entered.wait(2)
    owner.close();thread.join(2)
    assert errors==['cancelled'] and owner.active_pid is None and not thread.is_alive()
    with pytest.raises(RuntimeErrorCode):owner.run({},threading.Event(),lambda _:None,timeout=1)


@pytest.mark.skipif(os.name=='nt',reason='private POSIX file contract')
def test_output_validation_rejects_links_wrong_size_channels_and_metadata(tmp_path):
    from PIL import Image,PngImagePlugin
    from pixelmend_engine.generative_process import validate_output
    path=tmp_path/'output.png'
    def write(image,**kwargs):
        path.unlink(missing_ok=True);image.save(path,**kwargs);path.chmod(0o600)
    write(Image.new('RGB',(32,32)))
    assert validate_output(tmp_path,(32,32)).size==(32,32)
    for image in [Image.new('RGB',(31,32)),Image.new('RGBA',(32,32))]:
        write(image)
        with pytest.raises(RuntimeErrorCode):validate_output(tmp_path,(32,32))
    metadata=PngImagePlugin.PngInfo();metadata.add_text('prompt','private synthetic')
    write(Image.new('RGB',(32,32)),pnginfo=metadata)
    with pytest.raises(RuntimeErrorCode):validate_output(tmp_path,(32,32))
    outside=tmp_path/'outside.png';Image.new('RGB',(32,32)).save(outside);outside.chmod(0o600)
    path.unlink();path.symlink_to(outside)
    with pytest.raises(RuntimeErrorCode):validate_output(tmp_path,(32,32))

@pytest.mark.skipif(os.name=='nt',reason='POSIX exit-group race')
def test_dead_group_permission_error_cannot_leave_a_stale_active_owner(tmp_path,monkeypatch):
    path=executable(tmp_path,"import json,sys\njson.loads(sys.stdin.readline())\nprint(json.dumps({'event':'result','english':'A cat.'}),flush=True)")
    def denied(*_):raise PermissionError('departed process group')
    monkeypatch.setattr(os,'killpg',denied)
    owner=RuntimeOwner(path)
    try:
        result=owner.run({},threading.Event(),lambda _:None,timeout=2)
        assert result['english']=='A cat.'
    finally:
        assert owner.active_pid is None
    owner.close()


@pytest.mark.parametrize('available,hardware,expected',[(1,'Mac16,10','memory_insufficient'),(16*1024**3,'other','probe_not_accepted')])
def test_probe_rejects_unavailable_memory_or_unmeasured_hardware(monkeypatch,available,hardware,expected):
    from types import SimpleNamespace
    from pixelmend_engine import capabilities
    from pixelmend_engine.generative_packages import load_catalog
    import pixelmend_engine.generative_process as module
    owner=RuntimeOwner('/unused/runtime');calls=[]
    monkeypatch.setattr(capabilities,'generative_capabilities',lambda *_:{'platform_supported':True})
    monkeypatch.setattr(capabilities,'_mac_sysctl',lambda *_:hardware)
    monkeypatch.setattr(module.psutil,'virtual_memory',lambda:SimpleNamespace(total=16*1024**3,available=available))
    monkeypatch.setattr(owner,'run',lambda *a,**k:calls.append(a))
    with pytest.raises(RuntimeErrorCode) as error:owner.probe(load_catalog()[0],'/unused/model',threading.Event())
    assert error.value.code==expected
    assert calls==[]


def test_probe_accepts_measured_budget_with_reserve_without_enabling_profile(monkeypatch):
    from types import SimpleNamespace
    from pixelmend_engine import capabilities
    from pixelmend_engine.generative_packages import load_catalog
    import pixelmend_engine.generative_process as module
    definition=load_catalog()[0];budget=definition.probe_memory[0]['working_memory_bytes']
    assert definition.accepted_profiles==()
    owner=RuntimeOwner('/unused/runtime');calls=[]
    monkeypatch.setattr(capabilities,'generative_capabilities',lambda *_:{'platform_supported':True})
    monkeypatch.setattr(capabilities,'_mac_sysctl',lambda *_:'Mac16,10')
    monkeypatch.setattr(module.psutil,'virtual_memory',lambda:SimpleNamespace(total=16*1024**3,available=(budget*6+4)//5+2*1024**3))
    def run(request,*a,**k):
        calls.append(request);return {'metal':True,'gpu_result':[2,4,6],'image_model_loaded':True,
            'child_wall_seconds':1,'child_peak_rss_bytes':2,'child_peak_footprint_bytes':3,'stage_seconds':{}}
    monkeypatch.setattr(owner,'run',run)
    result=owner.probe(definition,'/unused/model',threading.Event())
    assert result['status']=='passed' and result['child_peak_footprint_bytes']==3
    assert len(calls)==1 and calls[0]['operation']=='probe'
