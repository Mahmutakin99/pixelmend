"""Define model manifests and verify sidecar-owned model files."""

import hashlib
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from tempfile import TemporaryDirectory

import huggingface_hub
from filelock import FileLock

_GIT_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ModelStoreError(Exception):
    """Base error for model manifest and file integrity failures."""


class InvalidModelManifestError(ModelStoreError):
    """Raised when a manifest cannot identify one immutable model file."""


class ModelDownloadError(ModelStoreError):
    """Raised when a model transport fails before integrity verification."""

    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        super().__init__(f"model download failed: {model_id}")


class ModelFileMissingError(ModelStoreError):
    """Raised when the candidate model path is not a regular file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(f"model file does not exist: {path}")


class ModelSizeMismatchError(ModelStoreError):
    """Raised before hashing when a model file has the wrong byte size."""

    def __init__(self, path: Path, expected_size: int, actual_size: int) -> None:
        self.path = path
        self.expected_size = expected_size
        self.actual_size = actual_size
        super().__init__(
            f"model size mismatch for {path}: "
            f"expected {expected_size} bytes, got {actual_size}"
        )


class ModelHashMismatchError(ModelStoreError):
    """Raised when a model file does not match its manifest SHA-256."""

    def __init__(
        self,
        path: Path,
        expected_sha256: str,
        actual_sha256: str,
    ) -> None:
        self.path = path
        self.expected_sha256 = expected_sha256
        self.actual_sha256 = actual_sha256
        super().__init__(
            f"model SHA-256 mismatch for {path}: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )


@dataclass(frozen=True, slots=True)
class ModelManifest:
    """Describe one immutable model artifact and its license record."""

    model_id: str
    repo_id: str
    revision: str
    filename: str
    size_bytes: int
    sha256: str
    license_id: str
    license_url: str

    def __post_init__(self) -> None:
        """Reject manifests that are mutable, incomplete, or path-shaped."""
        for field_name in (
            "model_id",
            "repo_id",
            "filename",
            "license_id",
            "license_url",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise InvalidModelManifestError(f"{field_name} must not be empty")

        if not isinstance(self.revision, str) or not _GIT_REVISION_PATTERN.fullmatch(
            self.revision
        ):
            raise InvalidModelManifestError(
                "revision must be a lowercase 40-character Git commit"
            )

        for field_name in ("model_id", "filename"):
            value = getattr(self, field_name)
            if (
                value in {".", ".."}
                or PurePosixPath(value).name != value
                or PureWindowsPath(value).name != value
            ):
                raise InvalidModelManifestError(
                    f"{field_name} must not contain path components"
                )

        if (
            isinstance(self.size_bytes, bool)
            or not isinstance(self.size_bytes, int)
            or self.size_bytes <= 0
        ):
            raise InvalidModelManifestError("size_bytes must be a positive integer")

        if not isinstance(self.sha256, str) or not _SHA256_PATTERN.fullmatch(
            self.sha256
        ):
            raise InvalidModelManifestError(
                "sha256 must be a lowercase 64-character hexadecimal digest"
            )


ModelDownloader = Callable[[ModelManifest, Path], None]


# Pin the repository revision as well as the file digest so moving branches
# cannot silently replace the model or its license record.
LAMA_ONNX_MANIFEST = ModelManifest(
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


def model_file_path(models_dir: Path, manifest: ModelManifest) -> Path:
    """Return the sidecar-owned path for one immutable model revision."""
    return models_dir / manifest.model_id / manifest.revision / manifest.filename


def download_hugging_face_model(
    manifest: ModelManifest,
    destination: Path,
) -> None:
    """Download one pinned public model into its isolated staging directory."""
    huggingface_hub.hf_hub_download(
        repo_id=manifest.repo_id,
        filename=manifest.filename,
        repo_type="model",
        revision=manifest.revision,
        local_dir=destination.parent,
        token=False,
    )


def verify_model_file(path: Path, manifest: ModelManifest) -> Path:
    """Return a model path only after its size and SHA-256 match the manifest."""
    if not path.is_file():
        raise ModelFileMissingError(path)

    actual_size = path.stat().st_size
    if actual_size != manifest.size_bytes:
        raise ModelSizeMismatchError(path, manifest.size_bytes, actual_size)

    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        # Model weights can be large, so integrity checking must stay bounded in RAM.
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)

    actual_sha256 = digest.hexdigest()
    if actual_sha256 != manifest.sha256:
        raise ModelHashMismatchError(path, manifest.sha256, actual_sha256)

    return path


def acquire_model(
    models_dir: Path,
    manifest: ModelManifest,
    *,
    downloader: ModelDownloader = download_hugging_face_model,
) -> Path:
    """Return a cached model or atomically activate one verified download."""
    target = model_file_path(models_dir, manifest)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock_path = target.with_name(f".{target.name}.lock")

    with FileLock(lock_path):
        try:
            return verify_model_file(target, manifest)
        except (
            ModelFileMissingError,
            ModelSizeMismatchError,
            ModelHashMismatchError,
        ):
            pass

        # Staging beside the target keeps os.replace on one filesystem.
        with TemporaryDirectory(
            dir=target.parent,
            prefix=f".{target.name}.partial-",
        ) as staging_dir:
            candidate = Path(staging_dir) / manifest.filename
            try:
                downloader(manifest, candidate)
            except Exception as error:
                raise ModelDownloadError(manifest.model_id) from error
            verify_model_file(candidate, manifest)
            os.replace(candidate, target)

        return target
