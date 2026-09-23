"""Export and parity-gate the Apache-2.0 Swin2SR Real-World x4 checkpoint.

The source weights are retrieved only from the pinned CAIDAS Hugging Face
revision.  This script produces a local verification candidate; publishing a
derived ONNX artifact is a separate, explicit release decision.
"""

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform

import numpy as np
import onnx
import onnxruntime as ort
import torch
from huggingface_hub import hf_hub_download
from transformers import Swin2SRForImageSuperResolution

from export import DEFAULT_OUT, sha256

MODEL_ID = 'caidas/swin2SR-realworld-sr-x4-64-bsrgan-psnr'
REVISION = 'bb13f02e45e88d00b6c202b3fbe6a181af144606'
WEIGHTS_FILENAME = 'pytorch_model.bin'
WEIGHTS_SHA256 = '4a5f52a20932085557ed115f87c0ee8385e12f2719108c0dfd38c64aedea4710'
WEIGHTS_SIZE_BYTES = 48_460_141
LICENSE_ID = 'Apache-2.0'
LICENSE_URL = 'https://huggingface.co/caidas/swin2SR-realworld-sr-x4-64-bsrgan-psnr/blob/main/LICENSE'


class Reconstruction(torch.nn.Module):
    """Keep the deployed graph to a single NCHW RGB tensor contract."""

    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, image):
        return self.model(pixel_values=image).reconstruction


def fetch(repo, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename in ('config.json', WEIGHTS_FILENAME):
        local = output_dir / filename
        # A verified local source supports offline, reproducible re-export.
        # Only a missing file needs the pinned remote acquisition path.
        if not local.exists():
            remote = hf_hub_download(repo_id=MODEL_ID, filename=filename, revision=REVISION)
            local.write_bytes(Path(remote).read_bytes())
    weights = output_dir / WEIGHTS_FILENAME
    if weights.stat().st_size != WEIGHTS_SIZE_BYTES or sha256(weights) != WEIGHTS_SHA256:
        raise ValueError('Pinned Swin2SR checkpoint verification failed.')
    return weights


def parity(model, artifact):
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    session = ort.InferenceSession(str(artifact), sess_options=options,
                                   providers=['CPUExecutionProvider'])
    rng = np.random.default_rng(20260923)
    rows = []
    with torch.inference_mode():
        for height, width in ((64, 64), (72, 64), (64, 72)):
            image = rng.random((1, 3, height, width), dtype=np.float32)
            expected = model(torch.from_numpy(image)).numpy()
            actual = session.run(['output'], {'input': image})[0]
            difference = np.abs(actual - expected)
            if actual.shape != (1, 3, height * 4, width * 4) or not np.isfinite(actual).all():
                raise ValueError('Invalid Swin2SR ONNX output.')
            np.testing.assert_allclose(actual, expected, rtol=3e-3, atol=3e-4)
            rows.append({'input_shape': list(image.shape), 'max_abs_error': float(difference.max()),
                         'mean_abs_error': float(difference.mean()), 'passed': True})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUT / 'swin2sr')
    args = parser.parse_args()
    weights = fetch(MODEL_ID, args.output_dir)
    torch.set_num_threads(4)
    model = Reconstruction(Swin2SRForImageSuperResolution.from_pretrained(
        args.output_dir, local_files_only=True).eval()).eval()
    artifact = args.output_dir / 'swin2sr-realworld-x4-fp32.onnx'
    staging = artifact.with_suffix('.staging.onnx')
    staging.unlink(missing_ok=True)
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
        'created_at': datetime.now(timezone.utc).isoformat(), 'model_id': 'swin2sr-realworld-x4',
        'source_repository': MODEL_ID, 'source_revision': REVISION,
        'weights_filename': WEIGHTS_FILENAME, 'weights_sha256': sha256(weights),
        'weights_size_bytes': weights.stat().st_size, 'license_id': LICENSE_ID,
        'license_url': LICENSE_URL, 'platform': platform.platform(),
        'python': platform.python_version(),
        'packages': {name: importlib.metadata.version(name)
                     for name in ('torch', 'onnx', 'onnxruntime', 'transformers')},
        'contract': 'FP32 NCHW RGB 0..1; H/W multiples of 8; natural scale 4; clip output to 0..1',
        'parity': checks,
        'artifact': {'filename': artifact.name, 'sha256': sha256(artifact),
                     'size_bytes': artifact.stat().st_size},
        'published': False,
    }
    (args.output_dir / 'swin2sr-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(provenance, indent=2))


if __name__ == '__main__':
    main()
