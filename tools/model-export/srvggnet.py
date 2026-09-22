"""SRVGGNetCompact (Real-ESRGAN, BSD-3-Clause).

Adapted from xinntao/Real-ESRGAN realesrgan/archs/srvgg_arch.py.
The optional registry and unused activation variants are omitted. Layer names
and the official General x4v3 configuration are preserved for strict loading.
"""
from torch import nn
from torch.nn import functional as F


class SRVGGNetCompact(nn.Module):
    def __init__(self):
        super().__init__()
        self.body = nn.ModuleList([nn.Conv2d(3, 64, 3, 1, 1), nn.PReLU(64)])
        for _ in range(32):
            self.body.extend([nn.Conv2d(64, 64, 3, 1, 1), nn.PReLU(64)])
        self.body.append(nn.Conv2d(64, 48, 3, 1, 1))
        self.upsampler = nn.PixelShuffle(4)

    def forward(self, image):
        output = image
        for layer in self.body:
            output = layer(output)
        return self.upsampler(output) + F.interpolate(image, scale_factor=4, mode='nearest')
