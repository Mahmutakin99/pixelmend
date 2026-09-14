export type BlobRef = { id: string; uri: string; width: number; height: number };
export type Point = { x: number; y: number };
export type Stroke = { id: string; mode: 'draw' | 'erase'; points: Point[]; color: string; opacity: number; size: number; hardness: number };
export type Snapshot = { photo: BlobRef; paint: Stroke[]; selection: Stroke[]; label: string };
export type EditorDocument = { version: 1; original: BlobRef; history: { past: Snapshot[]; present: Snapshot; future: Snapshot[] } };

const cloneSnapshot = (snapshot: Snapshot): Snapshot => structuredClone(snapshot);
const validBlob = (value: any): value is BlobRef => !!value && typeof value.id === 'string' && value.id.length > 0 && typeof value.uri === 'string' && value.uri.startsWith('pixelmend://') && Number.isInteger(value.width) && value.width > 0 && Number.isInteger(value.height) && value.height > 0;
const validStroke = (value: any): value is Stroke => !!value && typeof value.id === 'string' && (value.mode === 'draw' || value.mode === 'erase') && Array.isArray(value.points) && value.points.length > 0 && value.points.every((p: any) => Number.isFinite(p?.x) && Number.isFinite(p?.y)) && typeof value.color === 'string' && Number.isFinite(value.opacity) && Number.isFinite(value.size) && Number.isFinite(value.hardness);

export function createDocument(photo: BlobRef): EditorDocument {
  if (!validBlob(photo)) throw new Error('project_invalid');
  const snapshot = { photo, paint: [], selection: [], label: 'opened' };
  return { version: 1, original: photo, history: { past: [], present: snapshot, future: [] } };
}
function commit(document: EditorDocument, snapshot: Snapshot): EditorDocument {
  return { ...document, history: { past: [...document.history.past, cloneSnapshot(document.history.present)], present: snapshot, future: [] } };
}
export function addStroke(document: EditorDocument, target: 'paint' | 'selection', stroke: Stroke): EditorDocument {
  if (!validStroke(stroke)) throw new Error('project_invalid');
  const present = cloneSnapshot(document.history.present);
  present[target].push(structuredClone(stroke)); present.label = target === 'paint' ? 'paint' : 'selection';
  return commit(document, present);
}
export function applyResult(document: EditorDocument, photo: BlobRef, operation: 'remove' | 'upscale'): EditorDocument {
  if (!validBlob(photo)) throw new Error('project_invalid');
  const before = document.history.present;
  const ratioX = operation === 'upscale' ? photo.width / before.photo.width : 1;
  const ratioY = operation === 'upscale' ? photo.height / before.photo.height : 1;
  if (operation === 'upscale' && (!Number.isFinite(ratioX) || !Number.isFinite(ratioY) || ratioX <= 0 || ratioY <= 0)) throw new Error('project_invalid');
  const brushRatio = Math.sqrt(ratioX * ratioY);
  const scale = (strokes: Stroke[]) => strokes.map(s => ({ ...structuredClone(s), size: s.size * brushRatio, points: s.points.map(p => ({ x: p.x * ratioX, y: p.y * ratioY })) }));
  return commit(document, { photo, paint: scale(before.paint), selection: operation === 'remove' ? [] : scale(before.selection), label: operation });
}
export function undo(document: EditorDocument): EditorDocument {
  if (!document.history.past.length) return document;
  const past = document.history.past.slice(0, -1); const present = document.history.past[document.history.past.length - 1];
  return { ...document, history: { past, present: cloneSnapshot(present), future: [cloneSnapshot(document.history.present), ...document.history.future] } };
}
export function redo(document: EditorDocument): EditorDocument {
  if (!document.history.future.length) return document;
  const [next, ...future] = document.history.future;
  return { ...document, history: { past: [...document.history.past, cloneSnapshot(document.history.present)], present: cloneSnapshot(next), future } };
}
export function parseDocument(value: unknown): EditorDocument {
  const doc = value as EditorDocument;
  if (!doc || doc.version !== 1 || !validBlob(doc.original) || !doc.history || !Array.isArray(doc.history.past) || !Array.isArray(doc.history.future)) throw new Error('project_invalid');
  const validSnapshot = (s: any) => !!s && validBlob(s.photo) && Array.isArray(s.paint) && Array.isArray(s.selection) && s.paint.every(validStroke) && s.selection.every(validStroke) && typeof s.label === 'string';
  if (![...doc.history.past, doc.history.present, ...doc.history.future].every(validSnapshot)) throw new Error('project_invalid');
  return structuredClone(doc);
}
