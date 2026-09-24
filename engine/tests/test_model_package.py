import hashlib
from pathlib import Path
from threading import Event

import pytest

from pixelmend_engine.model_package import (
    ModelPackageFile,
    ModelPackageManifest,
    PackageHashMismatchError,
    PackageMissingFileError,
    install_package,
    verify_package,
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def package_manifest():
    return ModelPackageManifest(
        model_id='fixture-package', revision='a' * 40, license_id='test-license',
        license_url='https://example.test/license', files=(
            ModelPackageFile('unet/weights.bin', 3, digest(b'one')),
            ModelPackageFile('tokenizer/config.json', 3, digest(b'two')),
        ),
    )


def test_package_verification_requires_every_pinned_regular_file(tmp_path):
    manifest = package_manifest()
    root = tmp_path / manifest.model_id / manifest.revision
    (root / 'unet').mkdir(parents=True)
    (root / 'unet' / 'weights.bin').write_bytes(b'one')

    with pytest.raises(PackageMissingFileError, match='tokenizer/config.json'):
        verify_package(root, manifest)

    (root / 'tokenizer').mkdir()
    (root / 'tokenizer' / 'config.json').write_bytes(b'bad')
    with pytest.raises(PackageHashMismatchError, match='tokenizer/config.json'):
        verify_package(root, manifest)


def test_package_install_never_exposes_a_partial_revision(tmp_path):
    manifest = package_manifest()
    downloaded = []

    def downloader(file, destination, cancel, progress):
        downloaded.append(file.path)
        if file.path == 'tokenizer/config.json':
            raise RuntimeError('transport interrupted')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b'one')

    with pytest.raises(RuntimeError, match='transport interrupted'):
        install_package(tmp_path, manifest, downloader)

    target = tmp_path / manifest.model_id / manifest.revision
    assert not target.exists()
    assert downloaded == ['unet/weights.bin', 'tokenizer/config.json']


def test_package_install_is_atomic_and_reuses_a_verified_restart_cache(tmp_path):
    manifest = package_manifest()
    payloads = {'unet/weights.bin': b'one', 'tokenizer/config.json': b'two'}
    calls = []

    def downloader(file, destination, cancel, progress):
        calls.append(file.path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payloads[file.path])
        progress(len(payloads[file.path]))

    installed = install_package(tmp_path, manifest, downloader)
    assert verify_package(installed, manifest) == installed
    assert calls == ['unet/weights.bin', 'tokenizer/config.json']

    reused = install_package(tmp_path, manifest, lambda *_: pytest.fail('must not download'))
    assert reused == installed


def test_cancelled_package_install_leaves_no_ready_revision_and_can_retry(tmp_path):
    manifest = package_manifest()
    stopped = Event()
    payloads = {'unet/weights.bin': b'one', 'tokenizer/config.json': b'two'}

    def interrupted(file, destination, cancel, progress):
        destination.write_bytes(payloads[file.path])
        stopped.set()

    with pytest.raises(InterruptedError, match='cancelled'):
        install_package(tmp_path, manifest, interrupted, cancel=stopped)

    target = tmp_path / manifest.model_id / manifest.revision
    assert not target.exists()

    def retry(file, destination, cancel, progress):
        destination.write_bytes(payloads[file.path])

    installed = install_package(tmp_path, manifest, retry)
    assert verify_package(installed, manifest) == target


def test_corrupt_revision_is_replaced_only_after_complete_verification(tmp_path):
    manifest = package_manifest()
    target = tmp_path / manifest.model_id / manifest.revision
    (target / 'unet').mkdir(parents=True)
    (target / 'unet' / 'weights.bin').write_bytes(b'bad')
    (target / 'tokenizer').mkdir()
    (target / 'tokenizer' / 'config.json').write_bytes(b'two')

    def failed_repair(file, destination, cancel, progress):
        assert (target / 'unet' / 'weights.bin').read_bytes() == b'bad'
        raise RuntimeError('network failure')

    with pytest.raises(RuntimeError, match='network failure'):
        install_package(tmp_path, manifest, failed_repair)
    assert (target / 'unet' / 'weights.bin').read_bytes() == b'bad'

    def repair(file, destination, cancel, progress):
        destination.write_bytes(b'one' if file.path.startswith('unet/') else b'two')

    assert install_package(tmp_path, manifest, repair) == target
    assert verify_package(target, manifest) == target
    assert not list(target.parent.glob(f'.{manifest.revision}.invalid-*'))


@pytest.mark.parametrize('path', ['../weights.bin', '/weights.bin', 'unet/../../weights.bin', ''])
def test_package_manifest_rejects_unsafe_member_paths(path):
    with pytest.raises(ValueError):
        ModelPackageManifest(
            model_id='fixture-package', revision='a' * 40, license_id='test-license',
            license_url='https://example.test/license',
            files=(ModelPackageFile(path, 1, digest(b'x')),),
        )


def test_package_verification_rejects_a_symlinked_member_directory(tmp_path):
    manifest = package_manifest()
    root = tmp_path / manifest.model_id / manifest.revision
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'weights.bin').write_bytes(b'one')
    root.mkdir(parents=True)
    (root / 'unet').symlink_to(outside, target_is_directory=True)
    (root / 'tokenizer').mkdir()
    (root / 'tokenizer' / 'config.json').write_bytes(b'two')

    with pytest.raises(PackageMissingFileError, match='unet/weights.bin'):
        verify_package(root, manifest)
