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

def test_kernel_lifetime_peak_is_preferred_and_old_counter_falls_back():
    from pixelmend_engine.process_memory import RUsageV4
    assert ctypes.sizeof(RUsageV4)==296
    assert RUsageV4.ri_lifetime_max_phys_footprint.offset==240
    def peak(_pid,flavor,pointer):
        assert flavor==4
        record=ctypes.cast(pointer,ctypes.POINTER(RUsageV4)).contents
        record.ri_phys_footprint=100;record.ri_lifetime_max_phys_footprint=200
        return 0
    assert MacFootprint(platform_name='darwin',query=peak).read(1)==200
    def old(_pid,flavor,pointer):
        if flavor==4:return -1
        ctypes.cast(pointer,ctypes.POINTER(RUsageV2)).contents.ri_phys_footprint=100
        return 0
    assert MacFootprint(platform_name='darwin',query=old).read(1)==100
