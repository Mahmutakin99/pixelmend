"""ZIP64 continuation archives; restore aliases from a SHA256 manifest.

Only explicitly selected files enter the archive. No credentials or machine
configuration are collected. Python standard library only on the receiving Mac.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile
import zlib

CHUNK=4*1024**2

def safe_name(name):
    path=PurePosixPath(name)
    if not name or path.is_absolute() or '..' in path.parts or '\\' in name or str(path)!=name:
        raise ValueError('unsafe archive path')
    return name

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk:=stream.read(CHUNK):h.update(chunk)
    return h.hexdigest()

def archive(files,output,*,reserve_bytes=2*1024**3,compression=zipfile.ZIP_DEFLATED):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    rows=[];unique={};names=set()
    for source,name in files:
        source=Path(source);safe_name(name)
        if name in names or name=='manifest.json':raise ValueError('duplicate archive path')
        names.add(name)
        if source.is_symlink() or not source.is_file():raise ValueError('unsafe source')
        size=source.stat().st_size;sha=digest(source)
        payload=unique.setdefault((size,sha),(source,name))[1]
        rows.append({'path':name,'size_bytes':size,'sha256':sha,'payload':payload,
                     'mode':stat.S_IMODE(source.stat().st_mode)})
    manifest={'format':1,'files':rows,'unique_bytes':sum(key[0] for key in unique)}
    # Deflate can be larger than its input. Require the uncompressed bound plus
    # per-file overhead and the system reserve before opening any archive.
    required=manifest['unique_bytes']+manifest['unique_bytes']//500+len(rows)*4096+reserve_bytes
    free=shutil.disk_usage(output.parent).free
    if free<required:
        if compression!=zipfile.ZIP_DEFLATED:
            raise OSError(28,f'backup needs {required} bytes; available {free}')
        compressed=0
        for source,_ in unique.values():
            compressor=zlib.compressobj(1,zlib.DEFLATED,-15)
            with source.open('rb') as stream:
                while chunk:=stream.read(CHUNK):compressed+=len(compressor.compress(chunk))
            compressed+=len(compressor.flush())
        required=compressed+len(json.dumps(manifest).encode())+len(rows)*4096+reserve_bytes
        manifest['measured_compressed_bytes']=compressed
        if shutil.disk_usage(output.parent).free<required:
            raise OSError(28,f'backup needs {required} bytes; available {shutil.disk_usage(output.parent).free}')
    descriptor,name=tempfile.mkstemp(prefix=output.name+'.partial-',dir=output.parent)
    os.close(descriptor)
    temporary=Path(name)
    try:
        with zipfile.ZipFile(temporary,'w',compression=compression,compresslevel=1 if compression==zipfile.ZIP_DEFLATED else None,allowZip64=True) as z:
            for source,name in unique.values():
                if shutil.disk_usage(output.parent).free<reserve_bytes:raise OSError(28,'backup reserve exhausted')
                with source.open('rb') as incoming,z.open(name,'w',force_zip64=True) as target:
                    shutil.copyfileobj(incoming,target,CHUNK)
            z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        with zipfile.ZipFile(temporary) as z:
            if z.testzip() is not None:raise ValueError('ZIP integrity failure')
            for row in rows:
                if row['payload']!=row['path']:continue
                h=hashlib.sha256();size=0
                with z.open(row['payload']) as stream:
                    while chunk:=stream.read(CHUNK):h.update(chunk);size+=len(chunk)
                if size!=row['size_bytes'] or h.hexdigest()!=row['sha256']:raise ValueError('archive hash mismatch')
        # Exclusive destination prevents replacing an earlier backup.
        os.link(temporary,output);temporary.unlink()
    finally:
        temporary.unlink(missing_ok=True)
    return {'files':len(rows),'unique_files':len(unique),'unique_bytes':manifest['unique_bytes'],
            'archive_bytes':output.stat().st_size,'sha256':digest(output),'zip_integrity':True}

def restore(archive_path,destination):
    destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(archive_path) as z:
        rows=json.loads(z.read('manifest.json'))['files']
        for row in rows:
            name=safe_name(row['path']);payload=safe_name(row['payload'])
            target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(payload) as stream,target.open('xb') as output:shutil.copyfileobj(stream,output,CHUNK)
            target.chmod(row['mode'])
    verify_restored(archive_path,destination)

def verify_restored(archive_path,destination):
    with zipfile.ZipFile(archive_path) as z:rows=json.loads(z.read('manifest.json'))['files']
    for row in rows:
        path=Path(destination)/safe_name(row['path'])
        if path.is_symlink() or path.stat().st_size!=row['size_bytes'] or digest(path)!=row['sha256']:
            raise ValueError('restore hash mismatch')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('archive');p.add_argument('destination')
    args=p.parse_args();restore(args.archive,args.destination)
