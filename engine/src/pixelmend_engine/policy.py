"""One operator-owned resource policy shared with the desktop via capabilities."""

from dataclasses import asdict, dataclass
import os
import shutil

import psutil


class ResourceLimitError(ValueError):
    """A safe, renderer-readable admission failure before allocating resources."""

    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class ResourcePolicy:
    max_output_pixels: int = 200_000_000
    result_budget_bytes: int = 1024**3
    asset_budget_bytes: int = 2 * 1024**3
    tile_size: int = 128
    tile_overlap: int = 16

    def as_dict(self):
        return asdict(self)


def load_policy():
    """Only the sidecar launch environment may override the output ceiling."""
    pixels = int(os.environ.get('PIXELMEND_MAX_OUTPUT_PIXELS', '200000000'))
    if pixels < 1 or pixels > 1_000_000_000:
        raise ValueError('PIXELMEND_MAX_OUTPUT_PIXELS must be between 1 and 1000000000')
    return ResourcePolicy(max_output_pixels=pixels)


POLICY = load_policy()


def validate_dimensions(width, height, *, policy=POLICY):
    if (type(width) is not int or type(height) is not int or width < 1 or height < 1
            or width * height > policy.max_output_pixels):
        raise ResourceLimitError('output_limit', f'Çıktı en fazla {policy.max_output_pixels / 1e6:g} MP olabilir; pozitif tam ölçüler girin.')


def admit_image_job(image, target_size, *, ai=False, result_bytes=0, policy=POLICY,
                    temp_dir=None, available_bytes=None, disk_free_bytes=None):
    """Account separately for result quota, working RAM and mapped tile storage."""
    width, height = target_size
    validate_dimensions(width, height, policy=policy)
    natural_pixels = image.width * image.height * 16 if ai else 0
    if natural_pixels > policy.max_output_pixels:
        raise ResourceLimitError('intermediate_limit', 'AI 4× ara çıktısı piksel sınırını aşıyor. Daha küçük kaynak veya Lanczos seçin.')
    output_bytes = width * height * (4 if image.alpha is not None else 3)
    if output_bytes + result_bytes > policy.result_budget_bytes:
        raise ResourceLimitError('result_budget', 'Sonuç belleği dolu. Önceki sonuçları kapatın veya daha küçük ölçü seçin.')
    # Includes Pillow conversions, RGB output, alpha and bounded native workspace.
    required = output_bytes * 4 + natural_pixels * 3 + (1024**3 if ai else 128 * 1024**2)
    available = psutil.virtual_memory().available if available_bytes is None else available_bytes
    if required + 256 * 1024**2 > available:
        raise ResourceLimitError('memory_limit', 'İşlem için yeterli kullanılabilir bellek yok. Diğer uygulamaları kapatın veya ölçüyü küçültün.')
    if ai:
        free = shutil.disk_usage(temp_dir).free if disk_free_bytes is None else disk_free_bytes
        # RGB float accumulation + weight plane; mappings are session-owned.
        if free < natural_pixels * 16 + 256 * 1024**2:
            raise ResourceLimitError('disk_full', 'AI karo birleştirmesi için geçici disk alanı yetersiz.')
