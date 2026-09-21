"""Stable ONNX Runtime execution profiles for Apple Silicon inference."""

from pathlib import Path
import sys


def provider_spec(provider: str, model_cache_dir: Path):
    """Return an ORT provider declaration without advertising unavailable hardware."""
    if provider == 'CoreMLExecutionProvider':
        return (provider, {
            'ModelFormat': 'MLProgram',
            'MLComputeUnits': 'ALL',
            'RequireStaticInputShapes': '0',
            'EnableOnSubgraphs': '0',
            'ModelCacheDirectory': str(model_cache_dir),
        })
    return provider


def provider_candidates(available: tuple[str, ...] | list[str], model_cache_dir: Path,
                        *, platform_name: str | None = None):
    """Return platform-appropriate candidates; every accelerated path retains CPU.

    Presence is only a candidate. ``_probe_model`` selects one after a real inference,
    so a driver, runtime, or graph lowering failure cannot be advertised as usable.
    """
    platform_name = platform_name or sys.platform
    if platform_name == 'darwin':
        names = ('CoreMLExecutionProvider', 'CPUExecutionProvider')
    elif platform_name.startswith('win'):
        names = ('CUDAExecutionProvider', 'DmlExecutionProvider', 'CPUExecutionProvider')
    elif platform_name.startswith('linux'):
        names = ('CUDAExecutionProvider', 'CPUExecutionProvider')
    else:
        names = ('CPUExecutionProvider',)
    candidates = []
    for provider in names:
        if provider not in available:
            continue
        if provider == 'CoreMLExecutionProvider':
            try:
                model_cache_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                # A read-only cache must never make a verified CPU model unavailable.
                continue
        candidates.append(provider_spec(provider, model_cache_dir))
    return candidates


def runtime_providers(provider: str, model_cache_dir: Path):
    """Keep CPU available for graph portions an accelerated EP cannot lower."""
    spec = provider_spec(provider, model_cache_dir)
    return [spec, 'CPUExecutionProvider'] if provider != 'CPUExecutionProvider' else [spec]


def select_fastest(timings):
    """Choose only among providers that completed a real warm inference."""
    return min(timings)[1]


def provider_is_active(session_providers, requested: str):
    """Avoid reporting a requested EP after ONNX Runtime silently fell back."""
    return requested in session_providers
