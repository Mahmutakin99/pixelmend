"""Export only the pinned official General x4v3 weights, gated on raw FP32 parity."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import onnx
import torch

from export import DEFAULT_OUT, LICENSE_URL, fetch, parity, sha256
from srvggnet import SRVGGNetCompact

URL = 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth'
SHA = '8dc7edb9ac80ccdc30c3a5dca6616509367f05fbc184ad95b731f05bece96292'


def main():
    DEFAULT_OUT.mkdir(parents=True, exist_ok=True)
    weights = DEFAULT_OUT / 'realesr-general-x4v3.pth'
    fetch(URL, weights, SHA)
    license_file = DEFAULT_OUT / 'LICENSE.Real-ESRGAN.txt'
    fetch(LICENSE_URL, license_file)
    model = SRVGGNetCompact().eval()
    model.load_state_dict(torch.load(weights, map_location='cpu', weights_only=True)['params'], strict=True)
    torch.set_num_threads(4)
    output = DEFAULT_OUT / 'realesrgan-general-x4v3-fp32.onnx'
    temporary = output.with_suffix('.staging.onnx')
    with torch.inference_mode():
        torch.onnx.export(model, torch.zeros(1, 3, 16, 16), str(temporary),
                          input_names=['input'], output_names=['output'],
                          dynamic_axes={'input': {2: 'height', 3: 'width'}, 'output': {2: 'height_x4', 3: 'width_x4'}},
                          opset_version=17, dynamo=False)
    onnx.checker.check_model(str(temporary), full_check=True)
    checks = parity(model, temporary)
    temporary.replace(output)
    evidence = {'created_at': datetime.now(timezone.utc).isoformat(), 'model_id': 'realesrgan-general-x4v3',
                'weights_url': URL, 'weights_sha256': SHA, 'license_url': LICENSE_URL,
                'license_sha256': sha256(license_file), 'license_id': 'BSD-3-Clause',
                'architecture_sha256': sha256(Path(__file__).with_name('srvggnet.py')),
                'export_sha256': sha256(Path(__file__)), 'uv_lock_sha256': sha256(Path(__file__).with_name('uv.lock')),
                'artifact': {'filename': output.name, 'sha256': sha256(output), 'size_bytes': output.stat().st_size},
                'contract': 'FP32 NCHW RGB 0..1; dynamic H/W; natural scale 4; clip output to 0..1',
                'parity': checks, 'published': False}
    (DEFAULT_OUT / 'general-provenance.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
