export type ModelTier = 'fast' | 'balanced' | 'advanced';
export type PerformanceMode = 'automatic' | 'low-resource';
export type PixelMendPreferences = {
  language: string;
  theme: string;
  zoomSensitivity: number;
  removeModelTier: ModelTier;
  upscaleModelTier: ModelTier;
  performanceMode: PerformanceMode;
};

const defaults: PixelMendPreferences = {
  language: 'tr', theme: 'system', zoomSensitivity: 1.5,
  removeModelTier: 'balanced', upscaleModelTier: 'balanced', performanceMode: 'automatic',
};

export function normalizePreferences(value: Partial<PixelMendPreferences>): PixelMendPreferences {
  const zoom = Number(value.zoomSensitivity);
  return {
    ...defaults,
    ...value,
    zoomSensitivity: Number.isFinite(zoom) ? Math.max(.5, Math.min(4, zoom)) : defaults.zoomSensitivity,
    removeModelTier: ['fast', 'balanced'].includes(value.removeModelTier || '') ? value.removeModelTier! : defaults.removeModelTier,
    upscaleModelTier: ['fast', 'balanced'].includes(value.upscaleModelTier || '') ? value.upscaleModelTier! : defaults.upscaleModelTier,
    performanceMode: value.performanceMode === 'low-resource' ? 'low-resource' : defaults.performanceMode,
  };
}
