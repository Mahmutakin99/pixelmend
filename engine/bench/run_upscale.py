"""Run reproducible local upscale measurements; fixture pixels never enter git."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import statistics
import time

import numpy as np
import onnxruntime as ort
import psutil
from PIL import Image

from pixelmend_engine.models.realesrgan_onnx import RealESRGANUpscale


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def load_fixture(path):
    with Image.open(path) as image:
        return np.asarray(image.convert('RGB')).copy()


def measure(adapter, pixels, target):
    process = psutil.Process()
    before = process.memory_info().rss
    started = time.monotonic()
    result = adapter.run(pixels, target_size=target)
    seconds = time.monotonic() - started
    return result, seconds, max(before, process.memory_info().rss)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--fixtures', type=Path, required=True,
                        help='JSON list: {id,path,source_url,license,sha256}; paths are local and ignored')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--provider', default='CPUExecutionProvider')
    parser.add_argument('--tile-size', type=int, default=128)
    parser.add_argument('--overlap', type=int, default=16)
    args = parser.parse_args()
    fixtures = json.loads(args.fixtures.read_text())
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError('fixtures must contain approved CC0 or public-domain entries')
    adapter = RealESRGANUpscale(args.model, providers=[args.provider], tile_size=args.tile_size,
                                overlap=args.overlap)
    rows = []
    for fixture in fixtures:
        required = {'id', 'path', 'source_url', 'license', 'downloaded_at', 'sha256',
                    'input_width', 'input_height', 'expected_use'}
        if not required <= fixture.keys() or fixture['license'] not in {'CC0-1.0', 'Public-Domain'}:
            raise ValueError('fixture provenance is incomplete or not approved')
        path = Path(fixture['path'])
        if digest(path) != fixture['sha256']:
            raise ValueError(f"fixture hash mismatch: {fixture['id']}")
        pixels = load_fixture(path)
        if (pixels.shape[1], pixels.shape[0]) != (fixture['input_width'], fixture['input_height']):
            raise ValueError(f"fixture dimensions mismatch: {fixture['id']}")
        targets = {'2x': (pixels.shape[1] * 2, pixels.shape[0] * 2),
                   '4x': (pixels.shape[1] * 4, pixels.shape[0] * 4)}
        for name, target in targets.items():
            cold = measure(adapter, pixels, target)
            samples = [measure(adapter, pixels, target) for _ in range(args.runs)]
            result, _, peak = samples[-1]
            rows.append({'fixture': fixture['id'], 'source_url': fixture['source_url'],
                         'license': fixture['license'], 'fixture_sha256': fixture['sha256'],
                         'target': name, 'width': target[0], 'height': target[1],
                         'raw_rgb_sha256': hashlib.sha256(result.tobytes()).hexdigest(),
                         'cold_seconds': round(cold[1], 6),
                         'warm_seconds': [round(sample[1], 6) for sample in samples],
                         'warm_median_seconds': statistics.median(sample[1] for sample in samples),
                         'host_peak_rss_bytes': max(cold[2], peak), 'device_peak_bytes': None,
                         'tile_seam_check': 'manual_review_required',
                         'lanczos_comparison': 'manual_review_required'})
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(),
              'onnxruntime': ort.__version__, 'provider': args.provider,
              'model': {'provider_identity': args.provider, 'path': args.model.name, 'sha256': digest(args.model)},
              'tile': {'size': args.tile_size, 'overlap': args.overlap}, 'results': rows}
    args.out.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
