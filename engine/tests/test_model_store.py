from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from pathlib import Path
from threading import Event, Lock
from typing import Any

import huggingface_hub
import pytest

import pixelmend_engine.model_store as model_store
from pixelmend_engine.model_store import (
    InvalidModelManifestError,
    ModelFileMissingError,
    ModelHashMismatchError,
    ModelManifest,
    ModelSizeMismatchError,
    verify_model_file,
)

VALID_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
VALID_REVISION = "1" * 40
MISMATCHED_SHA256 = "a52d159f262b2c6ddb724a61840befc36eb30c88877a4030b65cbe86298449c9"


def test_lama_manifest_matches_pinned_hugging_face_artifact() -> None:
    assert model_store.LAMA_ONNX_MANIFEST == ModelManifest(
        model_id="lama",
        repo_id="Carve/LaMa-ONNX",
        revision="a3ee2fca54baebec351b8fa7786154ffa7555aa6",
        filename="lama_fp32.onnx",
        size_bytes=208_044_816,
        sha256="1faef5301d78db7dda502fe59966957ec4b79dd64e16f03ed96913c7a4eb68d6",
        license_id="Apache-2.0",
        license_url=(
            "https://huggingface.co/Carve/LaMa-ONNX/blob/"
            "a3ee2fca54baebec351b8fa7786154ffa7555aa6/README.md"
        ),
    )


def _manifest_values() -> dict[str, object]:
    return {
        "model_id": "test-model",
        "repo_id": "example/test-model",
        "revision": VALID_REVISION,
        "filename": "model.onnx",
        "size_bytes": 3,
        "sha256": VALID_SHA256,
        "license_id": "Apache-2.0",
        "license_url": "https://www.apache.org/licenses/LICENSE-2.0.txt",
    }


def test_manifest_is_immutable() -> None:
    manifest = ModelManifest(**_manifest_values())

    with pytest.raises(FrozenInstanceError):
        manifest.filename = "replacement.onnx"


def test_model_file_path_is_scoped_by_model_and_revision(tmp_path: Path) -> None:
    manifest = ModelManifest(**_manifest_values())

    assert model_store.model_file_path(tmp_path, manifest) == (
        tmp_path / manifest.model_id / manifest.revision / manifest.filename
    )


def test_hugging_face_download_uses_only_pinned_manifest_coordinates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = ModelManifest(**_manifest_values())
    destination = tmp_path / "staging" / manifest.filename
    destination.parent.mkdir()
    observed: dict[str, Any] = {}

    def fake_hf_hub_download(**kwargs: Any) -> str:
        observed.update(kwargs)
        destination.write_bytes(b"abc")
        return str(destination)

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", fake_hf_hub_download)

    model_store.download_hugging_face_model(manifest, destination)

    assert observed == {
        "repo_id": manifest.repo_id,
        "filename": manifest.filename,
        "repo_type": "model",
        "revision": manifest.revision,
        "local_dir": destination.parent,
        "token": False,
    }


def test_acquire_model_validates_staging_before_atomic_activation(
    tmp_path: Path,
) -> None:
    manifest = ModelManifest(**_manifest_values())
    target = model_store.model_file_path(tmp_path, manifest)
    candidates: list[Path] = []

    def download(candidate_manifest: ModelManifest, candidate: Path) -> None:
        assert candidate_manifest is manifest
        assert candidate.parent.parent == target.parent
        assert not target.exists()
        candidates.append(candidate)
        candidate.write_bytes(b"abc")

    acquired = model_store.acquire_model(tmp_path, manifest, downloader=download)

    assert acquired == target
    assert target.read_bytes() == b"abc"
    assert len(candidates) == 1
    assert not candidates[0].parent.exists()


def test_acquire_model_reuses_a_valid_cached_file(tmp_path: Path) -> None:
    manifest = ModelManifest(**_manifest_values())
    target = model_store.model_file_path(tmp_path, manifest)
    target.parent.mkdir(parents=True)
    target.write_bytes(b"abc")

    def unexpected_download(_: ModelManifest, __: Path) -> None:
        raise AssertionError("valid cached files must not be downloaded again")

    assert (
        model_store.acquire_model(tmp_path, manifest, downloader=unexpected_download)
        == target
    )


@pytest.mark.parametrize("invalid_cached_bytes", [b"abcd", b"abd"])
def test_acquire_model_repairs_an_invalid_cached_file(
    tmp_path: Path,
    invalid_cached_bytes: bytes,
) -> None:
    manifest = ModelManifest(**_manifest_values())
    target = model_store.model_file_path(tmp_path, manifest)
    target.parent.mkdir(parents=True)
    target.write_bytes(invalid_cached_bytes)

    def download(_: ModelManifest, candidate: Path) -> None:
        candidate.write_bytes(b"abc")

    assert model_store.acquire_model(tmp_path, manifest, downloader=download) == target
    assert target.read_bytes() == b"abc"


@pytest.mark.parametrize(
    ("invalid_candidate", "expected_error"),
    [
        (b"abcd", ModelSizeMismatchError),
        (b"abd", ModelHashMismatchError),
    ],
)
def test_acquire_model_rejects_invalid_staging_without_replacing_cache(
    tmp_path: Path,
    invalid_candidate: bytes,
    expected_error: type[Exception],
) -> None:
    manifest = ModelManifest(**_manifest_values())
    target = model_store.model_file_path(tmp_path, manifest)
    target.parent.mkdir(parents=True)
    target.write_bytes(b"existing-invalid-cache")
    candidates: list[Path] = []

    def download(_: ModelManifest, candidate: Path) -> None:
        candidates.append(candidate)
        candidate.write_bytes(invalid_candidate)

    with pytest.raises(expected_error):
        model_store.acquire_model(tmp_path, manifest, downloader=download)

    assert target.read_bytes() == b"existing-invalid-cache"
    assert len(candidates) == 1
    assert not candidates[0].parent.exists()


