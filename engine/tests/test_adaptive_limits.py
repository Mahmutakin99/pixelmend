from types import SimpleNamespace

import pytest

from pixelmend_engine.policy import adaptive_output_limit, admit_image_job, ResourceLimitError


def test_adaptive_limit_stays_under_hard_ceiling_and_accounts_for_ai_workspace():
    image = SimpleNamespace(width=4000, height=3000, alpha=None)
    standard = adaptive_output_limit(image, ai=False, available_bytes=8 * 1024**3,
                                     disk_free_bytes=8 * 1024**3)
    ai = adaptive_output_limit(image, ai=True, available_bytes=8 * 1024**3,
                               disk_free_bytes=8 * 1024**3)
    assert 0 < ai <= standard <= 200_000_000


def test_adaptive_limit_drops_when_live_resources_are_low():
    image = SimpleNamespace(width=1000, height=1000, alpha=None)
    ample = adaptive_output_limit(image, ai=True, available_bytes=8 * 1024**3,
                                  disk_free_bytes=8 * 1024**3)
    constrained = adaptive_output_limit(image, ai=True, available_bytes=900 * 1024**2,
                                        disk_free_bytes=900 * 1024**2)
    assert 0 < constrained < ample


def test_admission_rejects_targets_above_the_current_adaptive_limit():
    image = SimpleNamespace(width=1000, height=1000, alpha=None)
    with pytest.raises(ResourceLimitError) as caught:
        admit_image_job(image, (6500, 6500), ai=True,
                        available_bytes=2 * 1024**3, disk_free_bytes=8 * 1024**3)
    assert caught.value.code == 'adaptive_limit'


def test_ai_disk_admission_uses_source_workspace_not_final_output_pixels():
    image = SimpleNamespace(width=1000, height=1000, alpha=None)
    limit = adaptive_output_limit(image, ai=True, available_bytes=16 * 1024**3,
                                  disk_free_bytes=1024**3)
    assert limit == 200_000_000
