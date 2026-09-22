export function canvasCursor({editing, hasPreview, busy, hasRing = false}: {editing: boolean; hasPreview: boolean; busy: boolean; hasRing?: boolean}) {
  return editing && hasRing && !hasPreview && !busy ? 'none' : 'default';
}
