"""Copy original dependency notices into the standalone runtime's resources."""
from importlib.metadata import distributions
import json
from pathlib import Path
import shutil
import sys

def main():
    runtime = Path(sys.argv[1]).resolve()
    if not (runtime / 'pixelmend-generative-runtime').is_file():
        raise SystemExit('Standalone runtime is missing')
    target = runtime / '_internal' / 'pixelmend-licenses'
    target.mkdir(parents=True, exist_ok=True)
    rows = []
    for distribution in sorted(distributions(), key=lambda d:d.metadata['Name'].lower()):
        name = distribution.metadata['Name']
        row = {'name': name, 'version': distribution.version,
               'license': distribution.metadata.get('License-Expression') or distribution.metadata.get('License'),
               'notices': []}
        for entry in distribution.files or []:
            file = distribution.locate_file(entry)
            if not file.is_file() or not any(marker in file.name.lower() for marker in ('license','copying','notice')):
                continue
            if file.suffix.lower() not in ('', '.txt', '.md', '.rst') or file.stat().st_size>1024**2:
                continue
            destination = target / name / Path(str(entry)).name
            destination.parent.mkdir(exist_ok=True)
            # Retain each original notice even if a package reuses the filename.
            if destination.exists() and destination.read_bytes()!=file.read_bytes():
                import hashlib
                destination = destination.with_name(hashlib.sha256(str(entry).encode()).hexdigest()[:12]+'-'+file.name)
            shutil.copyfile(file, destination)
            row['notices'].append(str(destination.relative_to(target)))
        rows.append(row)
    (target / 'dependencies.json').write_text(json.dumps(rows,indent=2)+'\n')

if __name__=='__main__':
    main()
