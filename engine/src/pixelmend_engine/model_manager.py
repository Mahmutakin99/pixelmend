"""Nonblocking lifecycle, verified activation and inference leases for local models."""

import asyncio
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
from tempfile import TemporaryDirectory
import threading
from urllib.parse import quote, urlparse

from filelock import FileLock, Timeout
import httpx

from .model_catalog import DEFAULT_MODEL_CATALOG, ModelCatalogEntry
from .model_store import ModelManifest, model_file_path

CHUNK_BYTES = 1024 * 1024
DISK_RESERVE_BYTES = 64 * 1024 * 1024


class ModelManagerError(ValueError):
    """Public errors contain stable codes and safe, path-free messages."""

    def __init__(self, code: str, message: str, status_code: int = 409):
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class _Cancelled(Exception):
    pass


def _check_cancel(cancel: threading.Event):
    if cancel.is_set():
        raise _Cancelled()


def _trusted_url(url: str):
    parsed = urlparse(url)
    host = parsed.hostname or ''
    if (parsed.scheme != 'https' or parsed.username or parsed.password
            or parsed.port not in (None, 443)
            or not any(host == domain or host.endswith('.' + domain)
                       for domain in ('huggingface.co', 'hf.co', 'github.com',
                                      'objects.githubusercontent.com',
                                      'release-assets.githubusercontent.com'))):
        raise ModelManagerError('transport_error', 'Model host is not trusted.')


def stream_pinned_model(manifest: ModelManifest, destination: Path,
                        cancel: threading.Event, progress: Callable[[int], None]):
    """Fetch one allowlisted HTTPS artifact and verify it before activation."""
    if manifest.download_url:
        url = manifest.download_url
    elif re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+', manifest.repo_id):
        url = (f'https://huggingface.co/{manifest.repo_id}/resolve/'
               f'{manifest.revision}/{quote(manifest.filename, safe="")}')
    else:
        raise ModelManagerError('invalid_manifest', 'Invalid model repository.')
    # Explicit redirect validation prevents signed-CDN redirects from escaping HTTPS hosts.
    with httpx.Client(trust_env=False, follow_redirects=False,
                      timeout=httpx.Timeout(5, connect=5), headers={'Accept-Encoding': 'identity'}) as client:
        for _ in range(6):
            _check_cancel(cancel)
            _trusted_url(url)
            with client.stream('GET', url) as response:
                if response.is_redirect:
                    url = str(response.url.join(response.headers['location']))
                    continue
                response.raise_for_status()
                length = response.headers.get('content-length')
                if length is not None and int(length) != manifest.size_bytes:
                    raise ModelManagerError('size_mismatch', 'Model size does not match its manifest.')
                if response.headers.get('content-encoding', 'identity') != 'identity':
                    raise ModelManagerError('transport_error', 'Encoded model transport is unsupported.')
                total = 0
                with destination.open('xb') as output:
                    for chunk in response.iter_raw(chunk_size=CHUNK_BYTES):
                        _check_cancel(cancel)
                        total += len(chunk)
                        if total > manifest.size_bytes:
                            raise ModelManagerError('size_mismatch', 'Model exceeds its manifest size.')
                        output.write(chunk)
                        progress(total)
                    output.flush()
                    os.fsync(output.fileno())
                _check_cancel(cancel)
                return
    raise ModelManagerError('transport_error', 'Too many model download redirects.')


# Kept as an import-compatible name for callers that only use Hugging Face manifests.
stream_hugging_face_model = stream_pinned_model


