from dataclasses import FrozenInstanceError
from pathlib import Path

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


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("model_id", ""),
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
