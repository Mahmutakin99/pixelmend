import importlib.util
from pathlib import Path
import zipfile
import pytest

spec=importlib.util.spec_from_file_location('backup',Path(__file__).parents[2]/'tools/generative/development-backup.py')
backup=importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)

def test_archive_manifest_deduplicates_and_verifies_restore(tmp_path):
    a=tmp_path/'a';a.write_bytes(b'model')
    b=tmp_path/'b';b.write_bytes(b'model')
    output=tmp_path/'backup.zip'
    report=backup.archive([(a,'models/a'),(b,'originals/b')],output,reserve_bytes=0)
    assert report['files']==2 and report['unique_files']==1
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        assert z.read('models/a')==b'model'
        assert 'originals/b' not in z.namelist()
    restored=tmp_path/'restored'
    backup.restore(output,restored)
    assert (restored/'originals/b').read_bytes()==b'model'
    (restored/'models/a').write_bytes(b'bad')
    with pytest.raises(ValueError,match='hash'):
        backup.verify_restored(output,restored)

def test_rejects_unsafe_archive_paths_and_preserves_existing_output(tmp_path):
    a=tmp_path/'a';a.write_bytes(b'a');out=tmp_path/'b.zip'
    with pytest.raises(ValueError):backup.archive([(a,'../outside')],out,reserve_bytes=0)
    out.write_bytes(b'keep')
    with pytest.raises(FileExistsError):backup.archive([(a,'a')],out,reserve_bytes=0)
    assert out.read_bytes()==b'keep'

def test_uses_measured_compressed_size_when_uncompressed_archive_wont_fit(tmp_path,monkeypatch):
    from types import SimpleNamespace
    source=tmp_path/'weights';source.write_bytes(bytes(1024**2))
    monkeypatch.setattr(backup.shutil,'disk_usage',lambda _:SimpleNamespace(free=128*1024))
    report=backup.archive([(source,'weights')],tmp_path/'b.zip',reserve_bytes=0)
    assert report['archive_bytes']<128*1024

def test_stored_zip_never_uses_a_compressed_size_for_disk_admission(tmp_path,monkeypatch):
    from types import SimpleNamespace
    source=tmp_path/'weights';source.write_bytes(bytes(1024**2))
    monkeypatch.setattr(backup.shutil,'disk_usage',lambda _:SimpleNamespace(free=128*1024))
    with pytest.raises(OSError):backup.archive([(source,'weights')],tmp_path/'b.zip',reserve_bytes=0,compression=zipfile.ZIP_STORED)
    assert not (tmp_path/'b.zip').exists()
