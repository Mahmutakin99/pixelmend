import json
from pathlib import Path

from pixelmend_engine.inference_evidence import summarize_profile


def test_counts_only_executed_provider_events_and_discards_paths(tmp_path):
    trace = tmp_path / 'profile.json'
    trace.write_text(json.dumps([
        {'cat':'Node','ph':'X','dur':12,'args':{'provider':'CoreMLExecutionProvider','private_path':'/Users/private/image.png'}},
        {'cat':'Node','ph':'X','dur':2,'args':{'provider':'CPUExecutionProvider'}},
        {'cat':'Session','ph':'X','args':{'provider':'CUDAExecutionProvider'}},
    ]))
    evidence = summarize_profile(trace)
    assert evidence['providers'] == {'CoreMLExecutionProvider':1,'CPUExecutionProvider':1}
    assert '/Users' not in json.dumps(evidence)
    assert 'CUDAExecutionProvider' not in json.dumps(evidence)


def test_missing_profile_is_not_execution_evidence(tmp_path):
    evidence = summarize_profile(tmp_path / 'missing.json')
    assert evidence['status'] == 'unavailable'
    assert evidence['providers'] == {}
