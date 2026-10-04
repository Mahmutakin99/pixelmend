"""Lazy, verified lifecycle for pinned multi-file generative packages.

This module never imports a model library. Only explicit installation performs
network I/O; verification and inference are local. Renderer paths are not used.
"""
import asyncio
from collections import defaultdict
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import threading
from uuid import uuid4

from filelock import FileLock, Timeout
import httpx

from .model_manager import ModelManagerError, _trusted_url
from .model_package import (ModelPackageFile, ModelPackageManifest, ModelPackageError,
                            _checked_path, _verify_file, verify_package)
from .compute import ComputeCoordinator

GIB = 1024**3


def check_cancel(cancel):
    if cancel.is_set():
        raise InterruptedError()


@dataclass(frozen=True, slots=True)
class PackagePart:
    path: str
    index: int
    size_bytes: int
    sha256: str
    local_path: str
    url: str | None = None

    def __post_init__(self):
        for path in (self.path, self.local_path):
            ModelPackageManifest('part', '0'*40, 'transport', 'https://example.test',
                                 (ModelPackageFile(path, self.size_bytes, self.sha256),))
        if type(self.index) is not int or self.index < 0 or self.size_bytes > GIB:
            raise ValueError('invalid transport part')
        if self.url is not None:
            _trusted_url(self.url)


@dataclass(frozen=True, slots=True)
class PackageDefinition:
    manifest: ModelPackageManifest
    name: str
    runtime: str
    operations: tuple[str, ...]
    source_repository: str
    source_revision: str
    parts: tuple[PackagePart, ...]
    accepted_profiles: tuple[dict, ...] = ()

    def __post_init__(self):
        if self.runtime not in {'mlx', 'torch-cpu'} or not self.operations:
            raise ValueError('invalid package runtime')
        if len(self.source_revision) != 40 or any(c not in '0123456789abcdef' for c in self.source_revision):
            raise ValueError('invalid source revision')
        by_file = defaultdict(list)
        for part in self.parts:
            by_file[part.path].append(part)
        if set(by_file) != {f.path for f in self.manifest.files}:
            raise ValueError('incomplete transport manifest')
        for file in self.manifest.files:
            parts = sorted(by_file[file.path], key=lambda p:p.index)
            if ([p.index for p in parts] != list(range(len(parts)))
                    or sum(p.size_bytes for p in parts) != file.size_bytes):
                raise ValueError('invalid transport sequence')

    @property
    def size_bytes(self):
        return sum(file.size_bytes for file in self.manifest.files)


def load_catalog():
    data=json.loads(Path(__file__).with_name('generative_catalog.json').read_text())
    definitions=[]
    for row in data['packages']:
        manifest=ModelPackageManifest(row['id'],row['package_revision'],row['license_id'],
            row['license_url'],tuple(ModelPackageFile(**f) for f in row['files']))
        definitions.append(PackageDefinition(manifest,row['name'],row['runtime'],tuple(row['operations']),
            row['source_repository'],row['source_revision'],tuple(PackagePart(**p) for p in row['parts']),
            tuple(row['accepted_profiles'])))
    return tuple(definitions)


def download_part(part, destination, cancel, progress):
    if not part.url:
        raise ModelManagerError('local_package_required','Model paketini yerel klasörden seçin.')
    url=part.url
    with httpx.Client(trust_env=False,follow_redirects=False,timeout=httpx.Timeout(5,connect=5),
                      headers={'Accept-Encoding':'identity'}) as client:
        for _ in range(6):
            check_cancel(cancel);_trusted_url(url)
            with client.stream('GET',url) as response:
                if response.is_redirect:
                    url=str(response.url.join(response.headers['location']));continue
                response.raise_for_status()
                if response.headers.get('content-encoding','identity')!='identity':
                    raise ModelManagerError('transport_error','Model aktarımı doğrulanamadı.')
                if response.headers.get('content-length') and int(response.headers['content-length'])!=part.size_bytes:
                    raise ModelManagerError('package_invalid','Paket boyutu doğrulanamadı.')
                count=0
                with destination.open('xb') as stream:
                    for chunk in response.iter_raw(chunk_size=1024**2):
                        check_cancel(cancel);count+=len(chunk)
                        if count>part.size_bytes:
                            raise ModelManagerError('package_invalid','Paket boyutu doğrulanamadı.')
                        stream.write(chunk);progress(count)
                    stream.flush();os.fsync(stream.fileno())
                return
    raise ModelManagerError('transport_error','Model aktarımı tamamlanamadı.')


