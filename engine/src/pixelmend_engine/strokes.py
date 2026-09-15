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
                       'opacity': float(opacity), 'size': float(size)})
    return copied


def _draw(layer: Image.Image, strokes: list[dict]) -> None:
    """Apply round-capped strokes on an overlay so erasing never changes source pixels."""
    for stroke in strokes:
        points, radius = stroke['points'], stroke['size'] / 2
        if stroke['mode'] == 'erase':
            # Pillow does not implement destination-out for ImageDraw. Draw a
            # native-size mask then clear only the editable overlay's alpha.
            erase = Image.new('L', layer.size, 0)
            draw = ImageDraw.Draw(erase)
            fill = 255
        else:
            draw = ImageDraw.Draw(layer)
            rgb = tuple(bytes.fromhex(stroke['color'][1:]))
            fill = (*rgb, round(255 * stroke['opacity']))
        # ImageDraw's RGBA mode overwrites pixels, matching an editable paint layer.
        if len(points) > 1:
            draw.line(points, fill=fill, width=max(1, round(stroke['size'])), joint='curve')
        for x, y in (points[0], points[-1]):
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill)
        if stroke['mode'] == 'erase':
            alpha = np.asarray(layer.getchannel('A')).copy()
            alpha[np.asarray(erase) > 0] = 0
            layer.putalpha(Image.fromarray(alpha))


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
    base = Image.fromarray(rgb, 'RGB').convert('RGBA')
    return np.asarray(Image.alpha_composite(base, layer).convert('RGB')).copy()
