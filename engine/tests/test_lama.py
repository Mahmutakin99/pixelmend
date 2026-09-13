import os

import numpy as np
import pytest


def test_lama_letterbox_keeps_roi_aspect_and_mask_binary():
    from pixelmend_engine.models.lama_onnx import prepare_roi

    image = np.zeros((100, 900, 3), dtype=np.uint8)
    mask = np.zeros((100, 900), dtype=np.uint8)
    mask[40:60, 400:500] = 255
    data, selection, geometry = prepare_roi(image, mask)
    assert data.shape == (1, 3, 512, 512)
    assert selection.shape == (1, 1, 512, 512)
    assert set(np.unique(selection)) <= {0, 1}
    x0, y0, x1, y1, width, height = geometry
    assert abs(width / height - (x1-x0) / (y1-y0)) < .02


@pytest.mark.skipif(os.environ.get('PIXELMEND_REAL_MODELS') != '1', reason='explicit model smoke')
def test_real_lama_preserves_unmasked_pixels():
    from pixelmend_engine.models.lama_onnx import LamaInpaint
    from pixelmend_engine.paths import get_models_dir

    image = np.full((64, 96, 3), 160, dtype=np.uint8)
    image[28:36, 42:50] = 0
    mask = np.zeros((64, 96), dtype=np.uint8)
    mask[28:36, 42:50] = 255
    result = LamaInpaint(get_models_dir()).run(image, mask)
    np.testing.assert_array_equal(result[mask == 0], image[mask == 0])
    assert result[mask == 255].mean() > 30
