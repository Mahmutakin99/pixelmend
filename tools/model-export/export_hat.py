"""Export the official normal Real HAT GAN x4 checkpoint only after parity checks.

This exporter intentionally records that the source repository is Apache-2.0
while the separately hosted checkpoint has no explicit distribution grant. It
may create a local verification candidate; it never marks that candidate ready
for publication or application activation.
"""

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch

from export import DEFAULT_OUT, fetch, sha256

HAT_COMMIT = '1638a9a822581657811867bf670717f8371fc3e5'
WEIGHTS_URL = ('https://drive.usercontent.google.com/download?'
               'id=1Ma12vCWT27P9M99-s2RXnynKN-OQsBrv&export=download&confirm=t')
WEIGHTS_SHA256 = 'f5b1e3bbbb05147ca2beefcc715279cb647d7976cbda67d62ea7e6e20d5ffcc7'
WEIGHTS_SIZE_BYTES = 170277017
ARCHITECTURE_URL = f'https://raw.githubusercontent.com/XPixelGroup/HAT/{HAT_COMMIT}/hat/archs/hat_arch.py'
ARCHITECTURE_SHA256 = '81d8cecf491975246c9ebb20480898c656f59de020f38b05daa68741e426117f'
LICENSE_URL = f'https://raw.githubusercontent.com/XPixelGroup/HAT/{HAT_COMMIT}/LICENSE'
LICENSE_SHA256 = 'a91d57ebad8955a1757be7891ca2da8e07493e662f0e34e1e1926571e05f37fc'

HAT_KWARGS = {
    'upscale': 4, 'in_chans': 3, 'img_size': 64, 'window_size': 16,
    'compress_ratio': 3, 'squeeze_factor': 30, 'conv_scale': 0.01,
    'overlap_ratio': 0.5, 'img_range': 1., 'depths': [6] * 6,
    'embed_dim': 180, 'num_heads': [6] * 6, 'mlp_ratio': 2,
    'upsampler': 'pixelshuffle', 'resi_connection': '1conv',
}


def load_official_architecture(source_path: Path):
    """Load a minimally adapted, hash-pinned copy of the Apache HAT architecture.

    The official class only imports a registry and two tiny BasicSR helpers.
    Replacing those imports keeps the conversion environment small while using
    the exact network implementation and state-dict contract from the pinned
    upstream source.
    """
    source = source_path.read_text()
    helpers = '''from torch.nn.init import trunc_normal_\n\ndef to_2tuple(value):\n    return value if isinstance(value, tuple) else (value, value)\n\nclass _ArchitectureRegistry:\n    def register(self):\n        return lambda cls: cls\n\nARCH_REGISTRY = _ArchitectureRegistry()\n\ndef rearrange(tensor, pattern, *, nc, ch, owh, oww):\n    batch, _, windows = tensor.shape\n    return tensor.reshape(batch, nc, ch, owh, oww, windows).permute(1, 0, 5, 3, 4, 2).reshape(nc, batch * windows, owh * oww, ch)\n'''
    expected_imports = ('from basicsr.utils.registry import ARCH_REGISTRY\n'
                        'from basicsr.archs.arch_util import to_2tuple, trunc_normal_\n\n'
                        'from einops import rearrange\n')
    if expected_imports not in source:
        raise ValueError('Pinned HAT architecture import contract changed.')
    adapted = source.replace(expected_imports, helpers)
    generated = source_path.with_name('hat_arch_pixelmend.py')
    generated.write_text(adapted)
    spec = importlib.util.spec_from_file_location('pixelmend_hat_arch', generated)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.HAT


def parity(model, artifact: Path):
    session = ort.InferenceSession(str(artifact), providers=['CPUExecutionProvider'])
    rng = np.random.default_rng(20260923)
    rows = []
    with torch.inference_mode():
        for height, width in ((64, 64), (80, 64), (64, 80)):
            data = rng.random((1, 3, height, width), dtype=np.float32)
            expected = model(torch.from_numpy(data)).numpy()
            actual = session.run(['output'], {'input': data})[0]
            difference = np.abs(actual - expected)
            if actual.shape != (1, 3, height * 4, width * 4) or not np.isfinite(actual).all():
                raise ValueError('Invalid HAT ONNX output.')
            np.testing.assert_allclose(actual, expected, rtol=3e-3, atol=3e-4)
            rows.append({'input_shape': list(data.shape), 'max_abs_error': float(difference.max()),
                         'mean_abs_error': float(difference.mean()), 'passed': True})
    return rows


def main():
    DEFAULT_OUT.mkdir(parents=True, exist_ok=True)
    weights = DEFAULT_OUT / 'Real_HAT_GAN_SRx4.pth'
    source = DEFAULT_OUT / 'hat_arch.py'
    license_path = DEFAULT_OUT / 'LICENSE.HAT.txt'
    fetch(WEIGHTS_URL, weights, WEIGHTS_SHA256)
    fetch(ARCHITECTURE_URL, source, ARCHITECTURE_SHA256)
    fetch(LICENSE_URL, license_path, LICENSE_SHA256)
    if weights.stat().st_size != WEIGHTS_SIZE_BYTES:
        raise ValueError('Pinned HAT checkpoint size mismatch.')

    model = load_official_architecture(source)(**HAT_KWARGS).eval()
    checkpoint = torch.load(weights, map_location='cpu', weights_only=True)
    model.load_state_dict(checkpoint['params_ema'], strict=True)
    artifact = DEFAULT_OUT / 'real-hat-gan-x4-fp32.onnx'
    staging = artifact.with_suffix('.staging.onnx')
    staging.unlink(missing_ok=True)
    torch.set_num_threads(4)
    with torch.inference_mode():
        torch.onnx.export(
            model, torch.zeros(1, 3, 64, 64), str(staging),
            input_names=['input'], output_names=['output'],
            dynamic_axes={'input': {2: 'height', 3: 'width'},
                          'output': {2: 'height_x4', 3: 'width_x4'}},
            opset_version=17, dynamo=False,
        )
    onnx.checker.check_model(str(staging), full_check=True)
    checks = parity(model, staging)
    staging.replace(artifact)
    provenance = {
        'created_at': datetime.now(timezone.utc).isoformat(), 'model_id': 'real-hat-gan-x4',
        'variant': 'normal', 'source_repository': 'XPixelGroup/HAT', 'source_commit': HAT_COMMIT,
        'weights_url': WEIGHTS_URL, 'weights_sha256': sha256(weights),
        'weights_size_bytes': weights.stat().st_size, 'architecture_url': ARCHITECTURE_URL,
        'architecture_sha256': sha256(source), 'license_id': 'Apache-2.0',
        'license_url': LICENSE_URL, 'license_sha256': sha256(license_path),
        'checkpoint_distribution_terms': 'No separate checkpoint distribution grant was found at the official download.',
        'activation_permitted': False, 'published': False,
        'contract': 'FP32 NCHW RGB 0..1; H/W multiples of 16; natural scale 4; clip output to 0..1',
        'parity': checks,
        'artifact': {'filename': artifact.name, 'sha256': sha256(artifact),
                     'size_bytes': artifact.stat().st_size},
    }
    (DEFAULT_OUT / 'hat-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(provenance, indent=2))


if __name__ == '__main__':
    main()
