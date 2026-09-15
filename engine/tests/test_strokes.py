import numpy as np
import pytest

from pixelmend_engine.strokes import StrokeValidationError, rasterize_selection, render_paint


def stroke(*, mode='draw', points=None, color='#ff0000', opacity=1, size=4):
    return {'mode': mode, 'points': points or [{'x': 8, 'y': 8}], 'color': color,
            'opacity': opacity, 'size': size, 'hardness': 1}


def test_selection_strokes_become_native_binary_mask():
    mask = rasterize_selection([stroke()], 16, 16)
    assert mask.dtype == np.uint8
    assert mask[8, 8] == 255
    assert set(np.unique(mask)) <= {0, 255}


def test_paint_strokes_compose_at_native_coordinates_and_erase():
    image = np.zeros((16, 16, 3), dtype=np.uint8)
    painted = render_paint(image, [stroke(points=[{'x': 8, 'y': 8}], color='#ff8040')])
    erased = render_paint(image, [stroke(points=[{'x': 8, 'y': 8}], color='#ff8040'), stroke(mode='erase')])
    assert painted[8, 8].tolist() == [255, 128, 64]
    assert erased[8, 8].tolist() == [0, 0, 0]


@pytest.mark.parametrize('bad', [
    {'mode': 'draw', 'points': [{'x': float('nan'), 'y': 1}], 'color': '#fff', 'opacity': 1, 'size': 1, 'hardness': 1},
    {'mode': 'draw', 'points': [{'x': 99, 'y': 1}], 'color': '#fff', 'opacity': 1, 'size': 1, 'hardness': 1},
    {'mode': 'draw', 'points': [{'x': 1, 'y': 1}], 'color': 'red', 'opacity': 1, 'size': 1, 'hardness': 1},
])
def test_strokes_reject_untrusted_coordinates_and_style(bad):
    with pytest.raises(StrokeValidationError):
        rasterize_selection([bad], 16, 16)
