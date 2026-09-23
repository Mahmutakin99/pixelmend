"""Application-owned allowlist; unpublished artifacts never get invented metadata."""

from dataclasses import dataclass

from .model_store import LAMA_ONNX_MANIFEST, ModelManifest


@dataclass(frozen=True, slots=True)
class ModelCatalogEntry:
    id: str
    name: str
    manifest: ModelManifest | None
    source: str = "published"
    operation: str = ""
    tier: str = ""
    description: str = ""
    minimum_memory_bytes: int | None = None
    recommended_memory_bytes: int | None = None


REALESRGAN_LOCAL_MANIFEST = ModelManifest(
    model_id='realesrgan-x4plus', repo_id='Mahmutakin99/pixelmend-models',
    revision='1b35dd5d60b75067eec696cc7bce18f83ba94693',
    filename='realesrgan-x4plus-fp32.onnx', size_bytes=67051639,
    sha256='3d05f9cecd652841eeb408ceb02c360e48115eaba33c807894a06e6a00218fbc',
    license_id='BSD-3-Clause',
    license_url='https://raw.githubusercontent.com/xinntao/Real-ESRGAN/a4abfb2979a7bbff3f69f58f58ae324608821e27/LICENSE',
    download_url='https://github.com/Mahmutakin99/pixelmend-models/releases/download/models-2026-09-21/realesrgan-x4plus-fp32.onnx',
)
REALESRGAN_GENERAL_MANIFEST = ModelManifest(
    model_id='realesrgan-general-x4v3', repo_id='Mahmutakin99/pixelmend-models',
    revision='1b35dd5d60b75067eec696cc7bce18f83ba94693',
    filename='realesrgan-general-x4v3-fp32.onnx', size_bytes=4866417,
    sha256='1d6af9380cc478cabbb59349e0be704c77245fea4fe4797c7437e87a6b326e23',
    license_id='BSD-3-Clause', license_url=REALESRGAN_LOCAL_MANIFEST.license_url,
    download_url='https://github.com/Mahmutakin99/pixelmend-models/releases/download/models-2026-09-21/realesrgan-general-x4v3-fp32.onnx',
)
MIGAN_MANIFEST = ModelManifest(
    model_id='migan-512-places2', repo_id='andraniksargsyan/migan',
    revision='406830d0fa60666da0071c342ad2fbc8f30c5c64',
    filename='migan_pipeline_v2.onnx', size_bytes=28_079_181,
    sha256='6f1f3530a1a2324b19752018ce756088b07973cda8d7d890034ace5c8a48c40b',
    license_id='MIT',
    license_url='https://github.com/Picsart-AI-Research/MI-GAN/blob/main/LICENSE-WEIGHTS',
)

UPSCALE_MODELS = {'realesrgan_x4plus': 'realesrgan-x4plus',
                  'realesrgan_general_x4v3': 'realesrgan-general-x4v3'}
INPAINT_MODELS = {'lama': 'lama', 'migan_512_places2': 'migan-512-places2'}
AI_MODELS = {**INPAINT_MODELS, **UPSCALE_MODELS}

DEFAULT_MODEL_CATALOG = (
    # Only artifacts with a pinned manifest can be installed. The other tier
    # entries make the intended product hierarchy visible without pretending an
    # unmeasured download or licence review is a usable model.
    ModelCatalogEntry('migan-512-places2', 'MI-GAN 512 Places2', MIGAN_MANIFEST, operation='remove', tier='fast',
                      description='Daha düşük sistem gereksinimleri ve kısa bekleme süresi için önerilir. İnce ayrıntılarda daha sınırlı sonuç verebilir.'),
    ModelCatalogEntry('lama', 'LaMa', LAMA_ONNX_MANIFEST, operation='remove', tier='balanced',
                      description='Günlük kullanım için önerilir. İşlem süresi ve ayrıntı kalitesini dengeler.'),
    ModelCatalogEntry('sdxl-inpainting', 'SDXL Inpainting', None, operation='remove', tier='advanced',
                      description='Güçlü sistemler ve zor görseller için önerilir. Daha fazla bellek kullanabilir ve daha uzun sürebilir.'),
    ModelCatalogEntry('realesrgan-general-x4v3', 'RealESRGAN General x4v3', REALESRGAN_GENERAL_MANIFEST, operation='upscale', tier='fast',
                      description='Daha düşük sistem gereksinimleri ve kısa bekleme süresi için önerilir. İnce ayrıntılarda daha sınırlı sonuç verebilir.'),
    ModelCatalogEntry('realesrgan-x4plus', 'RealESRGAN x4plus', REALESRGAN_LOCAL_MANIFEST, operation='upscale', tier='balanced',
                      description='Günlük kullanım için önerilir. İşlem süresi ve ayrıntı kalitesini dengeler.'),
    ModelCatalogEntry('real-hat-gan-x4', 'Real HAT GAN x4', None, operation='upscale', tier='advanced',
                      description='Güçlü sistemler ve zor görseller için önerilir. Resmî ağırlığın dağıtım koşulları doğrulanana kadar kurulum sunulmuyor.'),
)
