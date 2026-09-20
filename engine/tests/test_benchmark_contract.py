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
