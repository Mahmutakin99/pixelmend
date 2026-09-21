from pathlib import Path

from pixelmend_engine.execution_profile import provider_candidates, runtime_providers


def test_apple_prefers_coreml_then_cpu(tmp_path):
    candidates = provider_candidates(
        ('CoreMLExecutionProvider', 'CPUExecutionProvider'), tmp_path, platform_name='darwin')
    assert candidates[0][0] == 'CoreMLExecutionProvider'
    assert candidates[-1] == 'CPUExecutionProvider'


def test_windows_nvidia_prefers_cuda_then_cpu(tmp_path):
    candidates = provider_candidates(
        ('CUDAExecutionProvider', 'DmlExecutionProvider', 'CPUExecutionProvider'), tmp_path, platform_name='win32')
    assert candidates == ['CUDAExecutionProvider', 'DmlExecutionProvider', 'CPUExecutionProvider']


def test_cpu_is_fallback_for_accelerated_graph_segments(tmp_path):
    assert runtime_providers('CUDAExecutionProvider', tmp_path) == ['CUDAExecutionProvider', 'CPUExecutionProvider']
