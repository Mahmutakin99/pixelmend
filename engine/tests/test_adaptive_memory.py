import threading

from test_generative_service import fixtures, payload, GIB
from pixelmend_engine.generative_service import GenerativeRequest


def test_low_available_memory_admits_selected_quality(tmp_path):
    service, _, _, _, host, _ = fixtures(tmp_path)
    host['available_memory_bytes'] = int(4.2 * GIB)
    report = service.preflight(GenerativeRequest.parse(payload(profile='balanced')))
    assert report['ready'], report
    assert report['execution_mode'] == 'adaptive'
    assert report['width'] == report['height'] == 768
    assert not report['waiting_for_memory']


def test_critical_pressure_is_accepted_as_waiting_not_failed(tmp_path):
    service, _, _, _, host, _ = fixtures(tmp_path)
    host['memory_pressure'] = 'critical'
    report = service.preflight(GenerativeRequest.parse(payload()))
    assert report['ready'] and report['waiting_for_memory']
    assert report['memory_pressure'] == 'critical'


def test_memory_gate_resumes_after_stable_recovery_and_cancels():
    from pixelmend_engine.generative_memory import MemoryGate
    clock = [0.0]
    host = {'available_memory_bytes': 4 * GIB, 'memory_pressure': 'critical'}
    events = []
    def wait(seconds):
        clock[0] += seconds
        if clock[0] >= 4:
            host['memory_pressure'] = 'normal'
        return False
    gate = MemoryGate(lambda: host, clock=lambda: clock[0], wait=wait)
    gate.wait(threading.Event(), events.append)
    assert clock[0] == 14
    assert events == [{'event': 'stage', 'stage': 'waiting_for_memory'}]
    cancel = threading.Event()
    cancel.set()
    import pytest
    with pytest.raises(InterruptedError):
        gate.wait(cancel, events.append)


def test_unknown_pressure_does_not_invent_an_unavailable_host():
    from pixelmend_engine.generative_memory import MemoryGate
    gate = MemoryGate(lambda: {'available_memory_bytes': 4 * GIB})
    gate.wait(threading.Event(), lambda _: None)


def test_allocation_recovery_waits_for_stability_even_after_pressure_clears():
    from pixelmend_engine.generative_memory import MemoryGate
    clock=[0.0];events=[]
    def wait(seconds):clock[0]+=seconds;return False
    gate=MemoryGate(lambda:{'available_memory_bytes':4*GIB,'memory_pressure':'normal'},
                    clock=lambda:clock[0],wait=wait)
    gate.wait(threading.Event(),events.append,minimum_available=4*GIB,force_recovery=True)
    assert clock[0]==10 and events==[{'event':'stage','stage':'waiting_for_memory'}]


def test_probe_uses_live_pressure_gate_without_profile_ram_reserve(monkeypatch):
    from dataclasses import replace
    from types import SimpleNamespace
    from pixelmend_engine import capabilities
    from pixelmend_engine.generative_packages import load_catalog
    from pixelmend_engine.generative_process import RuntimeOwner
    import pixelmend_engine.generative_process as module
    monkeypatch.setattr(capabilities,'generative_capabilities',lambda *_:{'platform_supported':True})
    monkeypatch.setattr(capabilities,'_mac_sysctl',lambda _:'Mac16,10')
    monkeypatch.setattr(module.psutil,'virtual_memory',lambda:SimpleNamespace(total=16*GIB,available=GIB))
    owner=RuntimeOwner('/unused/runtime')
    owner.run=lambda *args,**kwargs:{'metal':True,'gpu_result':[2,4,6],'image_model_loaded':True,
                                  'child_wall_seconds':1,'child_peak_rss_bytes':1,'stage_seconds':{}}
    definition=replace(load_catalog()[0],accepted_profiles=())
    result=owner.probe(definition,__import__('pathlib').Path('/unused/model'),threading.Event())
    assert result['status']=='passed'
