"""Window-safe ONNX adapter for the Apache-2.0 Swin2SR Real-World x4 model."""

import numpy as np

from .realesrgan_onnx import RealESRGANUpscale


class Swin2SRUpscale(RealESRGANUpscale):
    """Run Swin2SR in deterministic 8px-window-compatible tiles.

    The published model uses 8-pixel attention windows. Editor images need not
    share that alignment, so edge contexts are padded solely for inference and
    cropped before the normal overlapping-tile compositor sees them.
    """

    window_size = 8
    maximum_tile_size = 256

    def __init__(self, model_path, *, tile_size=192, overlap=16, **kwargs):
        if (type(tile_size) is not int or type(overlap) is not int
                or tile_size < self.window_size or tile_size > self.maximum_tile_size
                or not 0 < overlap < tile_size):
            raise ValueError('Swin2SR requires a bounded tile with a positive overlap')
        super().__init__(model_path, tile_size=tile_size, overlap=overlap, **kwargs)

    def tensor(self, data):
        height, width = data.shape[2:]
        padded_height = ((height + self.window_size - 1) // self.window_size) * self.window_size
        padded_width = ((width + self.window_size - 1) // self.window_size) * self.window_size
        if (padded_height, padded_width) == (height, width):
            return super().tensor(data)
        mode = 'reflect' if height > 1 and width > 1 else 'edge'
        padded = np.pad(data, ((0, 0), (0, 0), (0, padded_height - height),
                               (0, padded_width - width)), mode=mode)
        output = super().tensor(np.ascontiguousarray(padded))
        return output[:, :, :height * 4, :width * 4]
