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
