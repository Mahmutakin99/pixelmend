"""Resolve filesystem locations owned by the PixelMend sidecar."""

import os
import shutil
import time
import tempfile
import sys
from pathlib import Path
from uuid import uuid4

from platformdirs import user_cache_path, user_data_path

MODELS_DIR_ENV = "PIXELMEND_MODELS_DIR"
SESSIONS_DIR_ENV = 'PIXELMEND_SESSIONS_DIR'
SESSION_MARKER = '.pixelmend-session'


def get_models_dir() -> Path:
    """Return the sidecar-owned model directory without creating it."""
    override = os.environ.get(MODELS_DIR_ENV)
    if override:
        return Path(override).expanduser()

    return Path(user_cache_path("PixelMend", appauthor=False)) / "models"


def get_coreml_cache_dir() -> Path:
    """Return the durable Core ML compilation cache, separate from model bytes."""
    return get_models_dir().parent / 'coreml-cache'


def get_generative_models_dir() -> Path:
    """Large packages use application data; leave existing ONNX cache in place."""
    override = os.environ.get(MODELS_DIR_ENV)
    root = Path(override).expanduser() if override else Path(user_data_path('PixelMend', appauthor=False))
    return root / 'model-packages'


def get_generative_runtime() -> Path | None:
    """Main-process configuration only; never accept an executable from a request."""
    override = os.environ.get('PIXELMEND_GENERATIVE_RUNTIME')
    if override:
        candidate = Path(override)
        if not candidate.is_absolute():
            return None
    elif getattr(sys, 'frozen', False):
        candidate = Path(sys.executable).parent.parent / 'generative-runtime' / 'pixelmend-generative-runtime'
    else:
        return None
    return candidate if candidate.is_file() and not candidate.is_symlink() and os.access(candidate, os.X_OK) else None


def get_sessions_dir() -> Path:
    """Return the private parent used solely for ephemeral sidecar sessions."""
    override = os.environ.get(SESSIONS_DIR_ENV)
    # Sessions are intentionally OS-temporary, unlike durable model artifacts.
    return Path(override).expanduser() if override else Path(tempfile.gettempdir()) / 'PixelMend' / 'sessions'


def create_session_dir(parent: Path | None = None) -> Path:
    """Mark an application-owned directory before any temporary native files exist."""
    root = parent or get_sessions_dir()
    root.mkdir(parents=True, exist_ok=True)
    session = root / uuid4().hex
    session.mkdir(mode=0o700)
    (session / SESSION_MARKER).write_text('PixelMend sidecar session\n')
    return session


def cleanup_stale_sessions(parent: Path | None = None, *, ttl_seconds: int = 24 * 3600) -> None:
    """Delete only marked, idle session directories; never scan user image locations."""
    root = parent or get_sessions_dir()
    if not root.exists():
        return
    cutoff = time.time() - ttl_seconds
    for candidate in root.iterdir():
        marker = candidate / SESSION_MARKER
        if candidate.is_dir() and marker.is_file() and marker.stat().st_mtime < cutoff:
            shutil.rmtree(candidate)
