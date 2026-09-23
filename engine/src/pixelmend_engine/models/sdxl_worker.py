"""Optional isolated SDXL inpainting runtime with strict pixel composition."""

from pathlib import Path

import numpy as np
from PIL import Image

from ..model_package import verify_package
from ..sdxl_package import SDXL_INPAINTING_PACKAGE


class SDXLRuntimeUnavailable(RuntimeError):
    """Raised when the separately packaged diffusion runtime is unavailable."""


def context_box(mask: np.ndarray, *, maximum: int = 1024) -> tuple[int, int, int, int]:
    """Return a bounded context rectangle that includes every selected pixel."""
    if (mask.dtype != np.uint8 or mask.ndim != 2 or not np.any(mask)
            or maximum < 8):
        raise ValueError('a nonempty uint8 selection and positive context limit are required')
    height, width = mask.shape
    ys, xs = np.where(mask == 255)
    left, top, right, bottom = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    if right - left > maximum or bottom - top > maximum:
        raise ValueError('selection exceeds the advanced model context limit')
    padding = max(32, max(right - left, bottom - top) // 2)
    left, top = max(0, left - padding), max(0, top - padding)
    right, bottom = min(width, right + padding), min(height, bottom + padding)
    if right - left > maximum:
        right = min(width, left + maximum)
        left = max(0, right - maximum)
    if bottom - top > maximum:
        bottom = min(height, top + maximum)
        top = max(0, bottom - maximum)
    return left, top, right, bottom


def composite_selected(source: np.ndarray, candidate: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Publish only model pixels that the user deliberately selected."""
    if (source.dtype != np.uint8 or source.ndim != 3 or source.shape[2] != 3
            or candidate.shape != source.shape or candidate.dtype != np.uint8
            or mask.dtype != np.uint8 or mask.shape != source.shape[:2]
            or not np.all((mask == 0) | (mask == 255))):
        raise ValueError('source, candidate and binary selection shapes must match')
    return np.where(mask[:, :, None] == 255, candidate, source)


def _square(image: np.ndarray, mask: np.ndarray):
    height, width = image.shape[:2]
    side = max(height, width)
    bottom, right = side - height, side - width
    mode = 'reflect' if height > 1 and width > 1 else 'edge'
    return (np.pad(image, ((0, bottom), (0, right), (0, 0)), mode=mode),
            np.pad(mask, ((0, bottom), (0, right))), height, width)


def run_sdxl_inpaint(model_root: Path, source: np.ndarray, mask: np.ndarray, *, seed: int = 20260923,
                     prompt: str = 'realistic background, preserve the surrounding scene') -> tuple[np.ndarray, dict]:
    """Run SDXL locally, then enforce selection-only composition.

    Diffusers/Torch are deliberately optional: the main ONNX sidecar remains
    lightweight until the separately accepted advanced runtime is bundled.
    """
    root = verify_package(Path(model_root), SDXL_INPAINTING_PACKAGE)
    x0, y0, x1, y1 = context_box(mask)
    crop, selection = source[y0:y1, x0:x1], mask[y0:y1, x0:x1]
    square, square_mask, original_height, original_width = _square(crop, selection)
    try:
        import torch
        from diffusers import StableDiffusionXLInpaintPipeline
    except ImportError as error:
        raise SDXLRuntimeUnavailable('SDXL çalışma bileşeni bu uygulama paketinde kurulu değil.') from error
    device = 'mps' if torch.backends.mps.is_available() else 'cpu'
    try:
        pipeline = StableDiffusionXLInpaintPipeline.from_pretrained(
            str(root), torch_dtype=torch.float16 if device == 'mps' else torch.float32,
            local_files_only=True, use_safetensors=True,
        ).to(device)
        generator = torch.Generator(device=device).manual_seed(seed)
        generated = pipeline(
            prompt=prompt, image=Image.fromarray(square), mask_image=Image.fromarray(square_mask),
            height=512, width=512, num_inference_steps=30, guidance_scale=7.5, generator=generator,
        ).images[0]
    except Exception as error:
        raise SDXLRuntimeUnavailable('SDXL yerel çalıştırması başlatılamadı.') from error
    resized = np.asarray(generated.convert('RGB').resize((square.shape[1], square.shape[0]), Image.Resampling.LANCZOS))
    candidate = source.copy()
    candidate[y0:y1, x0:x1] = resized[:original_height, :original_width]
    return composite_selected(source, candidate, mask), {
        'backend': f'torch-{device}', 'seed': seed, 'context_box': [x0, y0, x1, y1],
        'prompt_mode': 'background_completion',
    }
