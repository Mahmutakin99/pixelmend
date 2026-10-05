import importlib.util,json,hashlib
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('release',Path(__file__).parents[2]/'tools/generative/model-release.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)

def fixture(tmp_path):
    source=tmp_path/'source'/'tiny';source.mkdir(parents=True);(source/'weights').write_bytes(b'model')
    sha=hashlib.sha256(b'model').hexdigest()
    catalog={'packages':[{'id':'tiny','parts':[{'local_path':'weights','size_bytes':5,'sha256':sha,'url':None}]}]}
    return source.parent,catalog,sha

def test_prepares_verified_assets_without_changing_local_install_paths(tmp_path):
    source,catalog,sha=fixture(tmp_path)
    report=release.prepare(source,catalog,tmp_path/'assets','models-test')
    assert (tmp_path/'assets'/sha).read_bytes()==b'model'
    part=report['catalog']['packages'][0]['parts'][0]
    assert part['local_path']=='weights'
    assert part['url']==f'https://github.com/Mahmutakin99/pixelmend-models/releases/download/models-test/{sha}'
    release.verify_remote(report,[{'name':sha,'size':5,'digest':'sha256:'+sha}])
    with pytest.raises(ValueError,match='remote'):
        release.verify_remote(report,[{'name':sha,'size':5,'digest':'sha256:'+'a'*64}])

def test_corrupt_sources_are_rejected_before_release(tmp_path):
    source,catalog,_=fixture(tmp_path);(source/'tiny/weights').write_bytes(b'wrong')
    with pytest.raises(ValueError,match='hash'):release.prepare(source,catalog,tmp_path/'assets','models-test')
