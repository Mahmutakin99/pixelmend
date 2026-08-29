"""Resolve filesystem locations owned by the PixelMend sidecar."""

import os
from pathlib import Path

from platformdirs import user_cache_path

MODELS_DIR_ENV = "PIXELMEND_MODELS_DIR"


def get_models_dir() -> Path:
    """Return the sidecar-owned model directory without creating it."""
    override = os.environ.get(MODELS_DIR_ENV)
    if override:
        return Path(override).expanduser()

    return Path(user_cache_path("PixelMend", appauthor=False)) / "models"
