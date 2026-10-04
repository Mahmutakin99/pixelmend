import asyncio
from contextlib import ExitStack
import hashlib
import threading

import pytest

from pixelmend_engine.generative_packages import (
    PackageDefinition, PackageManager, PackagePart, load_catalog,
)
from pixelmend_engine.model_manager import ModelManagerError
from pixelmend_engine.model_package import ModelPackageFile, ModelPackageManifest


def sha(data):
    return hashlib.sha256(data).hexdigest()


def definition(revision='a' * 40):
    files = (ModelPackageFile('weights.safetensors', 6, sha(b'abcdef')),
             ModelPackageFile('tokenizer/config.json', 3, sha(b'cfg')))
    return PackageDefinition(ModelPackageManifest('test-package', revision, 'Apache-2.0',
        'https://example.test/license', files), 'Test model', 'mlx', ('text_edit', 'text_to_image'),
        'official/model', 'b' * 40,
        (PackagePart('weights.safetensors', 0, 3, sha(b'abc'), 'weights.part0'),
         PackagePart('weights.safetensors', 1, 3, sha(b'def'), 'weights.part1'),
         PackagePart('tokenizer/config.json', 0, 3, sha(b'cfg'), 'tokenizer/config.json')))


async def settle(manager, model_id='test-package'):
    for _ in range(1000):
        view = manager.list_models()['models'][0]
        if view['state'] in {'installed', 'cancelled', 'failed', 'absent'}:
            return view
        await asyncio.sleep(.001)
    pytest.fail('package task did not settle')


def test_catalog_has_real_hashes_and_never_claims_unaccepted_profiles():
    catalog = load_catalog()
    assert len(catalog) == 2
    assert {d.manifest.model_id for d in catalog} == {'flux2-klein-4b-mlx-q4', 'opus-mt-tc-big-tr-en-f16'}
    for d in catalog:
        assert d.accepted_profiles == ()
        assert sum(f.size_bytes for f in d.manifest.files) > 400_000_000
        assert all(p.size_bytes <= 1024**3 and p.url is None for p in d.parts)
        assert d.source_revision != d.manifest.revision


def test_rejects_path_traversal_and_incomplete_transport():
    d = definition()
    with pytest.raises(ValueError):
        PackagePart('weights.safetensors', 0, 1, sha(b'x'), '../outside')
    with pytest.raises(ValueError):
        PackagePart('weights.safetensors', 0, 1, sha(b'x'), 'dir\\outside')
    with pytest.raises(ValueError):
        PackageDefinition(d.manifest, d.name, d.runtime, d.operations,
                          d.source_repository, d.source_revision, d.parts[:-1])


def test_failed_install_preserves_old_revision_and_reuses_verified_parts(tmp_path):
    async def check():
        calls=[]; fail=[True]
        def download(part, destination, cancel, progress):
            calls.append(part.local_path)
            if part.index == 1 and fail[0]:
                raise OSError('synthetic interrupted transport')
            destination.write_bytes({'weights.part0':b'abc', 'weights.part1':b'def',
                                     'tokenizer/config.json':b'cfg'}[part.local_path])
        old = tmp_path/'test-package'/('c'*40)
        old.mkdir(parents=True);(old/'old').write_bytes(b'healthy')
        manager=PackageManager(tmp_path, catalog=(definition(),), downloader=download)
        await manager.start();await manager.install('test-package')
        assert (await settle(manager))['state']=='failed'
        assert (old/'old').read_bytes()==b'healthy'
        assert not (tmp_path/'test-package'/('a'*40)).exists()
        fail[0]=False;await manager.retry('test-package')
        assert (await settle(manager))['state']=='installed'
        assert calls.count('weights.part0')==1
        assert (old/'old').read_bytes()==b'healthy'
        with manager.lease('test-package') as package:
            assert (package/'weights.safetensors').read_bytes()==b'abcdef'
            with pytest.raises(ModelManagerError, match='kullanım'):
                await manager.delete('test-package')
        await manager.delete('test-package');assert (await settle(manager))['state']=='absent'
        await manager.close()
    asyncio.run(check())


def test_start_never_loads_a_model_and_local_install_rejects_symlink(tmp_path):
    async def check():
        manager=PackageManager(tmp_path/'models',catalog=(definition(),),
                               prober=lambda *_:pytest.fail('startup must not probe'))
        await manager.start()
        source=tmp_path/'source';source.mkdir()
        (source/'weights.part0').write_bytes(b'abc');(source/'weights.part1').write_bytes(b'def')
        (source/'tokenizer').symlink_to(source, target_is_directory=True)
        (source/'config.json').write_bytes(b'cfg')
        await manager.install_local('test-package',source)
        assert (await settle(manager))['state']=='failed'
        assert manager.list_models()['models'][0]['error']['code']=='package_invalid'
        await manager.close()
    asyncio.run(check())


def test_cancel_keeps_only_verified_parts_and_releases_operation(tmp_path):
    async def check():
        entered=threading.Event()
        def download(part, destination, cancel, progress):
            if part.index == 1:
                entered.set();cancel.wait(3)
                raise InterruptedError()
            destination.write_bytes(b'abc')
        manager=PackageManager(tmp_path,catalog=(definition(),),downloader=download)
        await manager.start();await manager.install('test-package')
        assert await asyncio.to_thread(entered.wait,3)
        await manager.cancel('test-package')
        assert (await settle(manager))['state']=='cancelled'
        assert not list(tmp_path.rglob('*.partial'))
        assert not (tmp_path/'test-package'/('a'*40)).exists()
        await manager.close()
    asyncio.run(check())


def test_retry_accounts_for_verified_cached_parts_when_disk_is_tight(tmp_path,monkeypatch):
    from types import SimpleNamespace
    import pixelmend_engine.generative_packages as packages
    async def check():
        d=definition();calls=[]
        parent=tmp_path/d.manifest.model_id
        cache=parent/f'.{d.manifest.revision}.staging'/'parts';cache.mkdir(parents=True)
        (cache/sha(b'abc')).write_bytes(b'abc')
        # Remaining parts 6 + assembled files 9 + reserve, not full 18 again.
        monkeypatch.setattr(packages.shutil,'disk_usage',lambda _:SimpleNamespace(free=64*1024**2+15))
        def download(part,destination,*_):
            calls.append(part.local_path)
            destination.write_bytes({'weights.part1':b'def','tokenizer/config.json':b'cfg'}[part.local_path])
        manager=PackageManager(tmp_path,catalog=(d,),downloader=download)
        await manager.start();await manager.install('test-package')
        assert (await settle(manager))['state']=='installed'
        assert calls==['weights.part1','tokenizer/config.json']
        await manager.close()
    asyncio.run(check())
