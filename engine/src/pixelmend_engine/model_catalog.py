"""Application-owned allowlist; unpublished artifacts never get invented metadata."""

from dataclasses import dataclass

from .model_store import LAMA_ONNX_MANIFEST, ModelManifest


@dataclass(frozen=True, slots=True)
class ModelCatalogEntry:
    id: str
    name: str
    manifest: ModelManifest | None
    source: str = "published"


# Locally reproduced export, parity evidence in docs/verification. No public URL is claimed.
REALESRGAN_LOCAL_MANIFEST = ModelManifest(
    model_id='realesrgan-x4plus', repo_id='local/real-esrgan-x4plus',
    revision='c4e5303b53044767c94bb78f49365cb710ee459e',
    filename='realesrgan-x4plus-fp32.onnx', size_bytes=67051639,
    sha256='3d05f9cecd652841eeb408ceb02c360e48115eaba33c807894a06e6a00218fbc',
    license_id='BSD-3-Clause',
    license_url='https://raw.githubusercontent.com/xinntao/Real-ESRGAN/a4abfb2979a7bbff3f69f58f58ae324608821e27/LICENSE',
)
DEFAULT_MODEL_CATALOG = (
    ModelCatalogEntry('lama', 'LaMa', LAMA_ONNX_MANIFEST),
    ModelCatalogEntry('realesrgan-x4plus', 'RealESRGAN x4plus', REALESRGAN_LOCAL_MANIFEST, 'local'),
)
