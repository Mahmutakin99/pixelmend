"""Verified, atomic installation for multi-file model packages."""

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
from tempfile import TemporaryDirectory
from uuid import uuid4

from filelock import FileLock

_REVISION = re.compile(r'^[0-9a-f]{40}$')
_SHA256 = re.compile(r'^[0-9a-f]{64}$')


class ModelPackageError(ValueError):
    """Base error for a package that is unsafe, incomplete, or altered."""


class PackageMissingFileError(ModelPackageError):
    pass


class PackageHashMismatchError(ModelPackageError):
    pass


@dataclass(frozen=True, slots=True)
class ModelPackageFile:
    path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class ModelPackageManifest:
    model_id: str
    revision: str
    license_id: str
    license_url: str
    files: tuple[ModelPackageFile, ...]

    def __post_init__(self):
        if not isinstance(self.model_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', self.model_id):
            raise ValueError('model_id must be a safe identifier')
        if not isinstance(self.revision, str) or not _REVISION.fullmatch(self.revision):
            raise ValueError('revision must be a lowercase 40-character Git commit')
        if not isinstance(self.license_id, str) or not self.license_id.strip():
            raise ValueError('license_id must not be empty')
        if not isinstance(self.license_url, str) or not self.license_url.startswith('https://'):
            raise ValueError('license_url must be HTTPS')
        if not self.files:
            raise ValueError('files must not be empty')
        paths = set()
        for file in self.files:
            if not isinstance(file, ModelPackageFile):
                raise ValueError('files must contain ModelPackageFile values')
            member = PurePosixPath(file.path)
            if (not file.path or any(c in file.path for c in ('\\', ':', '\x00'))
                    or member.is_absolute() or '..' in member.parts or '.' in member.parts
                    or member.name != member.parts[-1] or str(member) != file.path or file.path in paths):
                raise ValueError('package file path must be a unique safe relative POSIX path')
            if isinstance(file.size_bytes, bool) or not isinstance(file.size_bytes, int) or file.size_bytes <= 0:
                raise ValueError('package file size must be positive')
            if not isinstance(file.sha256, str) or not _SHA256.fullmatch(file.sha256):
                raise ValueError('package file SHA-256 must be lowercase hexadecimal')
            paths.add(file.path)


def _checked_path(root: Path, relative_path: str) -> Path:
    target = root
    # `lstat` every component; checking only the leaf follows a directory link
    # before its file can be inspected.
    parts = PurePosixPath(relative_path).parts
    for index, part in enumerate(parts):
        target = target / part
        try:
            details = target.lstat()
        except FileNotFoundError:
            raise PackageMissingFileError(relative_path) from None
        if index < len(parts) - 1 and not stat.S_ISDIR(details.st_mode):
            raise PackageMissingFileError(relative_path)
    try:
        details = target.lstat()
    except FileNotFoundError:
        raise PackageMissingFileError(relative_path) from None
    if not stat.S_ISREG(details.st_mode):
        raise PackageMissingFileError(relative_path)
    return target


def _verify_file(root: Path, file: ModelPackageFile, cancel=None) -> None:
    path = _checked_path(root, file.path)
    if path.stat().st_size != file.size_bytes:
        raise PackageHashMismatchError(file.path)
    digest = hashlib.sha256()
    flags = os.O_RDONLY
    if os.name != 'nt':
        flags |= os.O_NOFOLLOW | os.O_NONBLOCK
    with os.fdopen(os.open(path, flags), 'rb') as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size != file.size_bytes:
            raise PackageHashMismatchError(file.path)
        while chunk := handle.read(1024 * 1024):
            if cancel is not None and cancel.is_set():
                raise InterruptedError('model package operation cancelled')
            digest.update(chunk)
        after = os.fstat(handle.fileno())
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise PackageHashMismatchError(file.path)
    if digest.hexdigest() != file.sha256:
        raise PackageHashMismatchError(file.path)


def verify_package(root: Path, manifest: ModelPackageManifest, *, cancel=None) -> Path:
    """Return only a fully present and hash-verified immutable package root."""
    root = Path(root)
    try:
        details = root.lstat()
    except FileNotFoundError:
        raise PackageMissingFileError('package') from None
    if not stat.S_ISDIR(details.st_mode):
        raise PackageMissingFileError('package')
    for file in manifest.files:
        _verify_file(root, file, cancel)
    return root


PackageDownloader = Callable[[ModelPackageFile, Path, object | None, Callable[[int], None]], None]


def install_package(models_dir: Path, manifest: ModelPackageManifest, downloader: PackageDownloader, *, cancel=None) -> Path:
    """Stage every file, verify the set, then atomically activate its revision.

    A previously healthy package is reused. An old corrupt package remains in
    place while its complete replacement is staged, so no caller ever receives
    a partial revision directory.
    """
    models_dir = Path(models_dir).absolute()
    parent = models_dir / manifest.model_id
    target = parent / manifest.revision
    parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(parent / f'.{manifest.revision}.lock')
    with lock:
        try:
            return verify_package(target, manifest, cancel=cancel)
        except ModelPackageError:
            pass
        with TemporaryDirectory(prefix=f'.{manifest.revision}.partial-', dir=parent) as temporary:
            staged = Path(temporary) / manifest.revision
            staged.mkdir()
            for file in manifest.files:
                if cancel is not None and cancel.is_set():
                    raise InterruptedError('model package operation cancelled')
                destination = staged.joinpath(*PurePosixPath(file.path).parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                downloader(file, destination, cancel, lambda count: None)
                _verify_file(staged, file, cancel)
            verify_package(staged, manifest, cancel=cancel)
            backup = None
            if target.exists():
                backup = parent / f'.{manifest.revision}.invalid-{uuid4().hex}'
                os.replace(target, backup)
            try:
                os.replace(staged, target)
            except Exception:
                if backup is not None and backup.exists():
                    os.replace(backup, target)
                raise
            if backup is not None:
                shutil.rmtree(backup)
    return target
