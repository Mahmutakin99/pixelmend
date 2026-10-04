#!/usr/bin/env python3
"""Select the official macOS 15 MLX wheels already pinned in uv.lock."""
import hashlib
import pathlib
import subprocess
import sys
import tomllib
import urllib.parse
import urllib.request

root=pathlib.Path(__file__).resolve().parents[2]
lock=tomllib.loads((root/'engine/generative-runtime/uv.lock').read_text())
cache=root/'.local-notes/generative/build-wheels';cache.mkdir(parents=True,exist_ok=True)
files=[]
for name in ('mlx','mlx-metal'):
    package=next(p for p in lock['package'] if p['name']==name)
    if package['version']!='0.32.2':raise ValueError('Unexpected MLX version; review the runtime lock before packaging')
    matches=[w for w in package['wheels'] if w['url'].endswith(('cp312-cp312-macosx_15_0_arm64.whl','py3-none-macosx_15_0_arm64.whl'))]
    if len(matches)!=1:raise ValueError('Expected exactly one pinned macOS 15 wheel')
    wheel=matches[0];url=urllib.parse.urlparse(wheel['url'])
    if url.scheme!='https' or url.hostname!='files.pythonhosted.org':raise ValueError('Unexpected official wheel host')
    file=cache/pathlib.PurePosixPath(url.path).name
    expected=wheel['hash'].removeprefix('sha256:')
    valid=file.exists() and file.stat().st_size==wheel['size'] and hashlib.file_digest(file.open('rb'),'sha256').hexdigest()==expected
    if not valid:
        temporary=file.with_suffix('.partial')
        try:
            with urllib.request.urlopen(wheel['url'],timeout=60) as source,temporary.open('wb') as output:
                total=0
                while chunk:=source.read(1024*1024):
                    total+=len(chunk)
                    if total>wheel['size']:raise ValueError('Wheel exceeds locked size')
                    output.write(chunk)
            with temporary.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            if total!=wheel['size'] or digest!=expected:raise ValueError('Wheel hash/size mismatch')
            temporary.replace(file)
        finally:temporary.unlink(missing_ok=True)
    files.append(str(file))
subprocess.run(['uv','pip','install','--python',str(root/'engine/generative-runtime/.venv/bin/python'),
                '--reinstall','--no-deps',*files],check=True)
print('Installed verified macOS 15 MLX 0.32.2 wheels; rebuild and audit the complete runtime before distribution.')
