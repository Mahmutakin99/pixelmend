import {describe, expect, it} from 'vitest';
import {boundedPan, wheelZoom} from './zoom';

describe('wheelZoom', () => {
  it('limits a large wheel delta to a practical zoom step', () => {
    expect(wheelZoom(1, -1000, 1.5)).toBeCloseTo(1.162, 2);
  });

  it('honours user sensitivity while keeping the zoom range bounded', () => {
    expect(wheelZoom(1, -50, 3)).toBeCloseTo(1.35, 2);
    expect(wheelZoom(7.9, -50, 3)).toBe(8);
    expect(wheelZoom(.26, 50, 3)).toBe(.25);
  });
  it('keeps middle-button panning inside the visible image bounds', () => {
    expect(boundedPan({x: 900, y: -900}, {width: 400, height: 300}, {width: 300, height: 200}, 2))
      .toEqual({x: 250, y: -200});
    expect(boundedPan({x: 20, y: 20}, {width: 100, height: 100}, {width: 300, height: 200}, 2))
      .toEqual({x: 0, y: 0});
  });
});
