"""Optional isolated SDXL inpainting runtime with strict pixel composition."""

from pathlib import Path

import numpy as np
from PIL import Image

from ..model_package import verify_package
from ..sdxl_package import SDXL_INPAINTING_PACKAGE
from .realesrgan_onnx import InferenceCancelled, check_cancel


class SDXLRuntimeUnavailable(RuntimeError):
    """Raised when the separately packaged diffusion runtime is unavailable."""


def context_box(mask: np.ndarray, *, maximum: int = 1024) -> tuple[int, int, int, int]:
    """Return a bounded context rectangle that includes every selected pixel."""
    if (mask.dtype != np.uint8 or mask.ndim != 2 or not np.any(mask == 255)
            or not np.all((mask == 0) | (mask == 255)) or maximum < 8):
        raise ValueError('a nonempty binary uint8 selection and positive context limit are required')
    height, width = mask.shape
    ys, xs = np.where(mask == 255)
    left, top, right, bottom = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    if right - left > maximum or bottom - top > maximum:
        raise ValueError('selection exceeds the advanced model context limit')
    padding = max(32, max(right - left, bottom - top) // 2)
    def axis(start,end,dimension):
        length=min(maximum,dimension,end-start+2*padding)
        origin=max(0,min((start+end-length)//2,dimension-length))
        return origin,origin+length
    left,right=axis(left,right,width)
    top,bottom=axis(top,bottom,height)
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
                     prompt: str = 'realistic background, preserve the surrounding scene',
                     cancel_event=None) -> tuple[np.ndarray, dict]:
    """Run SDXL locally, then enforce selection-only composition.

    Diffusers/Torch are deliberately optional: the main ONNX sidecar remains
    lightweight until the separately accepted advanced runtime is bundled.
    """
    if (source.dtype != np.uint8 or source.ndim != 3 or source.shape[2] != 3
            or mask.ndim != 2 or mask.shape != source.shape[:2]):
        raise ValueError('source and selection dimensions must match RGB image dimensions')
    context_box(mask)
    check_cancel(cancel_event)
    root = verify_package(Path(model_root), SDXL_INPAINTING_PACKAGE, cancel=cancel_event)
    x0, y0, x1, y1 = context_box(mask)
    crop, selection = source[y0:y1, x0:x1], mask[y0:y1, x0:x1]
    square, square_mask, original_height, original_width = _square(crop, selection)
    try:
        import torch
        from diffusers import StableDiffusionXLInpaintPipeline
    except ImportError as error:
        raise SDXLRuntimeUnavailable('SDXL çalışma bileşeni bu uygulama paketinde kurulu değil.') from error
    device = 'mps' if torch.backends.mps.is_available() else 'cpu'
    def after_step(_pipeline, _step, _timestep, callback_kwargs):
        check_cancel(cancel_event)
        latents = callback_kwargs.get('latents')
        if latents is not None and not bool(torch.isfinite(latents).all()):
            raise SDXLRuntimeUnavailable('SDXL sayısal olarak geçersiz sonuç üretti.')
        return callback_kwargs
    try:
        check_cancel(cancel_event)
        if device == 'mps':
            # Keep this large shared-memory model below the device's recommended
            # working-set budget instead of disabling PyTorch's safety limit.
            torch.mps.set_per_process_memory_fraction(0.82)
        pipeline = StableDiffusionXLInpaintPipeline.from_pretrained(
            str(root), torch_dtype=torch.float16 if device == 'mps' else torch.float32,
            local_files_only=True, use_safetensors=True, variant='fp16',
        )
        pipeline.enable_vae_tiling()
        # Attention slicing can produce NaN latents on Apple MPS. Validate every
        # step instead of publishing a plausible-looking black image.
        pipeline = pipeline.to(device)
        check_cancel(cancel_event)
        generator = torch.Generator(device='cpu').manual_seed(seed)
        generated = pipeline(
            prompt=prompt, image=Image.fromarray(square), mask_image=Image.fromarray(square_mask),
            height=512, width=512, num_inference_steps=30, guidance_scale=7.5, generator=generator,
            callback_on_step_end=after_step,
            callback_on_step_end_tensor_inputs=['latents'],
        ).images[0]
        check_cancel(cancel_event)
    except InferenceCancelled:
        raise
    except SDXLRuntimeUnavailable:
        raise
    except Exception as error:
        raise SDXLRuntimeUnavailable('SDXL yerel çalıştırması başlatılamadı.') from error
    resized = np.asarray(generated.convert('RGB').resize((square.shape[1], square.shape[0]), Image.Resampling.LANCZOS))
    candidate = source.copy()
    candidate[y0:y1, x0:x1] = resized[:original_height, :original_width]
    return composite_selected(source, candidate, mask), {
        'backend': f'torch-{device}', 'seed': seed, 'context_box': [x0, y0, x1, y1],
        'prompt_mode': 'background_completion',
    }