def safe_directory(path, create=False):
    path=Path(path).absolute()
    if path.is_symlink():
        raise ModelPackageError('unsafe managed directory')
    if create:
        path.mkdir(mode=0o700,parents=True,exist_ok=True)
    if not path.is_dir():
        raise ModelPackageError('managed directory missing')
    return path


class PackageReservation:
    def __init__(self,manager,id,path):
        self.manager=manager;self.id=id;self.path=path;self.released=False

    def verify(self,cancel):
        if self.released:raise ModelManagerError('package_in_use','Model referansı kapandı.')
        try:verify_package(self.path,self.manager.catalog[self.id].manifest,cancel=cancel)
        except ModelPackageError:
            raise ModelManagerError('package_invalid','Paket eksik veya değiştirilmiş. Yeniden kurun.') from None
        self.manager._change(self.id,package_verified=True)

    def release(self):
        with self.manager._mutex:
            if not self.released:
                self.released=True
                lock=self.manager._lease_locks[self.id]
                lock.release()
                self.manager._views[self.id]['in_use']-=1;self.manager._version+=1
                if not lock.is_locked:self.manager._lease_locks.pop(self.id)


class PackageManager:
    def __init__(self, models_dir, *, catalog=None, downloader=download_part, prober=None, coordinator=None):
        definitions=load_catalog() if catalog is None else tuple(catalog)
        self.catalog={d.manifest.model_id:d for d in definitions}
        if len(self.catalog)!=len(definitions):
            raise ValueError('duplicate package id')
        self.models_dir=Path(models_dir).absolute()
        self.downloader=downloader;self.prober=prober
        self.coordinator=coordinator or ComputeCoordinator()
        self._mutex=threading.RLock();self._tasks={};self._cancels={};self._lease_locks={};self._closed=False
        self._io=asyncio.Semaphore(2);self._version=0;self._views={}
        for id,d in self.catalog.items():
            m=d.manifest
            self._views[id]={'id':id,'name':d.name,'state':'absent','source':'published' if all(p.url for p in d.parts) else 'local',
                'published':all(p.url for p in d.parts),'verified_manifest':True,'runtime':d.runtime,
                'operation':'generative','operations':list(d.operations),'tier':'balanced',
                'size_bytes':d.size_bytes,'downloaded_bytes':0,'revision':m.revision,'package_revision':m.revision,
                'source_revision':d.source_revision,'sha256':None,'license_id':m.license_id,'license_url':m.license_url,
                'source_repository':d.source_repository,'package_verified':False,
                'error':None,'probe':None,'in_use':0,'stored_bytes':0,'active_revision':None,'loaded':False,
                'accepted_profiles':list(d.accepted_profiles),'last_used_at':None,'stale_revisions':[],
                'description':('Fotoğrafa komutla nesne ekleme ve yeni görsel üretme.' if d.runtime=='mlx' else
                               'Türkçe komutları bu bilgisayarda İngilizceye çevirir.')}

    def _change(self,id,**values):
        with self._mutex:
            self._views[id].update(values);self._version+=1

    def _definition(self,id):
        try:return self.catalog[id]
        except KeyError:raise ModelManagerError('unknown_model','Model bulunamadı.',404) from None

    def list_models(self):
        with self._mutex:return {'models':deepcopy(list(self._views.values()))}

    def _paths(self,d,create=False):
        root=safe_directory(self.models_dir,create)
        parent=safe_directory(root/d.manifest.model_id,create)
        target=parent/d.manifest.revision
        lock=parent/f'.{d.manifest.revision}.lock'
        if target.is_symlink() or lock.is_symlink():raise ModelPackageError('unsafe target')
        return parent,target,lock

    async def start(self):
        # Metadata only. Hashing/native model loading must never delay startup.
        for id,d in self.catalog.items():
            try:_,target,_=self._paths(d)
            except ModelPackageError:continue
            if target.is_dir() and not target.is_symlink():
                sizes=sum(p.stat().st_size for p in target.rglob('*') if p.is_file() and not p.is_symlink())
                self._change(id,state='installed',stored_bytes=sizes,active_revision=d.manifest.revision)

    async def _launch(self,id,operation,source=None):
        d=self._definition(id)
        with self._mutex:
            if self._closed or self._views[id]['in_use'] or id in self._tasks:
                raise ModelManagerError('package_in_use','Model kullanımda; işlem bitmesini bekleyin.')
            cancel=threading.Event();self._cancels[id]=cancel
            self._change(id,state='waiting',error=None)
            async def work():
                values={}
                try:
                    async with self._io:
                        values=await asyncio.to_thread(self._operate,d,operation,cancel,source)
                except InterruptedError:values={'state':'cancelled','error':None}
                except Exception as error:
                    if isinstance(error,ModelManagerError):code,message=error.code,str(error)
                    elif isinstance(error,ModelPackageError):code,message='package_invalid','Paket eksik veya değiştirilmiş. Doğrulanmış paketi yeniden kurun.'
                    elif isinstance(error,OSError) and error.errno==28:code,message='disk_insufficient','Model kurulumu için disk alanı yetersiz.'
                    elif isinstance(error,PermissionError):code,message='permission_denied','Model klasörüne yazılamadı.'
                    else:code,message='transport_error','Model işlemi tamamlanamadı. Yeniden deneyin.'
                    values={'state':'failed','error':{'code':code,'message':message}}
                finally:
                    with self._mutex:
                        self._tasks.pop(id,None);self._cancels.pop(id,None)
                        self._change(id,**values)
            self._tasks[id]=asyncio.create_task(work())
        return self.list_models()

    async def install(self,id):return await self._launch(id,'install')
    async def install_local(self,id,source):return await self._launch(id,'install',Path(source))
    async def retry(self,id):return await self.install(id)
    async def probe(self,id):return await self._launch(id,'probe')
    async def delete(self,id):return await self._launch(id,'delete')
    async def cancel(self,id):
        self._definition(id)
        with self._mutex:
            cancel=self._cancels.get(id)
            if cancel:cancel.set();self._change(id,state='cancelling')
        return self.list_models()

    def _operate(self,d,operation,cancel,source):
        id=d.manifest.model_id
        check_cancel(cancel)
        parent,target,lock=self._paths(d,create=True)
        with FileLock(lock,timeout=0):
            if operation=='delete':
                self._change(id,state='deleting')
                if target.exists():shutil.rmtree(target)
                cache=parent/f'.{d.manifest.revision}.staging'
                if cache.exists():shutil.rmtree(safe_directory(cache))
                return dict(state='absent',stored_bytes=0,active_revision=None,probe=None,package_verified=False)
            if operation=='probe':
                self._change(id,state='verifying');verify_package(target,d.manifest,cancel=cancel)
                if self.prober is None:raise ModelManagerError('runtime_unavailable','Yerel çalışma paketi bulunamadı.')
                with self.coordinator.operation('probe',cancel):
                    self._change(id,state='probing')
                    evidence=self.prober(d,target,cancel)
                check_cancel(cancel)
                return dict(state='installed',probe=evidence,loaded=False,package_verified=True)
            self._install(d,parent,target,cancel,source)
            return dict(state='installed',stored_bytes=d.size_bytes,active_revision=d.manifest.revision,
                        downloaded_bytes=d.size_bytes,probe=None,loaded=False,package_verified=True)

    def _install(self,d,parent,target,cancel,source):
        id=d.manifest.model_id
        try:verify_package(target,d.manifest,cancel=cancel);return
        except ModelPackageError:pass
        if source is not None:safe_directory(source)
        cache=safe_directory(parent/f'.{d.manifest.revision}.staging',create=True)
        parts_dir=safe_directory(cache/'parts',create=True)
        assembled=cache/'assembled'
        if assembled.exists():shutil.rmtree(safe_directory(assembled))
        unique_parts={part.sha256:part for part in d.parts}
        required=d.size_bytes+64*1024**2
        for part in unique_parts.values():
            try:_verify_file(parts_dir,ModelPackageFile(part.sha256,part.size_bytes,part.sha256),cancel)
            except ModelPackageError:required+=part.size_bytes
        if shutil.disk_usage(parent).free < required:
            raise ModelManagerError('disk_insufficient','Model kurulumu için disk alanı yetersiz.')
        completed=0
        for part in d.parts:
            check_cancel(cancel)
            file=ModelPackageFile(part.sha256,part.size_bytes,part.sha256)
            cached=parts_dir/part.sha256
            try:_verify_file(parts_dir,file,cancel)
            except ModelPackageError:
                if cached.is_symlink():raise ModelPackageError('unsafe cached part')
                if cached.exists():cached.unlink()
                temporary=parts_dir/f'{part.sha256}.partial'
                if temporary.is_symlink():raise ModelPackageError('unsafe temporary part')
                temporary.unlink(missing_ok=True)
                self._change(id,state='installing' if source is not None else 'downloading')
                try:
                    if source is not None:
                        source_file=_checked_path(source,part.local_path)
                        flags=os.O_RDONLY | (os.O_NOFOLLOW if os.name!='nt' else 0)
                        with os.fdopen(os.open(source_file,flags),'rb') as incoming, temporary.open('xb') as output:
                            count=0
                            while chunk:=incoming.read(1024**2):
                                check_cancel(cancel);count+=len(chunk)
                                if count>part.size_bytes:raise ModelPackageError('oversize local part')
                                output.write(chunk)
                            output.flush();os.fsync(output.fileno())
                    else:self.downloader(part,temporary,cancel,lambda count:self._change(id,downloaded_bytes=completed+count))
                    self._change(id,state='verifying')
                    _verify_file(parts_dir,ModelPackageFile(temporary.name,part.size_bytes,part.sha256),cancel)
                    os.replace(temporary,cached)
                finally:temporary.unlink(missing_ok=True)
            completed+=part.size_bytes;self._change(id,downloaded_bytes=completed)
        assembled.mkdir(mode=0o700)
        for file in d.manifest.files:
            destination=assembled/file.path;destination.parent.mkdir(parents=True,exist_ok=True)
            with destination.open('xb') as output:
                for part in sorted((p for p in d.parts if p.path==file.path),key=lambda p:p.index):
                    with (parts_dir/part.sha256).open('rb') as incoming:
                        while chunk:=incoming.read(1024**2):check_cancel(cancel);output.write(chunk)
                output.flush();os.fsync(output.fileno())
        verify_package(assembled,d.manifest,cancel=cancel);check_cancel(cancel)
        backup=parent/f'.{d.manifest.revision}.invalid-{uuid4().hex}' if target.exists() else None
        if backup:os.replace(target,backup)
        try:os.replace(assembled,target)
        except BaseException:
            if backup:os.replace(backup,target)
            raise
        if backup:shutil.rmtree(backup)
        shutil.rmtree(cache)

    @contextmanager
    def lease(self,id):
        reservation=self.reserve(id)
        try:
            reservation.verify(threading.Event())
            yield reservation.path
        finally:reservation.release()

    def reserve(self,id):
        """Pin an immutable revision now; hash later in the inference worker."""
        d=self._definition(id)
        with self._mutex:
            if id in self._tasks or self._closed:
                raise ModelManagerError('package_in_use','Model kullanımda; işlem bitmesini bekleyin.')
            try:
                _,target,lock_path=self._paths(d)
                if not target.is_dir():raise ModelPackageError('package missing')
                lock=self._lease_locks.get(id)
                if lock is None:lock=FileLock(lock_path,timeout=0,thread_local=False)
                lock.acquire()
            except ModelPackageError:
                raise ModelManagerError('package_invalid','Paket eksik veya değiştirilmiş. Yeniden kurun.') from None
            except Timeout:
                raise ModelManagerError('package_in_use','Model kullanımda; işlem bitmesini bekleyin.') from None
            self._lease_locks[id]=lock
            self._views[id]['in_use']+=1;self._version+=1
            return PackageReservation(self,id,target)

    async def close(self):
        with self._mutex:
            self._closed=True
            for cancel in self._cancels.values():cancel.set()
            tasks=list(self._tasks.values())
        if tasks:await asyncio.gather(*tasks)


