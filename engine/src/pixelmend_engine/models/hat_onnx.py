"""Window-safe ONNX adapter for the normal Real HAT GAN x4 model."""

import numpy as np

from .realesrgan_onnx import RealESRGANUpscale


class HATGANUpscale(RealESRGANUpscale):
    """Run HAT in bounded tiles while preserving edge pixels around its 16px windows."""

    window_size = 16
    maximum_tile_size = 256

    def __init__(self, model_path, *, tile_size=192, overlap=32, **kwargs):
        if (type(tile_size) is not int or type(overlap) is not int
                or tile_size < self.window_size or tile_size > self.maximum_tile_size
                or not 0 < overlap < tile_size):
            raise ValueError('HAT requires a bounded tile with a positive overlap')
        super().__init__(model_path, tile_size=tile_size, overlap=overlap, **kwargs)

    def tensor(self, data):
        """Pad only the inference context; crop it before tile compositing.

        HAT attention windows require height and width divisible by 16.  The
        enclosing tile implementation may create short edge contexts, so this
        method expands those contexts deterministically rather than rejecting
        ordinary image dimensions.  The caller receives exactly the original
        tensor extent at 4x and never observes the synthetic edge pixels.
        """
        height, width = data.shape[2:]
        padded_height = ((height + self.window_size - 1) // self.window_size) * self.window_size
        padded_width = ((width + self.window_size - 1) // self.window_size) * self.window_size
        if (padded_height, padded_width) == (height, width):
            return super().tensor(data)
        # Reflect avoids inventing a hard border. A 1px context cannot reflect,
        # and edge repetition remains deterministic for that degenerate case.
        mode = 'reflect' if height > 1 and width > 1 else 'edge'
        padded = np.pad(data, ((0, 0), (0, 0), (0, padded_height - height),
                               (0, padded_width - width)), mode=mode)
        output = super().tensor(np.ascontiguousarray(padded))
        return output[:, :, :height * 4, :width * 4]
