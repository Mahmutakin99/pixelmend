"""Create reproducible MI-GAN/LaMa/OpenCV object-removal review sheets."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import time

import numpy as np
import psutil
from PIL import Image, ImageDraw

from pixelmend_engine.models.lama_onnx import LamaInpaint
from pixelmend_engine.models.migan_onnx import MIGANInpaint
from pixelmend_engine.models.opencv_inpaint import OpenCVInpaint


CASES = (
    ('astronaut', 'flat', (.62, .10, .69, .18), 0),
    ('coffee', 'texture', (.10, .15, .20, .28), 0),
    ('brick', 'structure', (.42, .42, .58, .58), 0),
    ('chelsea', 'edge', (0, .40, .08, .55), 0),
    ('rocket', 'wide', (.38, .28, .62, .60), 1600),
    ('rocket', 'wide', (.38, .28, .62, .60), 2400),
)


def measure(adapter, pixels, mask):
    process = psutil.Process()
    before = process.memory_info().rss
    started = time.monotonic()
    output = adapter.run(pixels, mask)
    return output, time.monotonic() - started, max(before, process.memory_info().rss)


def load_image(root, name, width):
    filename = f'original-{name}.jpg' if name == 'rocket' else f'original-{name}.png'
    image = Image.open(root / filename).convert('RGB')
    if width:
        image = image.resize((width, width * 9 // 16), Image.Resampling.LANCZOS)
    else:
        image.thumbnail((512, 512))
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--migan', type=Path, required=True)
    parser.add_argument('--lama', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).parent / 'fixtures'
    args.out.mkdir(parents=True, exist_ok=True)
    migan = MIGANInpaint(args.migan, providers=['CPUExecutionProvider'])
    lama = LamaInpaint(model_path=args.lama, providers=['CPUExecutionProvider'])
    opencv = OpenCVInpaint('telea')
    rows = []
    for name, category, box, width in CASES:
        source = load_image(root, name, width)
        pixels = np.asarray(source).copy()
        image_width, image_height = source.size
        x0, y0, x1, y1 = [round(v * n) for v, n in zip(box, (image_width, image_height, image_width, image_height))]
        mask = np.zeros((image_height, image_width), np.uint8)
        mask[y0:y1, x0:x1] = 255
        outputs = {}
        for label, adapter in (('migan', migan), ('lama', lama), ('opencv', opencv)):
            result, elapsed, rss = measure(adapter, pixels, mask)
            if not np.array_equal(result[mask == 0], pixels[mask == 0]):
                raise ValueError(f'{label} altered pixels outside the selection: {name}')
            outputs[label] = result
            Image.fromarray(result).save(args.out / f'{name}-{width or "review"}-{label}.png')
            rows.append({'photo': name, 'category': category, 'width': image_width, 'height': image_height,
                         'algorithm': label, 'seconds': round(elapsed, 6), 'host_rss_bytes': rss,
                         'unmasked_exact': True, 'mask_box': [x0, y0, x1, y1],
                         'visual_review': 'pending'})
        marked = source.copy()
        ImageDraw.Draw(marked).rectangle((x0, y0, x1, y1), outline='red', width=max(2, image_width // 256))
        sheet = Image.new('RGB', (image_width * 4, image_height + 28), 'white')
        for index, (label, image) in enumerate((('Source / mask', marked), ('MI-GAN', Image.fromarray(outputs['migan'])),
                                                  ('LaMa', Image.fromarray(outputs['lama'])), ('OpenCV', Image.fromarray(outputs['opencv'])))):
            sheet.paste(image, (index * image_width, 28))
            ImageDraw.Draw(sheet).text((index * image_width + 5, 7), label, fill='black')
        sheet.save(args.out / f'{name}-{width or "review"}-comparison.png')
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(),
              'migan_sha256': hashlib.file_digest(args.migan.open('rb'), 'sha256').hexdigest(),
              'lama_sha256': hashlib.file_digest(args.lama.open('rb'), 'sha256').hexdigest(), 'results': rows}
    (args.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
