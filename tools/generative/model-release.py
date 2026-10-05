"""Prepare and validate immutable model-release transport assets.

Preparation never publishes. All local parts are verified before hard links are
created. The caller verifies GitHub's uploaded asset sizes and SHA256 digests
before committing a catalog with these URLs or publishing the draft release.
"""
from copy import deepcopy
import hashlib
import os
from pathlib import Path,PurePosixPath
import re
import shutil

GIB=1024**3
REPOSITORY='Mahmutakin99/pixelmend-models'

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        while chunk:=stream.read(4*1024**2):h.update(chunk)
    return h.hexdigest()

def prepare(source,catalog,destination,tag):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',tag):raise ValueError('invalid release tag')
    source=Path(source);destination=Path(destination)
    if destination.exists():raise FileExistsError(destination)
    candidate=deepcopy(catalog);assets={};paths={}
    for package in candidate['packages']:
        if not re.fullmatch(r'[a-z0-9-]+',package['id']):raise ValueError('invalid package id')
        for part in package['parts']:
            relative=PurePosixPath(part['local_path'])
            if relative.is_absolute() or '..' in relative.parts or '\\' in part['local_path']:
                raise ValueError('unsafe local part path')
            path=source/package['id']/str(relative)
            if any(p.is_symlink() for p in [path,*path.parents]) or not path.is_file():raise ValueError('unsafe local part')
            if not 0<=part['size_bytes']<=GIB or path.stat().st_size!=part['size_bytes'] or digest(path)!=part['sha256']:
                raise ValueError('local part hash mismatch')
            sha=part['sha256'];assets[sha]={'name':sha,'size':part['size_bytes'],'digest':'sha256:'+sha};paths[sha]=path
            part['url']=f'https://github.com/{REPOSITORY}/releases/download/{tag}/{sha}'
    destination.mkdir(parents=True)
    for sha,path in paths.items():
        try:os.link(path,destination/sha)
        except OSError:shutil.copyfile(path,destination/sha)
    return {'repository':REPOSITORY,'tag':tag,'catalog':candidate,'assets':list(assets.values()),
            'download_bytes':sum(row['size'] for row in assets.values())}

def verify_remote(report,assets):
    actual={row['name']:row for row in assets}
    for expected in report['assets']:
        row=actual.get(expected['name'])
        if row is None or row['size']!=expected['size'] or row.get('digest')!=expected['digest']:
            raise ValueError('remote asset hash or size mismatch')

if __name__=='__main__':
    import argparse,json
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('catalog');p.add_argument('destination');p.add_argument('tag')
    args=p.parse_args();report=prepare(args.source,json.loads(Path(args.catalog).read_text()),args.destination,args.tag)
    Path(args.destination).joinpath('release-verification.json').write_text(json.dumps(report,indent=2)+'\n')
