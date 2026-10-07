import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('bench', Path(__file__).parents[1] / 'bench/run_upscale.py')
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


def test_acceptance_requires_twelve_distinct_photographs():
    with pytest.raises(ValueError, match='12'):
        bench.validate_fixture_set([{'id':'only-one'}])
    with pytest.raises(ValueError, match='distinct'):
        bench.validate_fixture_set([{'id':'same'}] * 12)


def test_upscale_repeats_release_every_prior_pixel_output(monkeypatch):
    import importlib.util,weakref
    import numpy as np
    module_path=Path(__file__).resolve().parents[1]/'bench'/'run_upscale.py'
    spec=importlib.util.spec_from_file_location('upscale_bench',module_path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    refs=[]
    def measure(*args):
        assert all(ref() is None for ref in refs)
        output=np.zeros((8,8,3),np.uint8);refs.append(weakref.ref(output));return output,1.0,100
    monkeypatch.setattr(module,'measure',measure)
    result,stats=module.benchmark_runs(None,None,None,3)
    assert len(refs)==4 and sum(ref() is not None for ref in refs)==1
    assert stats['warm_seconds']==[1.,1.,1.] and result.shape==(8,8,3)
