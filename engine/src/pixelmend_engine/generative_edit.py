"""Source-resolution masked editing, independent of the unmasked image model."""
from dataclasses import dataclass, replace
import math

import cv2
import numpy as np
from PIL import Image

from .generative_process import RuntimeErrorCode
from .imageio import ImageAsset
from .strokes import StrokeValidationError, rasterize_selection, render_paint, validate_strokes


@dataclass(frozen=True,slots=True)
class EditPlan:
    working: ImageAsset
    mask: np.ndarray
    selection_box: tuple[int,int,int,int]
    crop_box: tuple[int,int,int,int]
    scaled_box: tuple[int,int,int,int]
    input_rgb: np.ndarray

    def model_prompt(self,english):
        sx0,sy0,sx1,sy1=self.selection_box
        cx0,cy0,cx1,cy1=self.crop_box
        left,top,width,height=self.scaled_box
        side=self.input_rgb.shape[0]
        x0=(left+(sx0-cx0)*width/(cx1-cx0))/side*100
        y0=(top+(sy0-cy0)*height/(cy1-cy0))/side*100
        x1=(left+(sx1-cx0)*width/(cx1-cx0))/side*100
        y1=(top+(sy1-cy0)*height/(cy1-cy0))/side*100
        return (f'{english}\nThe selected region spans x={x0:.1f}% to {x1:.1f}% and '
                f'y={y0:.1f}% to {y1:.1f}% of this image, measured from the top left. '
                'Place the requested change entirely within this region. Preserve the '
                'surrounding scene, other objects, camera perspective and lighting.')


def prepare_edit(source,selection_strokes,paint_strokes,profile):
    if profile not in {'low-resource','balanced'}:raise RuntimeErrorCode('output_invalid')
    try:
        validate_strokes(paint_strokes,source.width,source.height)
        mask=rasterize_selection(selection_strokes,source.width,source.height)
    except (StrokeValidationError,TypeError,ValueError):raise RuntimeErrorCode('selection_invalid') from None
    if source.alpha is not None:mask[source.alpha==0]=0
    # Reduce rows/columns instead of allocating a pair of int64 coordinates for
    # every selected pixel in a large source photograph.
    ys=np.flatnonzero(np.any(mask,axis=1));xs=np.flatnonzero(np.any(mask,axis=0))
    if not len(xs):raise RuntimeErrorCode('selection_empty')
    x0,y0,x1,y1=int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1
    margin_x=max(64,math.ceil((x1-x0)*.25));margin_y=max(64,math.ceil((y1-y0)*.25))
    cx0,cy0=max(0,x0-margin_x),max(0,y0-margin_y)
    cx1,cy1=min(source.width,x1+margin_x),min(source.height,y1+margin_y)
    crop_width,crop_height=cx1-cx0,cy1-cy0
    side=512 if profile=='low-resource' else 768
    factor=side/max(crop_width,crop_height)
    width,height=max(1,round(crop_width*factor)),max(1,round(crop_height*factor))
    if (x1-x0)*width/crop_width<32 or (y1-y0)*height/crop_height<32:
        raise RuntimeErrorCode('selection_too_small')
    rgb=render_paint(source.rgb,paint_strokes) if paint_strokes else source.rgb
    left,top=(side-width)//2,(side-height)//2
    crop=np.asarray(Image.fromarray(rgb[cy0:cy1,cx0:cx1]).resize((width,height),Image.Resampling.LANCZOS))
    padded=np.pad(crop,((top,side-height-top),(left,side-width-left),(0,0)),mode='reflect')
    working=replace(source,rgb=rgb)
    return EditPlan(working,mask,(x0,y0,x1,y1),(cx0,cy0,cx1,cy1),(left,top,width,height),padded)


def composite_edit(plan,generated_rgb):
    if (not isinstance(generated_rgb,np.ndarray) or generated_rgb.dtype!=np.uint8
            or generated_rgb.shape!=plan.input_rgb.shape):raise RuntimeErrorCode('output_invalid')
    left,top,width,height=plan.scaled_box
    cx0,cy0,cx1,cy1=plan.crop_box
    native=np.asarray(Image.fromarray(generated_rgb[top:top+height,left:left+width]).resize(
        (cx1-cx0,cy1-cy0),Image.Resampling.LANCZOS)).copy()
    mask=plan.mask[cy0:cy1,cx0:cx1]
    # Euclidean distance to unselected pixels. Weight is exactly zero outside;
    # the feather never expands the user mask and reaches full weight by pixel8.
    distance=cv2.distanceTransform((mask>0).astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    weight=np.minimum(distance/8,1)[:,:,None]
    base=plan.working.rgb[cy0:cy1,cx0:cx1]
    blended=np.rint(base.astype(np.float32)*(1-weight)+native.astype(np.float32)*weight).astype(np.uint8)
    rgb=plan.working.rgb.copy()
    rgb[cy0:cy1,cx0:cx1]=np.where(mask[:,:,None]>0,blended,base)
    # Alpha never participates in model inference/composition and is preserved verbatim.
    return replace(plan.working,rgb=rgb)
