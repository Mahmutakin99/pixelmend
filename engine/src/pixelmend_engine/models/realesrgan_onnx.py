"""RealESRGAN RGB inference with cancellable, disk-backed overlapping tiles."""

from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event

import numpy as np
import onnxruntime as ort
from PIL import Image

from ..policy import POLICY, ResourceLimitError, validate_dimensions


class InferenceCancelled(Exception):
    """Native calls finish, but no further tiles or results are published."""


def check_cancel(cancel_event):
    if cancel_event is not None and cancel_event.is_set():
        raise InferenceCancelled()


def tile_starts(length, size, overlap):
    """Anchor the last tile to the edge without gaps or tiny trailing tiles."""
    if length <= size:
        return [0]
    starts = list(range(0, length - size + 1, size - overlap))
    if starts[-1] != length - size:
        starts.append(length - size)
    return starts


def axis_weight(length, start, total, overlap):
    """Positive feather weights make every covered output pixel normalizable."""
    weight = np.ones(length, dtype=np.float32)
    fade = min(overlap, length)
    if start > 0:
        weight[:fade] *= np.linspace(1 / (fade + 1), 1, fade, dtype=np.float32)
    if start + length < total:
        weight[-fade:] *= np.linspace(1, 1 / (fade + 1), fade, dtype=np.float32)
    return weight


class RealESRGANUpscale:
    def __init__(self, model_path, *, providers=None, tile_size=128, overlap=16,
                 temp_dir=None, session=None):
        """The caller must verify the immutable artifact before constructing this adapter."""
        if type(tile_size) is not int or type(overlap) is not int or not 0 < overlap < tile_size:
            raise ValueError('tile size must exceed a positive overlap')
        self.tile_size, self.overlap, self.temp_dir = tile_size, overlap, temp_dir
        ort.disable_telemetry_events()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        self.session = session if session is not None else ort.InferenceSession(
            str(model_path), sess_options=options, providers=providers or ['CPUExecutionProvider'])
        inputs, outputs = self.session.get_inputs(), self.session.get_outputs()
        if (len(inputs) != 1 or len(outputs) != 1 or inputs[0].type != 'tensor(float)'
                or outputs[0].type != 'tensor(float)' or len(inputs[0].shape) != 4
                or inputs[0].shape[1] != 3 or len(outputs[0].shape) != 4
                or outputs[0].shape[1] != 3
                or any(isinstance(x, int) for x in inputs[0].shape[2:])):
            raise ValueError('expected dynamic FP32 NCHW RGB 4x ONNX contract')
        self.input_name = inputs[0].name

    def tensor(self, data):
        """Validate outputs before a malformed graph can corrupt the tile buffer."""
        output = self.session.run(None, {self.input_name: data})[0]
        expected = (1, 3, data.shape[2] * 4, data.shape[3] * 4)
        if output.shape != expected or not np.isfinite(output).all():
            raise ValueError('invalid RealESRGAN output')
        return output

    def run(self, image, mask=None, *, target_size=None, cancel_event=None, progress=None, **params):
        """Enhance RGB, then Lanczos-resample to the exact requested dimensions."""
        if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3 or min(image.shape[:2]) < 1:
            raise ValueError('nonempty RGB uint8 required')
        if mask is not None:
            raise ValueError('upscale does not accept a mask')
        height, width = image.shape[:2]
        natural = (width * 4, height * 4)
        validate_dimensions(*natural)
        target_size = target_size or natural
        validate_dimensions(*target_size)
        check_cancel(cancel_event)
        xs, ys = tile_starts(width, self.tile_size, self.overlap), tile_starts(height, self.tile_size, self.overlap)
        total = len(xs) * len(ys)
        # A private context removes all mapped intermediates on success, error or cancellation.
        with TemporaryDirectory(prefix='pixelmend-tiles-', dir=self.temp_dir) as directory:
            import shutil
            if shutil.disk_usage(directory).free < natural[0] * natural[1] * 16 + 256 * 1024**2:
                raise ResourceLimitError('disk_full', 'AI karo birleştirmesi için geçici disk alanı yetersiz.')
            accum = np.memmap(Path(directory) / 'rgb.f32', dtype=np.float32, mode='w+', shape=(height * 4, width * 4, 3))
            weights = np.memmap(Path(directory) / 'weight.f32', dtype=np.float32, mode='w+', shape=(height * 4, width * 4))
            try:
                completed = 0
                for y in ys:
                    for x in xs:
                        check_cancel(cancel_event)
                        right, bottom = min(width, x + self.tile_size), min(height, y + self.tile_size)
                        # Context halo is cropped, while overlapping cores feather their estimates.
                        x0, y0 = max(0, x - self.overlap), max(0, y - self.overlap)
                        x1, y1 = min(width, right + self.overlap), min(height, bottom + self.overlap)
                        data = np.ascontiguousarray(image[y0:y1, x0:x1].transpose(2, 0, 1)[None], dtype=np.float32) / 255
                        output = self.tensor(data)[0].transpose(1, 2, 0)
                        check_cancel(cancel_event)
                        patch = output[(y-y0)*4:(bottom-y0)*4, (x-x0)*4:(right-x0)*4]
                        feather = axis_weight((bottom-y)*4, y*4, height*4, self.overlap*4)[:, None] * axis_weight((right-x)*4, x*4, width*4, self.overlap*4)[None, :]
                        accum[y*4:bottom*4, x*4:right*4] += patch * feather[:, :, None]
                        weights[y*4:bottom*4, x*4:right*4] += feather
                        completed += 1
                        if progress:
                            progress(completed, total)
                result = np.empty((height * 4, width * 4, 3), dtype=np.uint8)
                for row in range(0, height * 4, 64):
                    check_cancel(cancel_event)
                    strip = accum[row:row+64] / weights[row:row+64, :, None]
                    result[row:row+64] = np.rint(np.clip(strip, 0, 1) * 255).astype(np.uint8)
            finally:
                accum._mmap.close()
                weights._mmap.close()
        check_cancel(cancel_event)
        if target_size != natural:
            result = np.asarray(Image.fromarray(result).resize(target_size, Image.Resampling.LANCZOS)).copy()
        check_cancel(cancel_event)
        return result
