from pathlib import Path

from platformdirs import user_cache_path

from pixelmend_engine.paths import get_models_dir


def test_models_dir_defaults_to_pixelmend_platform_cache(monkeypatch) -> None:
    monkeypatch.delenv("PIXELMEND_MODELS_DIR", raising=False)

    assert get_models_dir() == Path(
        user_cache_path("PixelMend", appauthor=False)
    ) / "models"


def test_models_dir_honors_explicit_override(monkeypatch, tmp_path: Path) -> None:
    override = tmp_path / "model-store"
    monkeypatch.setenv("PIXELMEND_MODELS_DIR", str(override))

    assert get_models_dir() == override