class ModelManager:
    """Workers own blocking IO; state and leases are protected across loop/worker threads."""

    def __init__(self, models_dir: Path, *, catalog: Iterable[ModelCatalogEntry] = DEFAULT_MODEL_CATALOG,
                 downloader=stream_pinned_model, prober=None):
        self.models_dir = Path(models_dir).absolute()
        entries = tuple(catalog)
        self._catalog = {entry.id: entry for entry in entries}
        if len(entries) != len(self._catalog):
            raise ValueError('duplicate model catalog id')
        for entry in entries:
            if not re.fullmatch(r'[a-zA-Z0-9_-]+', entry.id):
                raise ValueError('invalid catalog id')
            if entry.manifest and entry.manifest.model_id != entry.id:
                raise ValueError('catalog id differs from manifest')
        self._downloader = downloader
        self._prober = prober
        self._mutex = threading.RLock()
        self._tasks: dict[str, asyncio.Task] = {}
        self._cancels: dict[str, threading.Event] = {}
        self._signatures = {}
        self._lease_locks = {}
        self._closed = False
        self._started = False
        self._version = 0
        self._views = {}
        for entry in entries:
            m = entry.manifest
            self._views[entry.id] = {
                'id': entry.id, 'name': entry.name,
                'state': 'absent' if m else 'unavailable', 'published': m is not None and entry.source == 'published',
                'source': entry.source, 'verified_manifest': m is not None,
                'size_bytes': m.size_bytes if m else None, 'downloaded_bytes': 0,
                'revision': m.revision if m else None, 'sha256': m.sha256 if m else None,
                'license_id': m.license_id if m else None, 'license_url': m.license_url if m else None,
                'error': None, 'probe': None, 'in_use': 0,
                'stored_bytes': 0, 'active_revision': m.revision if m else None,
                'last_used_at': None, 'stale_revisions': [],
                'operation': entry.operation, 'tier': entry.tier,
                'description': entry.description,
                'minimum_memory_bytes': entry.minimum_memory_bytes,
                'recommended_memory_bytes': entry.recommended_memory_bytes,
            }

    def _entry(self, model_id):
        try:
            return self._catalog[model_id]
        except KeyError:
            raise ModelManagerError('unknown_model', 'Unknown model.', 404) from None

    def _change(self, model_id, **values):
        with self._mutex:
            self._views[model_id].update(values)
            self._version += 1

    def list_models(self):
        with self._mutex:
            return {'models': deepcopy(list(self._views.values()))}

    def _target(self, manifest, *, create=False):
        """Reject symlinks in managed components and lock paths before filesystem work."""
        root = self.models_dir
        # Existing ancestors may contain platform aliases (/var -> /private/var),
        # but the explicitly chosen root and every component below it must be real.
        if root.is_symlink():
            raise ModelManagerError('unsafe_path', 'Model storage contains an unsafe path.')
        if create:
            root.mkdir(parents=True, exist_ok=True)
        current = root
        for name in (manifest.model_id, manifest.revision):
            current = current / name
            if current.is_symlink():
                raise ModelManagerError('unsafe_path', 'Model storage contains an unsafe path.')
            if create:
                current.mkdir(exist_ok=True)
        target = model_file_path(root, manifest)
        for candidate in (target, target.with_name(f'.{target.name}.lock')):
            if candidate.is_symlink():
                raise ModelManagerError('unsafe_path', 'Model storage contains an unsafe path.')
        return target

    @staticmethod
    def _signature(info):
        # Windows can report a different creation-time value through an open
        # descriptor and a later path stat for the same untouched file. The
        # creation time is not a content mutation signal; device, inode, size
        # and modification time still detect replacement during verification.
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)

    def _verify(self, path, manifest, cancel):
        """Hash a regular file in bounded chunks, allowing cancellation during verification."""
        _check_cancel(cancel)
        try:
            # O_NOFOLLOW/O_NONBLOCK are POSIX hardening flags. They are not
            # supported by Windows' os.open implementation, where passing them
            # turns an ordinary local model into a generic transport error.
            flags = os.O_RDONLY
            if os.name != 'nt':
                flags |= os.O_NOFOLLOW | os.O_NONBLOCK
            descriptor = os.open(path, flags)
        except FileNotFoundError:
            raise ModelManagerError('missing_model', 'Model is not installed.') from None
        with os.fdopen(descriptor, 'rb') as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise ModelManagerError('unsafe_path', 'Model is not a regular file.')
            if info.st_size != manifest.size_bytes:
                raise ModelManagerError('size_mismatch', 'Model size does not match its manifest.')
            digest = hashlib.sha256()
            while chunk := source.read(CHUNK_BYTES):
                _check_cancel(cancel)
                digest.update(chunk)
            if digest.hexdigest() != manifest.sha256:
                raise ModelManagerError('hash_mismatch', 'Model hash does not match its manifest.')
            final = os.fstat(source.fileno())
            if self._signature(info) != self._signature(final):
                raise ModelManagerError('changed_model', 'Model changed during verification.')
            return self._signature(final)

    async def start(self):
        """Discover cached artifacts inside the app lifespan, never during construction."""
        if self._started:
            return
        self._started = True
        for entry in self._catalog.values():
            if entry.manifest:
                # A missing cache is ordinary; discovery does not download anything.
                # Complete the cheap cache scan before accepting a user install.
                # Otherwise a fresh install can be accidentally coalesced into discovery.
                await asyncio.to_thread(self._operate, entry.manifest, 'discover', threading.Event())

    async def _launch(self, model_id, operation, source=None):
        entry = self._entry(model_id)
        with self._mutex:
            if self._closed:
                raise ModelManagerError('closed', 'Model manager is shutting down.')
            if entry.manifest is None:
                raise ModelManagerError('unpublished', 'This model has no verified published artifact.')
            if operation == 'install' and entry.source == 'local' and source is None:
                raise ModelManagerError('local_source_required', 'Choose the verified local ONNX file.')
            view = self._views[model_id]
            if view['in_use']:
                raise ModelManagerError('in_use', 'Model is in use.')
            task = self._tasks.get(model_id)
            if task and not task.done():
                if operation == 'install' and view['state'] != 'cancelling':
                    return self.list_models()
                raise ModelManagerError('busy', 'A model operation is already active.')
            cancel = threading.Event()
            self._cancels[model_id] = cancel
            self._change(model_id, state='waiting', error=None)
            self._tasks[model_id] = asyncio.create_task(asyncio.to_thread(
                self._operate, entry.manifest, operation, cancel, source))
        return self.list_models()

    async def install(self, model_id):
        return await self._launch(model_id, 'install')

    async def install_local(self, model_id, source):
        return await self._launch(model_id, 'install', Path(source))

    async def retry(self, model_id):
        return await self._launch(model_id, 'install')

    async def probe(self, model_id):
        return await self._launch(model_id, 'probe')

    async def delete(self, model_id):
        return await self._launch(model_id, 'delete')

    async def cancel(self, model_id):
        self._entry(model_id)
        with self._mutex:
            task = self._tasks.get(model_id)
            if task and not task.done():
                self._cancels[model_id].set()
                self._change(model_id, state='cancelling')
        return self.list_models()

    def _operate(self, manifest, operation, cancel, source=None):
        model_id = manifest.model_id
        lock = None
        try:
            target = self._target(manifest, create=operation == 'install')
            if operation == 'discover' and not target.exists():
                self._change(model_id, state='absent')
                return
            if not target.parent.exists():
                if operation == 'delete':
                    self._change(model_id, state='absent', downloaded_bytes=0, stored_bytes=0, probe=None)
                    return
                raise ModelManagerError('missing_model', 'Model is not installed.')
            lock = FileLock(target.with_name(f'.{target.name}.lock'))
            while True:
                _check_cancel(cancel)
                try:
                    lock.acquire(timeout=0)
                    break
                except Timeout:
                    cancel.wait(.05)
            self._target(manifest)
            _check_cancel(cancel)
            if operation == 'delete':
                self._change(model_id, state='deleting')
                target.unlink(missing_ok=True)
                self._signatures.pop(model_id, None)
                self._change(model_id, state='absent', downloaded_bytes=0, stored_bytes=0, probe=None)
                return
            self._change(model_id, state='verifying')
            try:
                signature = self._verify(target, manifest, cancel)
            except ModelManagerError as error:
                if operation != 'install' or error.code not in {'missing_model', 'size_mismatch', 'hash_mismatch'}:
                    raise
                if shutil.disk_usage(target.parent).free < manifest.size_bytes + DISK_RESERVE_BYTES:
                    raise ModelManagerError('insufficient_disk', 'Not enough free disk space for this model.')
                self._change(model_id, state='downloading', downloaded_bytes=0, probe=None)
                # Staging and activation stay beside the target under the existing store lock.
                with TemporaryDirectory(dir=target.parent, prefix=f'.{target.name}.partial-') as staging:
                    candidate = Path(staging) / manifest.filename
                    def progress(count):
                        _check_cancel(cancel)
                        if not isinstance(count, int) or not 0 <= count <= manifest.size_bytes:
                            raise ModelManagerError('size_mismatch', 'Model exceeds its manifest size.')
                        self._change(model_id, downloaded_bytes=count)
                    if source is None:
                        self._downloader(manifest, candidate, cancel, progress)
                    else:
                        # Local files pass the same pinned digest gate as downloaded bytes.
                        self._verify(source, manifest, cancel)
                        with source.open('rb') as incoming, candidate.open('xb') as outgoing:
                            count = 0
                            while chunk := incoming.read(CHUNK_BYTES):
                                count += len(chunk)
                                progress(count)
                                outgoing.write(chunk)
                            outgoing.flush()
                            os.fsync(outgoing.fileno())
                    _check_cancel(cancel)
                    self._change(model_id, state='verifying')
                    self._verify(candidate, manifest, cancel)
                    self._target(manifest)
                    _check_cancel(cancel)
                    os.replace(candidate, target)
                    signature = self._signature(target.stat())
            self._signatures[model_id] = signature
            self._change(model_id, downloaded_bytes=manifest.size_bytes, stored_bytes=manifest.size_bytes)
            _check_cancel(cancel)
            if self._prober is None:
                self._change(model_id, state='installed', probe={
                    'status': 'unmeasured', 'selected_provider': None, 'providers': [], 'measured_at': None})
                return
            probe = {'status': 'running', 'selected_provider': None, 'providers': [], 'measured_at': None}
            self._change(model_id, state='probing', probe=probe)
            try:
                result = self._prober(manifest, target)
                selected = result['selected_provider']
                providers = result['providers']
                if (result.get('status', 'passed') != 'passed' or not isinstance(selected, str)
                        or not isinstance(providers, list) or selected not in providers
                        or not all(isinstance(p, str) and p.endswith('ExecutionProvider') for p in providers)):
                    raise ValueError('invalid probe result')
                if self._signature(target.stat()) != signature:
                    raise ValueError('model changed during probe')
            except Exception:
                self._change(model_id, probe={**probe, 'status': 'failed',
                             'measured_at': datetime.now(timezone.utc).isoformat()})
                raise ModelManagerError('probe_failed', 'Model runtime probe failed.') from None
            _check_cancel(cancel)
            self._change(model_id, state='ready', probe={
                'status': 'passed', 'selected_provider': selected, 'providers': providers,
                'execution': result.get('execution'),
                'measured_at': datetime.now(timezone.utc).isoformat()})
        except _Cancelled:
            self._change(model_id, state='cancelled', error=None)
        except ModelManagerError as error:
            self._change(model_id, state='error', error={'code': error.code, 'message': str(error)})
        except Exception:
            self._change(model_id, state='error', error={
                'code': 'transport_error' if operation == 'install' else 'model_error',
                'message': 'Model operation failed. Retry or check local storage.'})
        finally:
            if lock is not None and lock.is_locked:
                lock.release()

    @contextmanager
    def lease(self, model_id):
        """Pin a verified/probed artifact from queue admission through native completion."""
        entry = self._entry(model_id)
        with self._mutex:
            view = self._views[model_id]
            if self._closed or view['state'] != 'ready':
                raise ModelManagerError('not_ready', 'Model is not ready; install or probe it first.')
            target = self._target(entry.manifest)
            try:
                if self._signature(target.stat()) != self._signatures.get(model_id):
                    raise ModelManagerError('changed_model', 'Model changed; probe it again before use.')
            except OSError:
                raise ModelManagerError('missing_model', 'Model is not installed.') from None
            if view['in_use'] == 0:
                lock = FileLock(target.with_name(f'.{target.name}.lock'), thread_local=False)
                try:
                    lock.acquire(timeout=0)
                except Timeout:
                    raise ModelManagerError('busy', 'Model is being modified by another process.') from None
                self._lease_locks[model_id] = lock
            self._change(model_id, in_use=view['in_use'] + 1)
            self._change(model_id, last_used_at=datetime.now(timezone.utc).isoformat())
        try:
            yield target
        finally:
            with self._mutex:
                count = self._views[model_id]['in_use'] - 1
                self._change(model_id, in_use=count)
                if count == 0:
                    self._lease_locks.pop(model_id).release()

    def selected_provider(self, model_id):
        self._entry(model_id)
        with self._mutex:
            probe = self._views[model_id]['probe']
            if not probe or probe['status'] != 'passed':
                raise ModelManagerError('not_ready', 'Model has no successful runtime probe.')
            return probe['selected_provider']

    async def events(self):
        """Coalesce progress into bounded latest-state SSE instead of unbounded queues."""
        version = -1
        ticks = 0
        while not self._closed:
            with self._mutex:
                changed = version != self._version
                version = self._version
                snapshot = self.list_models() if changed else None
            if snapshot is not None:
                yield snapshot
            elif ticks % 60 == 0:
                yield None
            ticks += 1
            await asyncio.sleep(.25)

    async def close(self):
        """Cancel transport cooperatively and drain threads, including native probes."""
        with self._mutex:
            self._closed = True
            for model_id, task in self._tasks.items():
                if not task.done():
                    self._cancels[model_id].set()
            tasks = list(self._tasks.values())
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
