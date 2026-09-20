from pathlib import Path

from pixelmend_engine.execution_profile import provider_candidates, provider_spec, runtime_providers, select_fastest, provider_is_active


def test_coreml_candidates_precede_cpu_and_use_a_model_cache(tmp_path: Path):
    candidates = provider_candidates(
        ('CoreMLExecutionProvider', 'CPUExecutionProvider'), tmp_path,
    )
    assert candidates[1] == 'CPUExecutionProvider'
    coreml = candidates[0][1]
    assert coreml['ModelFormat'] == 'MLProgram'
    assert coreml['MLComputeUnits'] == 'ALL'
    assert coreml['ModelCacheDirectory'] == str(tmp_path)


def test_cpu_provider_has_no_apple_specific_options(tmp_path: Path):
    assert provider_spec('CPUExecutionProvider', tmp_path) == 'CPUExecutionProvider'


def test_coreml_runtime_keeps_cpu_for_unsupported_subgraphs(tmp_path: Path):
    providers = runtime_providers('CoreMLExecutionProvider', tmp_path)
    assert providers[0][0] == 'CoreMLExecutionProvider'
    assert providers[1] == 'CPUExecutionProvider'


def test_coreml_is_skipped_when_its_cache_cannot_be_created(monkeypatch, tmp_path: Path):
    def denied(*args, **kwargs):
        raise PermissionError('sandbox')
    monkeypatch.setattr(Path, 'mkdir', denied)
    assert provider_candidates(('CoreMLExecutionProvider', 'CPUExecutionProvider'), tmp_path) == [
        'CPUExecutionProvider'
    ]


def test_fastest_selection_uses_warm_measurement():
    assert select_fastest([(4.9, 'CPUExecutionProvider'), (1.2, 'CoreMLExecutionProvider')]) == 'CoreMLExecutionProvider'


def test_provider_is_active_uses_the_created_ort_session_not_the_request():
    assert provider_is_active(('CoreMLExecutionProvider', 'CPUExecutionProvider'), 'CoreMLExecutionProvider')
    assert not provider_is_active(('CPUExecutionProvider',), 'CoreMLExecutionProvider')
