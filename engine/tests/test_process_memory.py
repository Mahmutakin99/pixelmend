import ctypes
import os
import sys

import pytest

from pixelmend_engine.process_memory import RUsageV2,MacFootprint


def test_kernel_structure_layout_matches_stable_darwin_v2_contract():
    assert ctypes.sizeof(RUsageV2)==160
    assert RUsageV2.ri_phys_footprint.offset==72


def test_unsupported_host_and_failed_kernel_query_stay_unknown():
    assert MacFootprint(platform_name='linux').read(os.getpid()) is None
    sampler=MacFootprint(platform_name='darwin',query=lambda *_:-1)
    assert sampler.read(os.getpid()) is None


@pytest.mark.skipif(sys.platform!='darwin',reason='actual Darwin counter')
def test_actual_kernel_process_footprint_is_positive_when_available():
    value=MacFootprint().read(os.getpid())
    # Sandboxed access may be denied; an unavailable metric must not be invented.
    assert value is None or value>0
