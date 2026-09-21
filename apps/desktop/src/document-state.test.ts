import {describe, expect, it} from 'vitest';
import {documentFingerprint, isDocumentDirty} from './document-state';

describe('document save state', () => {
  const document = {version: 1, history: {past: [{label: 'opened'}], present: {label: 'paint'}, future: []}};

  it('marks the exact saved document state as clean even when undo history exists', () => {
    const saved = documentFingerprint(document);
    expect(isDocumentDirty(document, saved)).toBe(false);
  });

  it('becomes clean again when undo returns to the saved snapshot', () => {
    const saved = documentFingerprint(document);
    const changed = {...document, history: {...document.history, present: {label: 'selection'}}};
    expect(isDocumentDirty(changed, saved)).toBe(true);
    expect(isDocumentDirty(document, saved)).toBe(false);
  });
});
