from types import SimpleNamespace

import pytest

from pixelmend_engine.policy import ResourcePolicy, ResourceLimitError, admit_image_job, inference_settings, validate_dimensions


def test_200_mp_and_operator_override_dimensions():
    validate_dimensions(16000, 12000)
    with pytest.raises(ResourceLimitError):
        validate_dimensions(20001, 10000)
    with pytest.raises(ResourceLimitError):
        validate_dimensions(True, 10)
    validate_dimensions(25000, 10000, policy=ResourcePolicy(max_output_pixels=300_000_000))


def test_admission_checks_natural_output_ram_disk_and_existing_results():
    image = SimpleNamespace(width=4000, height=3000, alpha=None)
    args = dict(ai=True, available_bytes=8 * 1024**3, disk_free_bytes=5 * 1024**3)
    admit_image_job(image, (16000, 12000), **args)
    for changes, code in [({'available_bytes': 1024**3}, 'memory_limit'),
                           ({'disk_free_bytes': 1024**3}, 'disk_full'),
                           ({'result_bytes': 600_000_000}, 'result_budget')]:
        with pytest.raises(ResourceLimitError) as caught:
            admit_image_job(image, (16000, 12000), **(args | changes))
        assert caught.value.code == code
    image.width = 8000
    with pytest.raises(ResourceLimitError) as caught:
        admit_image_job(image, (100, 100), **args)
    assert caught.value.code == 'intermediate_limit'


def test_ai_admission_uses_real_default_temporary_directory():
    image = SimpleNamespace(width=16, height=16, alpha=None)
    admit_image_job(image, (32, 32), ai=True, available_bytes=8 * 1024**3)


def test_low_resource_mode_has_a_real_bounded_tile_and_cpu_effect():
    assert inference_settings('automatic') == {'tile_size': 128, 'tile_overlap': 16, 'intra_op_threads': 4}
    assert inference_settings('low-resource') == {'tile_size': 64, 'tile_overlap': 8, 'intra_op_threads': 2}
    with pytest.raises(ValueError):
        inference_settings('turbo')
