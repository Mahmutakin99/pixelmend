import {describe, expect, it} from 'vitest';
import {normalizePreferences} from './preferences';

describe('preferences', () => {
  it('keeps a persisted canvas sensitivity within its safe range', () => {
    expect(normalizePreferences({zoomSensitivity: 2.5}).zoomSensitivity).toBe(2.5);
    expect(normalizePreferences({zoomSensitivity: 99}).zoomSensitivity).toBe(4);
  });

  it('uses balanced models and automatic performance by default', () => {
    expect(normalizePreferences({})).toMatchObject({removeModelTier: 'balanced', upscaleModelTier: 'balanced', performanceMode: 'automatic'});
  });
});
