"""Keep normalized source assets private to one sidecar session."""

from dataclasses import dataclass
from io import BytesIO
from uuid import uuid4

from .imageio import ImageAsset, ImageWarningCode, encode_preview_png, load_image


class AssetError(Exception):
    """Base error for opaque session asset operations."""


class AssetNotFoundError(AssetError):
    """Raised when an opaque asset identifier is unknown in this session."""


class AssetInUseError(AssetError):
    """Raised when a job still owns a reference to the source asset."""


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


class AssetStore:
    """Own in-memory assets for one sidecar process and their job references."""

    def __init__(self) -> None:
        self._assets: dict[str, _StoredAsset] = {}

    def import_image(self, source: BytesIO) -> ImportedAsset:
        """Normalize a source once and identify it with a non-path opaque token."""
        image = load_image(source)
        asset_id = uuid4().hex
        self._assets[asset_id] = _StoredAsset(
            image=image,
            preview=encode_preview_png(image),
        )
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
        self._get(asset_id).job_references += 1

    def release_from_job(self, asset_id: str) -> None:
        """Release one previously acquired job reference without underflowing."""
        stored = self._get(asset_id)
        if stored.job_references:
            stored.job_references -= 1

    def delete(self, asset_id: str) -> None:
        """Dispose an idle asset; active jobs must finish or cancel first."""
        stored = self._get(asset_id)
        if stored.job_references:
            raise AssetInUseError(f"asset is in use: {asset_id}")
        del self._assets[asset_id]

    def contains(self, asset_id: str) -> bool:
        """Report whether this session still owns an opaque asset identifier."""
        return asset_id in self._assets

    def _get(self, asset_id: str) -> _StoredAsset:
        """Resolve a session asset without ever treating its id as a filesystem path."""
        try:
            return self._assets[asset_id]
        except KeyError as error:
            raise AssetNotFoundError(f"unknown asset: {asset_id}") from error
