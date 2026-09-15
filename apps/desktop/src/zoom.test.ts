import {describe, expect, it} from 'vitest';
import {wheelZoom} from './zoom';

describe('wheelZoom', () => {
  it('limits a large wheel delta to a gentle zoom step', () => {
    expect(wheelZoom(1, -1000, 0.001)).toBeCloseTo(1.051, 2);
  });

  it('honours user sensitivity while keeping the zoom range bounded', () => {
    expect(wheelZoom(1, -50, 0.004)).toBeCloseTo(1.221, 2);
    expect(wheelZoom(7.9, -50, 0.004)).toBe(8);
    expect(wheelZoom(.26, 50, 0.004)).toBe(.25);
  });
});
