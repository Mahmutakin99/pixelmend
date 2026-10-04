"""Restore the locally reviewed CC0/public-domain fixtures from pinned hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'fixtures')
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    catalog = Path(__file__).resolve().parent / 'photograph-manifest.json'
    rows = json.loads(catalog.read_text())
    for row in rows:
        name = row['id'] + ('.jpg' if row['id'] in {'skin', 'rocket', 'hubble_deep_field'} else '.png')
        original = root / ('original-' + name)
        if not original.exists():
            with urllib.request.urlopen(row['source_url'], timeout=60) as response:
                raw = response.read(32 * 1024 * 1024 + 1)
            if hashlib.sha256(raw).hexdigest() != row['original_sha256']:
                raise ValueError('Source photograph hash mismatch: ' + row['id'])
            original.write_bytes(raw)
        if hashlib.sha256(original.read_bytes()).hexdigest() != row['original_sha256']:
            raise ValueError('Cached photograph hash mismatch: ' + row['id'])
        image = Image.open(original).convert('RGB')
        image.thumbnail((192, 192), Image.Resampling.LANCZOS)
        output = root / (row['id'] + '.png')
        image.save(output)
        if hashlib.sha256(output.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Prepared fixture differs; use the recorded Pillow environment.')
        row['path'] = str(output)
    (root / 'manifest.json').write_text(json.dumps(rows, indent=2) + '\n')
    print('Verified 12 photographs.')


if __name__ == '__main__':
    main()
