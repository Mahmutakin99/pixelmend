from dataclasses import replace
import numpy as np
import pytest

from pixelmend_engine.generative_edit import prepare_edit, composite_edit
from pixelmend_engine.generative_process import RuntimeErrorCode
from pixelmend_engine.imageio import ImageAsset
from pixelmend_engine.strokes import rasterize_selection,render_paint


def stroke(x,y,size=100,mode='draw'):
    return {'mode':mode,'points':[{'x':x,'y':y}],'size':size,'opacity':1,'color':'#ff0000','hardness':1}


def image(width=900,height=600,alpha=None):
    rng=np.random.default_rng(42)
    return ImageAsset(rng.integers(0,256,(height,width,3),dtype=np.uint8),alpha,None,())


def test_source_mask_crop_context_aspect_padding_and_strict_pixel_preservation():
    source=image();selected=[stroke(450,300,180)];paint=[stroke(20,20,30)]
    before=source.rgb.copy();plan=prepare_edit(source,selected,paint,'low-resource')
    assert plan.input_rgb.shape==(512,512,3)
    assert plan.crop_box==(296,146,605,455) # 181² binary selection plus64 each direction.
    # Each context side is >=64 or 25% of bounding box unless clipped at source edge.
    x0,y0,x1,y1=plan.selection_box;cx0,cy0,cx1,cy1=plan.crop_box
    assert x0-cx0>=64 and y0-cy0>=64 and cx1-x1>=64 and cy1-y1>=64
    result=composite_edit(plan,np.full((512,512,3),127,np.uint8))
    working=render_paint(source.rgb,paint)
    np.testing.assert_array_equal(result.rgb[plan.mask==0],working[plan.mask==0])
    assert np.any(result.rgb[plan.mask>0]!=working[plan.mask>0])
    np.testing.assert_array_equal(source.rgb,before)
    assert result.rgb.shape==source.rgb.shape


def test_alpha_is_preserved_and_fully_transparent_pixels_are_not_edited():
    alpha=np.full((400,600),127,np.uint8);alpha[100:220,150:260]=0
    source=image(600,400,alpha);plan=prepare_edit(source,[stroke(250,200,200)],[],'low-resource')
    result=composite_edit(plan,np.full((512,512,3),255,np.uint8))
    np.testing.assert_array_equal(result.alpha,alpha)
    np.testing.assert_array_equal(result.rgb[alpha==0],source.rgb[alpha==0])
    np.testing.assert_array_equal(result.rgb[plan.mask==0],source.rgb[plan.mask==0])


@pytest.mark.parametrize('selected',[[],[stroke(200,200,150),stroke(200,200,200,'erase')],[stroke(200,200,1)]])
def test_empty_erased_or_too_small_selection_is_rejected(selected):
    with pytest.raises(RuntimeErrorCode) as error:prepare_edit(image(400,400),selected,[],'low-resource')
    assert error.value.code in {'selection_empty','selection_too_small'}


def test_transparent_only_selection_is_rejected():
    with pytest.raises(RuntimeErrorCode) as error:
        prepare_edit(image(400,400,np.zeros((400,400),np.uint8)),[stroke(200,200,100)],[],'low-resource')
    assert error.value.code=='selection_empty'


def test_edge_selection_reflected_padding_and_large_source_restore_dimensions():
    source=image(2000,400)
    plan=prepare_edit(source,[stroke(0,180,160)],[],'low-resource')
    assert plan.crop_box[0]==0
    assert plan.input_rgb.shape==(512,512,3)
    xpad,ypad,scaled_width,scaled_height=plan.scaled_box
    assert scaled_width!=scaled_height
    result=composite_edit(plan,plan.input_rgb)
    assert (result.width,result.height)==(2000,400)
    np.testing.assert_array_equal(result.rgb[plan.mask==0],source.rgb[plan.mask==0])
    assert 'selected' in plan.model_prompt('Add a cat.').lower()


def test_feather_is_only_inward_and_no_wider_than_eight_source_pixels():
    source=replace(image(400,400),rgb=np.zeros((400,400,3),np.uint8))
    plan=prepare_edit(source,[stroke(200,200,160)],[],'low-resource')
    result=composite_edit(plan,np.full((512,512,3),255,np.uint8))
    assert result.rgb[200,200].tolist()==[255,255,255]
    # Left edge of the binary circle is x120. Eighth inner pixel is fully generated.
    assert 0<result.rgb[200,120,0]<255
    assert result.rgb[200,127,0]==255
    assert result.rgb[200,119,0]==0
    np.testing.assert_array_equal(result.rgb[plan.mask==0],source.rgb[plan.mask==0])


def test_output_shape_and_invalid_selection_coordinates_are_rejected():
    plan=prepare_edit(image(400,400),[stroke(200,200,100)],[],'balanced')
    with pytest.raises(RuntimeErrorCode):composite_edit(plan,np.zeros((512,512,3),np.uint8))
    with pytest.raises(RuntimeErrorCode):prepare_edit(image(400,400),[stroke(float('nan'),200)],[],'low-resource')
