"""One operator-owned resource policy shared with the desktop via capabilities."""

from dataclasses import asdict, dataclass
import os
import shutil
import tempfile

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


def inference_settings(resource_mode: str):
    """Return the explicit bounded native settings for one user-selected mode."""
    if resource_mode == 'automatic':
        return {'tile_size': POLICY.tile_size, 'tile_overlap': POLICY.tile_overlap, 'intra_op_threads': 4}
    if resource_mode == 'low-resource':
        # Smaller tiles reduce peak native allocation; fewer ORT threads avoid
        # fighting foreground UI and other processes for unified memory.
        return {'tile_size': 64, 'tile_overlap': 8, 'intra_op_threads': 2}
    raise ValueError('invalid resource mode')


def adaptive_output_limit(image, *, ai: bool, result_bytes=0, policy=POLICY,
                          available_bytes=None, disk_free_bytes=None):
    """Return the largest safe final pixel count for the current machine state.

    The value is advisory for the UI. ``admit_image_job`` remains the final
    admission gate because memory and disk can change between display and run.
    """
    available = psutil.virtual_memory().available if available_bytes is None else available_bytes
    free = shutil.disk_usage(tempfile.gettempdir()).free if disk_free_bytes is None else disk_free_bytes
    channels = 4 if getattr(image, 'alpha', None) is not None else 3
    # Final RGB/alpha plus conversions, a 256 MiB system reserve and a 25% headroom.
    per_output_pixel = channels * 4 * 1.25
    ram_pixels = max(0, int((available - 256 * 1024**2 - result_bytes) / per_output_pixel))
    if not ai:
        return min(policy.max_output_pixels, ram_pixels)
    # AI also needs a float output workspace and a disk-backed accumulation map.
    ai_ram_pixels = max(0, int((available - 512 * 1024**2 - result_bytes) / (per_output_pixel + 24)))
    # Disk-backed maps scale with the model's natural 4× source output, not
    # with a smaller/larger final resample target.
    workspace = image.width * image.height * 16 + 256 * 1024**2
    disk_limit = policy.max_output_pixels if free >= workspace else 0
    return min(policy.max_output_pixels, ram_pixels, ai_ram_pixels, disk_limit)


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
        free = shutil.disk_usage(temp_dir or tempfile.gettempdir()).free if disk_free_bytes is None else disk_free_bytes
        # RGB float accumulation + weight plane; mappings are session-owned.
        if free < natural_pixels * 16 + 256 * 1024**2:
            raise ResourceLimitError('disk_full', 'AI karo birleştirmesi için geçici disk alanı yetersiz.')
    adaptive = adaptive_output_limit(image, ai=ai, result_bytes=result_bytes, policy=policy,
                                     available_bytes=available_bytes, disk_free_bytes=disk_free_bytes)
    if width * height > adaptive:
        raise ResourceLimitError('adaptive_limit',
            f'Bu işlem için kullanılabilir çıktı sınırı {adaptive / 1e6:.1f} MP. '
            'Daha küçük bir ölçü seçin veya sistemde bellek ve disk alanı açın.')
