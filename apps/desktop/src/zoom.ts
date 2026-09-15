/** Convert imprecise trackpad/wheel deltas into a bounded, gentle editor zoom. */
export function wheelZoom(current: number, deltaY: number, sensitivity: number) {
  const boundedDelta = Math.max(-50, Math.min(50, deltaY));
  const next = current * Math.exp(-boundedDelta * sensitivity);
  return Math.max(.25, Math.min(8, next));
}
