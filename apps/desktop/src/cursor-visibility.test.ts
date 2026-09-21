import {describe, expect, it} from 'vitest';
import {canvasCursor} from './cursor-visibility';

describe('canvas cursor', () => {
  it('only hides the system cursor while an editable brush tool is active', () => {
    expect(canvasCursor({editing: true, hasPreview: false, busy: false})).toBe('none');
    expect(canvasCursor({editing: false, hasPreview: false, busy: false})).toBe('default');
    expect(canvasCursor({editing: true, hasPreview: true, busy: false})).toBe('default');
    expect(canvasCursor({editing: true, hasPreview: false, busy: true})).toBe('default');
  });
});
