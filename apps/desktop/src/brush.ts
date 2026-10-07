import type { Point, Stroke } from './document';

type Layer = 'paint' | 'selection';

export function previewBrush(stroke:Stroke,scale:number):Stroke {
  return {...stroke,size:stroke.size*scale};
}

function configure(context: CanvasRenderingContext2D, stroke: Stroke, layer: Layer) {
  context.globalCompositeOperation = stroke.mode === 'erase' ? 'destination-out' : 'source-over';
  context.globalAlpha = stroke.mode === 'erase' || layer === 'selection' ? 1 : stroke.opacity;
  context.fillStyle = stroke.color;
  context.strokeStyle = stroke.color;
  context.lineWidth = stroke.size;
  context.lineCap = 'round';
  context.lineJoin = 'round';
}

export function drawStrokeStart(context: CanvasRenderingContext2D, stroke: Stroke, layer: Layer) {
  const point = stroke.points[0];
  if (!point) return;
  context.save();
  configure(context, stroke, layer);
  context.beginPath();
  context.arc(point.x, point.y, stroke.size / 2, 0, Math.PI * 2);
  context.fill();
  context.restore();
}

export function drawStrokeSegment(context: CanvasRenderingContext2D, stroke: Stroke, layer: Layer, from: Point, to: Point) {
  if (from.x === to.x && from.y === to.y) return;
  context.save();
  configure(context, stroke, layer);
  context.beginPath();
  context.moveTo(from.x, from.y);
  context.lineTo(to.x, to.y);
  context.stroke();
  context.restore();
}

export function drawStroke(context: CanvasRenderingContext2D, stroke: Stroke, layer: Layer) {
  drawStrokeStart(context, stroke, layer);
  for (let index = 1; index < stroke.points.length; index++) drawStrokeSegment(context, stroke, layer, stroke.points[index - 1], stroke.points[index]);
}
