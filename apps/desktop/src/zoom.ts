/** Convert imprecise trackpad/wheel deltas into a bounded, usable editor zoom. */
export function wheelZoom(current: number, deltaY: number, sensitivity: number) {
  const boundedDelta = Math.max(-50, Math.min(50, deltaY));
  const next = current * Math.exp(-boundedDelta * sensitivity * .002);
  return Math.max(.25, Math.min(8, next));
}

export function boundedPan(pan: {x: number; y: number}, image: {width: number; height: number}, viewport: {width: number; height: number}, scale: number) {
  const maxX = Math.max(0, (image.width * scale - viewport.width) / 2);
  const maxY = Math.max(0, (image.height * scale - viewport.height) / 2);
  return {x: Math.max(-maxX, Math.min(maxX, pan.x)), y: Math.max(-maxY, Math.min(maxY, pan.y))};
}
