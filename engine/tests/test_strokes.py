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


def test_strokes_at_the_final_addressable_pixel_are_accepted():
    image = np.zeros((16, 16, 3), dtype=np.uint8)
    painted = render_paint(image, [stroke(points=[{'x': 15, 'y': 15}])])
    assert painted[15, 15].tolist() == [255, 0, 0]


@pytest.mark.parametrize('bad', [
    {'mode': 'draw', 'points': [{'x': float('nan'), 'y': 1}], 'color': '#fff', 'opacity': 1, 'size': 1, 'hardness': 1},
    {'mode': 'draw', 'points': [{'x': 99, 'y': 1}], 'color': '#fff', 'opacity': 1, 'size': 1, 'hardness': 1},
    {'mode': 'draw', 'points': [{'x': 1, 'y': 1}], 'color': 'red', 'opacity': 1, 'size': 1, 'hardness': 1},
])
def test_strokes_reject_untrusted_coordinates_and_style(bad):
    with pytest.raises(StrokeValidationError):
        rasterize_selection([bad], 16, 16)


def test_translucent_strokes_use_canvas_source_over():
    image=np.full((16,16,3),255,np.uint8)
    painted=render_paint(image,[stroke(color='#ff0000',opacity=.5),stroke(color='#0000ff',opacity=.5)])
    assert np.max(np.abs(painted[8,8].astype(int)-[128,64,191])) <= 1


def test_each_segment_accumulates_opacity_like_canvas_live_and_replay():
    image=np.full((16,16,3),255,np.uint8)
    painted=render_paint(image,[stroke(opacity=.5,points=[{'x':4,'y':8},{'x':12,'y':8},{'x':4,'y':8}])])
    assert np.max(np.abs(painted[8,8].astype(int)-[255,64,64])) <= 1


def test_zero_length_segment_does_not_add_opacity():
    image=np.full((16,16,3),255,np.uint8)
    a=render_paint(image,[stroke(opacity=.5)])
    b=render_paint(image,[stroke(opacity=.5,points=[{'x':8,'y':8},{'x':8,'y':8}])])
    np.testing.assert_array_equal(a,b)


def test_long_diagonal_uses_bounded_supersampling_tiles(monkeypatch):
    from PIL import Image
    import pixelmend_engine.strokes as module
    original=Image.new
    def guarded(mode,size,*args,**kwargs):
        if mode=='L':assert max(size)<=1024, 'unbounded supersampled coverage'
        return original(mode,size,*args,**kwargs)
    monkeypatch.setattr(Image,'new',guarded)
    layer=original('RGBA',(900,900),(0,0,0,0))
    commands=module.validate_strokes([stroke(points=[{'x':0,'y':0},{'x':899,'y':899}])],900,900)
    module._draw(layer,commands)
    assert layer.getpixel((450,450))[3]==255


def test_continuation_chunk_does_not_add_an_extra_dab():
    image=np.full((16,16,3),255,np.uint8)
    points=[{'x':4,'y':8},{'x':8,'y':8},{'x':12,'y':8}]
    whole=render_paint(image,[stroke(points=points,opacity=.5)])
    tail=stroke(points=points[1:],opacity=.5);tail['continuation']=True
    chunks=render_paint(image,[stroke(points=points[:2],opacity=.5),tail])
    np.testing.assert_array_equal(whole,chunks)
