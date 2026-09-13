# Phase 1 Engine Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the Phase 1 license/codec gates, finish the M4 setup record, and create the smallest tested Python engine foundation that owns model-directory resolution.

**Architecture:** The sidecar remains a Python 3.12 `src`-layout package managed by `uv`. This slice introduces only the shared path boundary: the sidecar resolves its default platform cache directory and honors the explicit `PIXELMEND_MODELS_DIR` override without creating files as a side effect.

**Tech Stack:** Python 3.12, uv, pytest, platformdirs, Apache-2.0

---

### Task 1: Close Phase 1 decision gates

**Files:**
- Create: `LICENSE`
- Modify: `DURUM.md`
- Modify: `AI_AJANI_DEVIR_BELGESI.md`
- Modify: `docs/karar-gunlugu.md`
- Modify: `docs/modeller-ve-lisanslar.md`
- Modify: `docs/faz-0-kurulum.md`
- Modify: `docs/faz-1-hafif-motor.md`

- [x] **Step 1:** Add the standard Apache License 2.0 text as the repository license.
- [x] **Step 2:** Record ADR decisions that the repository uses Apache-2.0 and HEIF/HEIC is outside v1; JPEG, PNG, WebP, and TIFF remain the v1 inputs.
- [x] **Step 3:** Remove the two decisions from the open-gates table and update Phase 0/1 checkboxes and wording without weakening third-party license tracking.
- [x] **Step 4:** Run `rg -n "Apache-2.0|HEIF|HEIC|Faz 1" DURUM.md docs LICENSE` and confirm every live document agrees.

### Task 2: Finish the M4 setup record

**Files:**
- Modify: `DURUM.md`

- [x] **Step 1:** Install `pnpm` with Homebrew because Node 25 no longer includes `corepack` on this machine.
- [x] **Step 2:** Run `pnpm --version`, `node --version`, `uv --version`, `uv python list --only-installed`, `git --version`, and `sw_vers`; confirm Python 3.12.13 is visible through uv.
- [x] **Step 3:** Record Apple M4, 16 GB, macOS 26.6, Node, pnpm, uv, Python, and Git versions in `DURUM.md`.

### Task 3: Bootstrap the Python package

**Files:**
- Create: `engine/pyproject.toml`
- Create: `engine/src/pixelmend_engine/__init__.py`
- Create: `engine/tests/test_paths.py`
- Create: `engine/src/pixelmend_engine/paths.py`
- Create: `engine/uv.lock`

- [x] **Step 1:** Create `pyproject.toml` for Python `>=3.12,<3.13`, Apache-2.0 metadata, `platformdirs`, and a pytest development group; create an empty documented package initializer.
- [x] **Step 2: Write the failing tests**

```python
import importlib
from pathlib import Path

import pytest
from platformdirs import user_cache_path


def _load_get_models_dir():
    try:
        module = importlib.import_module("pixelmend_engine.paths")
    except ModuleNotFoundError:
        pytest.fail("pixelmend_engine.paths is not implemented")
    return module.get_models_dir


def test_models_dir_defaults_to_pixelmend_platform_cache(monkeypatch) -> None:
    monkeypatch.delenv("PIXELMEND_MODELS_DIR", raising=False)

    assert _load_get_models_dir()() == Path(
        user_cache_path("PixelMend", appauthor=False)
    ) / "models"


def test_models_dir_honors_explicit_override(monkeypatch, tmp_path: Path) -> None:
    override = tmp_path / "model-store"
    monkeypatch.setenv("PIXELMEND_MODELS_DIR", str(override))

    assert _load_get_models_dir()() == override
```

- [x] **Step 3: Verify RED**

Run: `cd engine && uv run pytest tests/test_paths.py -v`

Expected: both tests fail with `pixelmend_engine.paths is not implemented`.

- [x] **Step 4: Write the minimal implementation**

```python
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
```

- [x] **Step 5: Verify GREEN**

Run: `cd engine && uv run pytest tests/test_paths.py -v`

Expected: both tests pass with no warnings.

- [x] **Step 6:** Run `git diff --check` and update `DURUM.md` with the exact test evidence. Do not commit without separate user approval.
