"""Exercise real model lifecycle with tiny immutable local fixtures."""

import asyncio
import hashlib
import threading
from pathlib import Path

import pytest
from filelock import FileLock

from pixelmend_engine.model_catalog import ModelCatalogEntry
from pixelmend_engine.model_manager import ModelManager, ModelManagerError
from pixelmend_engine.model_store import ModelManifest, model_file_path


PAYLOAD = b'local model fixture'


def fixture_entry():
    manifest = ModelManifest('fixture', 'owner/repo', 'a' * 40, 'model.onnx',
                             len(PAYLOAD), hashlib.sha256(PAYLOAD).hexdigest(),
                             'Apache-2.0', 'https://example.org/license')
    return ModelCatalogEntry('fixture', 'Fixture', manifest)


def download(manifest, destination, cancel, progress):
    destination.write_bytes(PAYLOAD)
    progress(len(PAYLOAD))


def probe(manifest, path):
    assert path.read_bytes() == PAYLOAD
    return {'selected_provider': 'CPUExecutionProvider', 'providers': ['CPUExecutionProvider']}


async def settle(manager):
    for _ in range(400):
        state = manager.list_models()['models'][0]['state']
        if state not in {'waiting', 'downloading', 'verifying', 'probing', 'deleting', 'cancelling'}:
            return state
        await asyncio.sleep(.01)
    raise AssertionError('model lifecycle did not settle')


def test_install_lease_delete_and_unpublished(tmp_path):
    async def run():
        manager = ModelManager(tmp_path, catalog=[fixture_entry()], downloader=download, prober=probe)
        await manager.start()
        await manager.install('fixture')
        assert await settle(manager) == 'ready'
        view = manager.list_models()['models'][0]
        assert view['downloaded_bytes'] == len(PAYLOAD)
        assert view['probe']['status'] == 'passed'
        with manager.lease('fixture') as path:
            assert path.read_bytes() == PAYLOAD
            assert manager.selected_provider('fixture') == 'CPUExecutionProvider'
            assert manager.list_models()['models'][0]['in_use'] == 1
            with pytest.raises(ModelManagerError, match='in use'):
                await manager.delete('fixture')
        await manager.delete('fixture')
        assert await settle(manager) == 'absent'
        assert not path.exists()
        await manager.close()

        defaults = ModelManager(tmp_path)
        ai = next(v for v in defaults.list_models()['models'] if v['id'] == 'realesrgan-x4plus')
        assert ai['state'] == 'unavailable' and ai['published'] is False
        assert ai['sha256'] is None and ai['size_bytes'] is None and ai['revision'] is None
        with pytest.raises(ModelManagerError):
            await defaults.install(ai['id'])
        await defaults.close()
    asyncio.run(run())


@pytest.mark.parametrize('payload,code', [(b'bad', 'size_mismatch'), (b'x' * len(PAYLOAD), 'hash_mismatch')])
def test_corrupt_download_is_never_activated_and_retry_recovers(tmp_path, payload, code):
    async def run():
        attempts = 0
        def transport(manifest, path, cancel, progress):
            nonlocal attempts
            attempts += 1
            path.write_bytes(payload if attempts == 1 else PAYLOAD)
        manager = ModelManager(tmp_path, catalog=[fixture_entry()], downloader=transport, prober=probe)
        await manager.install('fixture')
        assert await settle(manager) == 'error'
        assert manager.list_models()['models'][0]['error']['code'] == code
        target = model_file_path(tmp_path, fixture_entry().manifest)
        assert not target.exists()
        assert not list(target.parent.glob('*.partial-*'))
        await manager.retry('fixture')
        assert await settle(manager) == 'ready'
        await manager.close()
    asyncio.run(run())


def test_cancel_drains_download_and_keeps_event_loop_responsive(tmp_path):
    started = threading.Event()
    ended = threading.Event()
    def transport(manifest, path, cancel, progress):
        path.write_bytes(b'partial')
        started.set()
        cancel.wait(3)
        ended.set()
    async def run():
        manager = ModelManager(tmp_path, catalog=[fixture_entry()], downloader=transport, prober=probe)
        await manager.install('fixture')
        assert await asyncio.to_thread(started.wait, 2)
        await manager.cancel('fixture')
        await manager.close()
        assert ended.is_set()
        assert manager.list_models()['models'][0]['state'] == 'cancelled'
        assert not list(tmp_path.rglob('*.onnx'))
    asyncio.run(run())


def test_cancel_while_waiting_for_existing_store_lock(tmp_path):
    entry = fixture_entry()
    target = model_file_path(tmp_path, entry.manifest)
    target.parent.mkdir(parents=True)
    lock = FileLock(target.with_name(f'.{target.name}.lock'))
    async def run():
        manager = ModelManager(tmp_path, catalog=[entry], downloader=download, prober=probe)
        with lock:
            await manager.install('fixture')
            await asyncio.sleep(.06)
            assert manager.list_models()['models'][0]['state'] == 'waiting'
            await manager.cancel('fixture')
            await asyncio.wait_for(manager.close(), .5)
        assert not target.exists()
    asyncio.run(run())


def test_symlink_escape_and_unknown_id_rejected(tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    root = tmp_path / 'models'
    root.mkdir()
    (root / 'fixture').symlink_to(outside, target_is_directory=True)
    async def run():
        manager = ModelManager(root, catalog=[fixture_entry()], downloader=download, prober=probe)
        with pytest.raises(ModelManagerError):
            await manager.install('../outside')
        await manager.install('fixture')
        assert await settle(manager) == 'error'
        assert manager.list_models()['models'][0]['error']['code'] == 'unsafe_path'
        assert list(outside.iterdir()) == []
        await manager.close()
    asyncio.run(run())


def test_start_verifies_cache_without_loading_runtime(tmp_path):
    entry = fixture_entry()
    target = model_file_path(tmp_path, entry.manifest)
    target.parent.mkdir(parents=True)
    target.write_bytes(PAYLOAD)
    probes = 0
    def bad_probe(manifest, path):
        nonlocal probes
        probes += 1
        raise RuntimeError('private/path/secret')
    async def run():
        manager = ModelManager(tmp_path, catalog=[entry], prober=bad_probe)
        await manager.start()
        assert await settle(manager) == 'installed'
        assert probes == 0
        view = manager.list_models()['models'][0]
        assert view['probe']['status'] == 'unmeasured'
        with pytest.raises(ModelManagerError):
            with manager.lease('fixture'):
                pass
        await manager.probe('fixture')
        assert await settle(manager) == 'error'
        assert probes == 1
        assert 'private' not in str(manager.list_models()['models'][0])
        await manager.close()
    asyncio.run(run())
