import numpy as np

from pixelmend_engine.models.sdxl_worker import composite_selected, context_box


def test_sdxl_composite_never_changes_pixels_outside_the_selection():
    source = np.arange(4 * 5 * 3, dtype=np.uint8).reshape(4, 5, 3)
    candidate = np.full_like(source, 255)
    mask = np.zeros((4, 5), dtype=np.uint8)
    mask[1:3, 2:4] = 255

    result = composite_selected(source, candidate, mask)

    np.testing.assert_array_equal(result[mask == 0], source[mask == 0])
    np.testing.assert_array_equal(result[mask == 255], candidate[mask == 255])


def test_sdxl_context_is_bounded_and_contains_edge_selection():
    mask = np.zeros((900, 1600), dtype=np.uint8)
    mask[820:900, 0:120] = 255

    x0, y0, x1, y1 = context_box(mask, maximum=512)

    assert 0 <= x0 < x1 <= 1600 and 0 <= y0 < y1 <= 900
    assert x1 - x0 <= 512 and y1 - y0 <= 512
    assert x0 == 0 and y1 == 900
