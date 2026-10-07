"""Validate untrusted vector strokes and render them only at native asset size."""

import math
import re

import numpy as np
from PIL import Image, ImageDraw

MAX_STROKES = 2_048
MAX_POINTS_PER_STROKE = 8_192
MAX_POINTS = 250_000
_COLOR = re.compile(r'^#[0-9a-fA-F]{6}$')


class StrokeValidationError(ValueError):
    """A renderer-supplied stroke does not satisfy the authenticated contract."""


def validate_strokes(strokes, width: int, height: int) -> list[dict]:
    """Copy only finite, bounded brush commands; ids and paths never cross this API."""
    if not isinstance(strokes, list) or len(strokes) > MAX_STROKES:
        raise StrokeValidationError('invalid stroke count')
    copied, total = [], 0
    for stroke in strokes:
        if not isinstance(stroke, dict) or stroke.get('mode') not in {'draw', 'erase'}:
            raise StrokeValidationError('invalid stroke mode')
        points = stroke.get('points')
        if not isinstance(points, list) or not points or len(points) > MAX_POINTS_PER_STROKE:
            raise StrokeValidationError('invalid stroke points')
        color, opacity, size = stroke.get('color'), stroke.get('opacity'), stroke.get('size')
        if not isinstance(color, str) or not _COLOR.fullmatch(color):
            raise StrokeValidationError('invalid stroke color')
        if (not isinstance(opacity, (int, float)) or not math.isfinite(opacity)
                or opacity <= 0 or opacity > 1 or not isinstance(size, (int, float))
                or not math.isfinite(size) or size <= 0):
            raise StrokeValidationError('invalid stroke style')
        continuation=stroke.get('continuation',False)
        if not isinstance(continuation,bool):raise StrokeValidationError('invalid stroke continuation')
        normalized = []
        for point in points:
            if not isinstance(point, dict):
                raise StrokeValidationError('invalid stroke point')
            x, y = point.get('x'), point.get('y')
            if (not isinstance(x, (int, float)) or not isinstance(y, (int, float))
                    or not math.isfinite(x) or not math.isfinite(y) or x < 0 or y < 0
                    or x >= width or y >= height):
                raise StrokeValidationError('stroke point is outside image bounds')
            normalized.append((float(x), float(y)))
        total += len(normalized)
        if total > MAX_POINTS:
            raise StrokeValidationError('too many stroke points')
        copied.append({'mode': stroke['mode'], 'points': normalized, 'color': color,
                       'opacity': float(opacity), 'size': float(size), 'continuation':continuation})
    return copied


def _intersects_tile(a,b,box,radius):
    """Conservative segment/expanded-rectangle test; avoids empty diagonal tiles."""
    low,high=0.,1.
    for start,end,left,right in ((a[0],b[0],box[0]-radius-1,box[2]+radius+1),
                                (a[1],b[1],box[1]-radius-1,box[3]+radius+1)):
        delta=end-start
        if delta==0:
            if not left<=start<=right:return False
        else:
            near,far=sorted(((left-start)/delta,(right-start)/delta))
            low=max(low,near);high=min(high,far)
            if low>high:return False
    return True


def _draw(layer: Image.Image, strokes: list[dict]) -> None:
    """Canvas dab/segment order, with bounded antialiased coverage tiles."""
    for stroke in strokes:
        points, radius = stroke['points'], stroke['size'] / 2
        rgb = tuple(bytes.fromhex(stroke['color'][1:]))
        primitives=[] if stroke.get('continuation') else [(points[0],points[0])]
        primitives.extend((a,b) for a,b in zip(points,points[1:]) if a != b)
        for a,b in primitives:
            left=max(0,math.floor(min(a[0],b[0])-radius-1)); top=max(0,math.floor(min(a[1],b[1])-radius-1))
            right=min(layer.width,math.ceil(max(a[0],b[0])+radius+1)); bottom=min(layer.height,math.ceil(max(a[1],b[1])+radius+1))
            for y0 in range(top,bottom,256):
                for x0 in range(left,right,256):
                    x1=min(right,x0+256);y1=min(bottom,y0+256);box=(x0,y0,x1,y1)
                    if not _intersects_tile(a,b,box,radius):continue
                    factor=4;size=(x1-x0,y1-y0)
                    full=any(all(math.hypot(x-point[0],y-point[1])<=radius for x,y in ((x0,y0),(x1,y0),(x0,y1),(x1,y1))) for point in (a,b))
                    if full:coverage=Image.new('L',size,255)
                    else:
                        coverage=Image.new('L',(size[0]*factor,size[1]*factor),0)
                        draw=ImageDraw.Draw(coverage)
                        ends=[((x-x0)*factor,(y-y0)*factor) for x,y in (a,b)];r=radius*factor
                        if a!=b:draw.line(ends,fill=255,width=max(1,round(stroke['size']*factor)))
                        for x,y in ends[:1] if a==b else ends:draw.ellipse((x-r,y-r,x+r,y+r),fill=255)
                        coverage=coverage.resize(size,Image.Resampling.BOX)
                    patch=layer.crop(box)
                    if stroke['mode']=='erase':
                        alpha=np.asarray(patch.getchannel('A')).astype(np.uint16)
                        remain=255-np.asarray(coverage).astype(np.uint16)
                        patch.putalpha(Image.fromarray(((alpha*remain+127)//255).astype(np.uint8)))
                    else:
                        alpha=np.rint(np.asarray(coverage)*stroke['opacity']).astype(np.uint8)
                        overlay=Image.new('RGBA',size,(*rgb,0));overlay.putalpha(Image.fromarray(alpha))
                        patch=Image.alpha_composite(patch,overlay)
                    layer.paste(patch,box)


def rasterize_selection(strokes, width: int, height: int) -> np.ndarray:
    """Build the canonical native uint8 0/255 inpaint mask from vector selection strokes."""
    layer = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(layer)
    for stroke in validate_strokes(strokes, width, height):
        points, radius = stroke['points'], stroke['size'] / 2
        fill = 0 if stroke['mode'] == 'erase' else 255
        if len(points) > 1:
            draw.line(points, fill=fill, width=max(1, round(stroke['size'])), joint='curve')
        for x, y in (points[0], points[-1]):
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill)
    return np.where(np.asarray(layer) >= 128, 255, 0).astype(np.uint8)


def render_paint(rgb: np.ndarray, strokes) -> np.ndarray:
    """Composite validated paint commands at source resolution and return RGB pixels."""
    height, width = rgb.shape[:2]
    layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    _draw(layer, validate_strokes(strokes, width, height))
    output = rgb.copy()
    for top in range(0,height,256):
        bottom=min(height,top+256)
        base=Image.fromarray(rgb[top:bottom]).convert('RGBA')
        output[top:bottom]=np.asarray(Image.alpha_composite(base,layer.crop((0,top,width,bottom))).convert('RGB'))
    return output
