"""Stable ONNX Runtime execution profiles for Apple Silicon inference."""

from pathlib import Path


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


def provider_candidates(available: tuple[str, ...] | list[str], model_cache_dir: Path):
    """Prefer a measured Apple profile, retaining CPU as a correct fallback."""
    names = ('CoreMLExecutionProvider', 'CPUExecutionProvider')
    candidates = []
    if 'CoreMLExecutionProvider' in available:
        try:
            model_cache_dir.mkdir(parents=True, exist_ok=True)
            candidates.append(provider_spec('CoreMLExecutionProvider', model_cache_dir))
        except OSError:
            # A read-only cache must never make a verified CPU model unavailable.
            pass
    if 'CPUExecutionProvider' in available:
        candidates.append('CPUExecutionProvider')
    return candidates


def runtime_providers(provider: str, model_cache_dir: Path):
    """Keep CPU available for graph portions Core ML cannot lower."""
    spec = provider_spec(provider, model_cache_dir)
    return [spec, 'CPUExecutionProvider'] if provider == 'CoreMLExecutionProvider' else [spec]


def select_fastest(timings):
    """Choose only among providers that completed a real warm inference."""
    return min(timings)[1]


def provider_is_active(session_providers, requested: str):
    """Avoid reporting a requested EP after ONNX Runtime silently fell back."""
    return requested in session_providers
