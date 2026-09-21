export const MAX_OUTPUT_PIXELS = 200_000_000;

export type Dimensions = {width: number; height: number};

export function preserveDimensions(source: Dimensions): Dimensions {
  return {width: source.width, height: source.height};
}

export function fitDimension(source: Dimensions, edited: 'width' | 'height', value: number): Dimensions {
  const normalized = Math.max(1, Math.round(value));
  return edited === 'width'
    ? {width: normalized, height: Math.max(1, Math.round(normalized * source.height / source.width))}
    : {width: Math.max(1, Math.round(normalized * source.width / source.height)), height: normalized};
}

export function targetIsValid(width: number, height: number, maxPixels = MAX_OUTPUT_PIXELS) {
  return Number.isSafeInteger(width) && Number.isSafeInteger(height) && width > 0 && height > 0 && width * height <= maxPixels;
}