def test_acquire_model_wraps_download_failure_and_cleans_staging(
    tmp_path: Path,
) -> None:
    manifest = ModelManifest(**_manifest_values())
    target = model_store.model_file_path(tmp_path, manifest)
    candidates: list[Path] = []

    def fail_download(_: ModelManifest, candidate: Path) -> None:
        candidates.append(candidate)
        candidate.write_bytes(b"partial")
        raise RuntimeError("network interrupted")

    with pytest.raises(model_store.ModelDownloadError) as caught:
        model_store.acquire_model(tmp_path, manifest, downloader=fail_download)

    assert caught.value.model_id == manifest.model_id
    assert isinstance(caught.value.__cause__, RuntimeError)
    assert not target.exists()
    assert len(candidates) == 1
    assert not candidates[0].parent.exists()


def test_acquire_model_rejects_a_missing_staged_file(tmp_path: Path) -> None:
    manifest = ModelManifest(**_manifest_values())
    candidates: list[Path] = []

    def download_nothing(_: ModelManifest, candidate: Path) -> None:
        candidates.append(candidate)

    with pytest.raises(ModelFileMissingError):
        model_store.acquire_model(tmp_path, manifest, downloader=download_nothing)

    assert len(candidates) == 1
    assert not candidates[0].parent.exists()


def test_acquire_model_cleans_staging_when_atomic_activation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = ModelManifest(**_manifest_values())
    target = model_store.model_file_path(tmp_path, manifest)
    candidates: list[Path] = []

    def download(_: ModelManifest, candidate: Path) -> None:
        candidates.append(candidate)
        candidate.write_bytes(b"abc")

    def fail_replace(_: Path, __: Path) -> None:
        raise OSError("atomic activation failed")

    monkeypatch.setattr(model_store.os, "replace", fail_replace)

    with pytest.raises(OSError, match="atomic activation failed"):
        model_store.acquire_model(tmp_path, manifest, downloader=download)

    assert not target.exists()
    assert len(candidates) == 1
    assert not candidates[0].parent.exists()


def test_acquire_model_serializes_concurrent_downloads(tmp_path: Path) -> None:
    manifest = ModelManifest(**_manifest_values())
    target = model_store.model_file_path(tmp_path, manifest)
    first_download_started = Event()
    release_first_download = Event()
    second_download_started = Event()
    count_lock = Lock()
    download_count = 0

    def download(_: ModelManifest, candidate: Path) -> None:
        nonlocal download_count
        with count_lock:
            download_count += 1
            invocation = download_count

        if invocation == 1:
            first_download_started.set()
            assert release_first_download.wait(timeout=2)
        else:
            second_download_started.set()

        candidate.write_bytes(b"abc")

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            model_store.acquire_model,
            tmp_path,
            manifest,
            downloader=download,
        )
        assert first_download_started.wait(timeout=2)
        second = pool.submit(
            model_store.acquire_model,
            tmp_path,
            manifest,
            downloader=download,
        )

        try:
            assert not second_download_started.wait(timeout=0.2)
        finally:
            release_first_download.set()

        assert first.result(timeout=2) == target
        assert second.result(timeout=2) == target

    assert download_count == 1


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("model_id", ""),
        ("model_id", "nested/model"),
        ("model_id", "nested\\model"),
        ("model_id", "."),
        ("model_id", ".."),
        ("repo_id", " "),
        ("revision", "main"),
        ("revision", 123),
        ("filename", ""),
        ("filename", 123),
        ("filename", "nested/model.onnx"),
        ("filename", "nested\\model.onnx"),
        ("size_bytes", 0),
        ("size_bytes", True),
        ("sha256", "not-a-sha256"),
        ("sha256", 123),
        ("license_id", ""),
        ("license_url", " "),
    ],
)
def test_manifest_rejects_values_that_cannot_identify_one_immutable_file(
    field: str,
    invalid_value: object,
) -> None:
    values = _manifest_values()
    values[field] = invalid_value

    with pytest.raises(InvalidModelManifestError):
        ModelManifest(**values)


def test_verify_model_file_accepts_exact_size_and_sha256(tmp_path: Path) -> None:
    model_path = tmp_path / "model.onnx"
    model_path.write_bytes(b"abc")
    manifest = ModelManifest(**_manifest_values())

    assert verify_model_file(model_path, manifest) == model_path


def test_verify_model_file_reports_a_missing_file(tmp_path: Path) -> None:
    model_path = tmp_path / "missing.onnx"
    manifest = ModelManifest(**_manifest_values())

    with pytest.raises(ModelFileMissingError) as caught:
        verify_model_file(model_path, manifest)

    assert caught.value.path == model_path


def test_verify_model_file_rejects_wrong_byte_size(tmp_path: Path) -> None:
    model_path = tmp_path / "model.onnx"
    model_path.write_bytes(b"abcd")
    manifest = ModelManifest(**_manifest_values())

    with pytest.raises(ModelSizeMismatchError) as caught:
        verify_model_file(model_path, manifest)

    assert caught.value.path == model_path
    assert caught.value.expected_size == 3
    assert caught.value.actual_size == 4


def test_verify_model_file_rejects_wrong_sha256(tmp_path: Path) -> None:
    model_path = tmp_path / "model.onnx"
    model_path.write_bytes(b"abd")
    manifest = ModelManifest(**_manifest_values())

    with pytest.raises(ModelHashMismatchError) as caught:
        verify_model_file(model_path, manifest)

    assert caught.value.path == model_path
    assert caught.value.expected_sha256 == VALID_SHA256
    assert caught.value.actual_sha256 == MISMATCHED_SHA256
