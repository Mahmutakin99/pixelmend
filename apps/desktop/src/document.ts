export type BlobRef = { id: string; uri: string; width: number; height: number };
export type Point = { x: number; y: number };
export type Stroke = { id: string; mode: 'draw' | 'erase'; points: Point[]; color: string; opacity: number; size: number; hardness: number; continuation?:boolean };
export type Snapshot = { photo: BlobRef; paint: Stroke[]; selection: Stroke[]; label: string; generation?:GenerationInfo };
export type EditorDocument = { version: 1; original: BlobRef; history: { past: Snapshot[]; present: Snapshot; future: Snapshot[] } };

import {validBlob,validStroke,validDocument,validGeneration} from '../electron/project-schema.mjs';

export function createDocument(photo: BlobRef): EditorDocument {
  if (!validBlob(photo)) throw new Error('project_invalid');
  const snapshot = { photo, paint: [], selection: [], label: 'opened' };
  return { version: 1, original: photo, history: { past: [], present: snapshot, future: [] } };
}
function commit(document: EditorDocument, snapshot: Snapshot): EditorDocument {
  return { ...document, history: { past: [...document.history.past, document.history.present], present: snapshot, future: [] } };
}
export function applyGenerativeResult(document:EditorDocument,photo:BlobRef,generation:GenerationInfo):EditorDocument {
  if(!validBlob(photo)||!validGeneration(generation)||generation.operation!=='text_edit')throw new Error('project_invalid');
  return commit(document,{photo,paint:[],selection:[],label:'text_edit',generation:structuredClone(generation)});
}
export function createGeneratedDocument(photo:BlobRef,generation:GenerationInfo):EditorDocument {
  if(!validGeneration(generation)||generation.operation!=='text_to_image')throw new Error('project_invalid');
  const document=createDocument(photo);return {...document,history:{...document.history,present:{...document.history.present,generation:structuredClone(generation),label:'text_to_image'}}};
}
export function addStroke(document: EditorDocument, target: 'paint' | 'selection', stroke: Stroke): EditorDocument {
  const chunks:Stroke[]=[];
  if(!Array.isArray(stroke?.points)||!stroke.points.length)throw new Error('project_invalid');
  for(let offset=0;offset<stroke.points.length;){
    const end=Math.min(offset+8192,stroke.points.length);
    const chunk={...stroke,id:offset?`${stroke.id}:${offset}`:stroke.id,points:stroke.points.slice(offset,end),...(offset?{continuation:true}:{})};
    if(!validStroke(chunk,document.history.present.photo.width,document.history.present.photo.height))throw new Error('project_invalid');
    chunks.push(structuredClone(chunk));if(end===stroke.points.length)break;offset=end-1;
  }
  const layer=[...document.history.present[target],...chunks];
  if(layer.length>2048||layer.reduce((n,s)=>n+s.points.length,0)>250000)throw new Error('project_invalid');
  const present={...document.history.present,[target]:layer,label:target==='paint'?'paint':'selection'};

  return commit(document, present);
}
export function applyResult(document: EditorDocument, photo: BlobRef, operation: 'remove' | 'upscale'): EditorDocument {
  if (!validBlob(photo)) throw new Error('project_invalid');
  const before = document.history.present;
  const ratioX = operation === 'upscale' ? photo.width / before.photo.width : 1;
  const ratioY = operation === 'upscale' ? photo.height / before.photo.height : 1;
  if (operation === 'upscale' && (!Number.isFinite(ratioX) || !Number.isFinite(ratioY) || ratioX <= 0 || ratioY <= 0)) throw new Error('project_invalid');
  const brushRatio = Math.sqrt(ratioX * ratioY);
  const scale = (strokes: Stroke[]) => strokes.map(s => ({ ...s, size: s.size * brushRatio, points: s.points.map(p => ({ x: p.x * ratioX, y: p.y * ratioY })) }));
  return commit(document, { photo, paint: operation === 'remove' ? before.paint : scale(before.paint), selection: operation === 'remove' ? [] : scale(before.selection), label: operation });
}
export function undo(document: EditorDocument): EditorDocument {
  if (!document.history.past.length) return document;
  const past = document.history.past.slice(0, -1); const present = document.history.past[document.history.past.length - 1];
  return { ...document, history: { past, present: present, future: [document.history.present, ...document.history.future] } };
}
export function redo(document: EditorDocument): EditorDocument {
  if (!document.history.future.length) return document;
  const [next, ...future] = document.history.future;
  return { ...document, history: { past: [...document.history.past, document.history.present], present: next, future } };
}
export function parseDocument(value: unknown): EditorDocument {
  if (!validDocument(value)) throw new Error('project_invalid');
  const doc=structuredClone(value) as EditorDocument;
  const strokes=new Map<string,Stroke>(),keys=new WeakMap<Stroke,string>();
  for(const snapshot of [...doc.history.past,doc.history.present,...doc.history.future])for(const layer of ['paint','selection'] as const){
    snapshot[layer]=snapshot[layer].map(stroke=>{let key=keys.get(stroke);if(!key){key=JSON.stringify(stroke);keys.set(stroke,key);}const old=strokes.get(key);if(old)return old;strokes.set(key,stroke);return stroke;});
  }
  return doc;
}
import type {GenerationInfo} from './bridge';
