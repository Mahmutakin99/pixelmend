import {describe, expect, it} from 'vitest';
import {documentFingerprint, isDocumentDirty} from './document-state';
import {createDocument, addStroke, undo, redo} from './document';

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
  it('ignores changed undo/redo stacks after returning to the saved pixels and layers', () => {
    const opened=createDocument({id:'source',uri:'pixelmend://asset/source',width:10,height:10});
    const saved=documentFingerprint(opened);
    const edited=addStroke(opened,'paint',{id:'stroke',mode:'draw',points:[{x:1,y:1}],color:'#000000',opacity:1,size:2,hardness:1});
    expect(isDocumentDirty(undo(edited),saved)).toBe(false);
    expect(isDocumentDirty(redo(undo(edited)),saved)).toBe(true);
  });
});
