from pathlib import Path

from platformdirs import user_cache_path

from pixelmend_engine.paths import get_models_dir, create_session_dir, cleanup_stale_sessions


def test_models_dir_defaults_to_pixelmend_platform_cache(monkeypatch) -> None:
    monkeypatch.delenv("PIXELMEND_MODELS_DIR", raising=False)

    assert get_models_dir() == Path(
        user_cache_path("PixelMend", appauthor=False)
    ) / "models"


def test_models_dir_honors_explicit_override(monkeypatch, tmp_path: Path) -> None:
    override = tmp_path / "model-store"
    monkeypatch.setenv("PIXELMEND_MODELS_DIR", str(override))

    assert get_models_dir() == override


def test_owned_sessions_are_marked_and_only_expire_after_ttl(tmp_path: Path) -> None:
    active = create_session_dir(tmp_path)
    stale = create_session_dir(tmp_path)
    stale.touch(exist_ok=True)
    import os, time
    old = time.time() - 100
    os.utime(stale / '.pixelmend-session', (old, old))
    (tmp_path / 'unrelated').mkdir()
    cleanup_stale_sessions(tmp_path, ttl_seconds=10)
    assert active.exists()
    assert not stale.exists()
    assert (tmp_path / 'unrelated').exists()
