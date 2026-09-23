import {describe, expect, it} from 'vitest';
import {showsAiControls} from './ai-controls';

describe('AI controls visibility', () => {
  it('shows model controls only for an active AI workflow', () => {
    expect(showsAiControls('upscale', 'lanczos')).toBe(false);
    expect(showsAiControls('upscale', 'ai')).toBe(true);
    expect(showsAiControls('remove', 'opencv')).toBe(false);
    expect(showsAiControls('remove', 'lama')).toBe(true);
  });
});