class CombinedModelManager:
    """Keep the existing ONNX methods and merge only snapshots/lifecycle routing."""
    def __init__(self,onnx,packages):self.onnx=onnx;self.packages=packages
    def __getattr__(self,name):return getattr(self.onnx,name)
    def list_models(self):return {'models':self.onnx.list_models()['models']+self.packages.list_models()['models']}
    async def start(self):await self.packages.start();await self.onnx.start()
    async def close(self):await self.packages.close();await self.onnx.close()
    async def events(self):
        previous=None;ticks=0
        while True:
            value=self.list_models()
            if value!=previous:previous=value;ticks=0;yield value
            elif ticks>=30:ticks=0;yield None
            ticks+=1;await asyncio.sleep(.1)
    async def _route(self,id,operation,*args):
        manager=self.packages if id in self.packages.catalog else self.onnx
        result=await getattr(manager,operation)(id,*args)
        return self.list_models() if isinstance(result,dict) and 'models' in result else result
    async def install(self,id):return await self._route(id,'install')
    async def install_local(self,id,source):return await self._route(id,'install_local',source)
    async def retry(self,id):return await self._route(id,'retry')
    async def cancel(self,id):return await self._route(id,'cancel')
    async def probe(self,id):return await self._route(id,'probe')
    async def delete(self,id):return await self._route(id,'delete')
