export function canvasCursor({editing, hasPreview, busy}: {editing: boolean; hasPreview: boolean; busy: boolean}) {
  return editing && !hasPreview && !busy ? 'none' : 'default';
}
