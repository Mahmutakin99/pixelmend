"""Resolve filesystem locations owned by the PixelMend sidecar."""

import os
import shutil
import time
import tempfile
from pathlib import Path
from uuid import uuid4

from platformdirs import user_cache_path

MODELS_DIR_ENV = "PIXELMEND_MODELS_DIR"
SESSIONS_DIR_ENV = 'PIXELMEND_SESSIONS_DIR'
SESSION_MARKER = '.pixelmend-session'


def get_models_dir() -> Path:
    """Return the sidecar-owned model directory without creating it."""
    override = os.environ.get(MODELS_DIR_ENV)
    if override:
        return Path(override).expanduser()

    return Path(user_cache_path("PixelMend", appauthor=False)) / "models"


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
