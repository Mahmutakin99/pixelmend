"""Application-owned allowlist; unpublished artifacts never get invented metadata."""

from dataclasses import dataclass

from .model_store import LAMA_ONNX_MANIFEST, ModelManifest


@dataclass(frozen=True, slots=True)
class ModelCatalogEntry:
    id: str
    name: str
    manifest: ModelManifest | None


# RealESRGAN remains unavailable until a published immutable export passes parity.
DEFAULT_MODEL_CATALOG = (
    ModelCatalogEntry('lama', 'LaMa', LAMA_ONNX_MANIFEST),
    ModelCatalogEntry('realesrgan-x4plus', 'RealESRGAN x4plus', None),
)
