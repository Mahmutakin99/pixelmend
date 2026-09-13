"""Keep normalized source assets private to one sidecar session."""

from dataclasses import dataclass
from io import BytesIO
from uuid import uuid4
from threading import RLock
from time import monotonic
from contextlib import contextmanager

from .imageio import ImageAsset, ImageWarningCode, encode_preview_png, load_image


class AssetError(Exception):
    """Base error for opaque session asset operations."""


class AssetNotFoundError(AssetError):
    """Raised when an opaque asset identifier is unknown in this session."""


class AssetInUseError(AssetError):
    """Raised when a job still owns a reference to the source asset."""


class AssetCapacityError(AssetError):
    """Raised before committing an import beyond the session budget."""


@dataclass(frozen=True, slots=True)
class ImportedAsset:
    """Return only renderer-safe import facts; source paths never enter this type."""

    asset_id: str
    width: int
    height: int
    warnings: tuple[ImageWarningCode, ...]


@dataclass(slots=True)
class _StoredAsset:
    """Pair the canonical inference asset with its normalized preview bytes."""

    image: ImageAsset
    preview: bytes
    job_references: int = 0
    touched: float = 0

    @property
    def size_bytes(self):
        return self.image.rgb.nbytes + len(self.preview) + (
            self.image.alpha.nbytes if self.image.alpha is not None else 0)


class AssetStore:
    """Own in-memory assets for one sidecar process and their job references."""

    def __init__(self, *, max_assets=32, byte_budget=512 * 1024 * 1024,
                 ttl_seconds=3600) -> None:
        self._assets: dict[str, _StoredAsset] = {}
        self._lock = RLock()
        self.max_assets = max_assets
        self.byte_budget = byte_budget
        self.ttl_seconds = ttl_seconds

    @property
    def used_bytes(self):
        with self._lock:
            return sum(asset.size_bytes for asset in self._assets.values())

    def close(self):
        """Release all session data after worker shutdown."""
        with self._lock:
            self._assets.clear()

    def expire(self):
        """Expire only unused assets; active native jobs retain their source."""
        with self._lock:
            now = monotonic()
            for asset_id, stored in list(self._assets.items()):
                if not stored.job_references and now - stored.touched >= self.ttl_seconds:
                    del self._assets[asset_id]

    def import_image(self, source: BytesIO) -> ImportedAsset:
        """Normalize a source once and identify it with a non-path opaque token."""
        # Serialize decode to bound temporary allocations from concurrent uploads.
        with self._lock:
            if len(self._assets) >= self.max_assets:
                raise AssetCapacityError('asset count exceeded')
            image = load_image(source)
            stored = _StoredAsset(image=image, preview=encode_preview_png(image), touched=monotonic())
            if self.used_bytes + stored.size_bytes > self.byte_budget:
                raise AssetCapacityError('asset memory budget exceeded')
            asset_id = uuid4().hex
            self._assets[asset_id] = stored
        return ImportedAsset(
            asset_id=asset_id,
            width=image.width,
            height=image.height,
            warnings=image.warnings,
        )

    def preview_bytes(self, asset_id: str) -> bytes:
        """Return only the normalized preview for a known opaque identifier."""
        return self._get(asset_id).preview

    def get_image(self, asset_id: str) -> ImageAsset:
        """Return the canonical asset for engine jobs, never for renderer transport."""
        return self._get(asset_id).image

    def acquire_for_job(self, asset_id: str) -> None:
        """Pin an asset while an active job can still read its canonical pixels."""
        with self._lock:
            self._get(asset_id).job_references += 1

    def release_from_job(self, asset_id: str) -> None:
        """Release one previously acquired job reference without underflowing."""
        with self._lock:
            stored = self._get(asset_id)
            if stored.job_references:
                stored.job_references -= 1

    def delete(self, asset_id: str) -> None:
        """Dispose an idle asset; active jobs must finish or cancel first."""
        with self._lock:
            stored = self._get(asset_id)
            if stored.job_references:
                raise AssetInUseError(f"asset is in use: {asset_id}")
            del self._assets[asset_id]

    def contains(self, asset_id: str) -> bool:
        """Report whether this session still owns an opaque asset identifier."""
        with self._lock:
            return asset_id in self._assets

    def _get(self, asset_id: str) -> _StoredAsset:
        """Resolve a session asset without ever treating its id as a filesystem path."""
        try:
            with self._lock:
                stored = self._assets[asset_id]
                stored.touched = monotonic()
                return stored
        except KeyError as error:
            raise AssetNotFoundError(f"unknown asset: {asset_id}") from error
