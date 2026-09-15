import {describe, expect, it} from 'vitest';
import {fitDimension, targetIsValid} from './upscale';

describe('upscale dimensions', () => {
  it('keeps aspect ratio while a dimension is edited', () => {
    expect(fitDimension({width: 1600, height: 900}, 'width', 2400)).toEqual({width: 2400, height: 1350});
    expect(fitDimension({width: 1600, height: 900}, 'height', 2160)).toEqual({width: 3840, height: 2160});
  });

  it('accepts a safe target and rejects invalid or over-limit targets', () => {
    expect(targetIsValid(3840, 2160)).toBe(true);
    expect(targetIsValid(0, 2160)).toBe(false);
    expect(targetIsValid(20000, 10000)).toBe(true);
    expect(targetIsValid(20001, 10000)).toBe(false);
    expect(targetIsValid(10000, 6000, 50_000_000)).toBe(false);
    expect(targetIsValid(10000, 6000, 80_000_000)).toBe(true);
  });
});
