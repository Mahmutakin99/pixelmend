import {describe, expect, it} from 'vitest';
import {keepsErasePreview} from './cursor-preview';

describe('erase cursor preview', () => {
  it('stays visible for the complete erase stroke', () => {
    expect(keepsErasePreview('erase')).toBe(true);
    expect(keepsErasePreview('draw')).toBe(false);
  });
});
