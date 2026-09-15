import {describe, expect, it} from 'vitest';
import {userError} from './errors';

describe('userError', () => {
  it('never exposes the raw sidecar stroke validation message', () => {
    const value = userError('save', new Error('Renderer asset: Error: stroke point is outside image bounds'));
    expect(value.title).toBe('Çizim kaydedilemedi');
    expect(value.message).not.toContain('stroke point');
  });
  it('uses an actionable message for an invalid custom target', () => {
    expect(userError('upscale', new Error('target_invalid')).title).toBe('Geçersiz ölçü');
  });
});
