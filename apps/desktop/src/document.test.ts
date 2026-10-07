import {describe,it,expect} from 'vitest';
import {createDocument,addStroke,undo,redo,applyResult,parseDocument,applyGenerativeResult,createGeneratedDocument} from './document';
const photo={id:'a'.repeat(64),uri:'pixelmend://blob/a',width:100,height:80};
const stroke={id:'s',mode:'draw' as const,points:[{x:10,y:20}],color:'#ff0000',opacity:.4,size:8,hardness:.7};
describe('immutable project history',()=>{
 it('shares published strokes across history without retaining mutable input',()=>{
  const input=structuredClone(stroke),a=addStroke(createDocument(photo),'paint',input),b=addStroke(a,'paint',{...stroke,id:'second'});
  input.points[0].x=42;
  expect(a.history.present.paint[0].points[0].x).toBe(10);
  expect(b.history.past[1]).toBe(a.history.present);
  expect(b.history.present.paint[0]).toBe(a.history.present.paint[0]);
  expect(undo(b).history.present).toBe(a.history.present);
  expect(redo(undo(b)).history.present).toBe(b.history.present);
 });
 it.each([{size:-2},{opacity:0},{opacity:1.5},{hardness:2},{color:'red'},{points:[{x:100,y:20}]}])('rejects invalid project brush %j',invalid=>{
  const doc=createDocument(photo);doc.history.present.paint=[{...stroke,...invalid}];
  expect(()=>parseDocument(doc)).toThrow('project_invalid');
 });
 it('keeps paint and selection separate and restores both across removal',()=>{
  const initial=createDocument(photo); const painted=addStroke(initial,'paint',stroke);
  const selected=addStroke(painted,'selection',stroke);
  const applied=applyResult(selected,{...photo,id:'b'.repeat(64)},'remove');
  expect(initial.history.present.paint).toEqual([]);
  expect(applied.history.present.paint).toEqual([stroke]);
  expect(applied.history.present.selection).toEqual([]);
  expect(undo(applied).history.present).toEqual(selected.history.present);
  expect(redo(undo(applied)).history.present).toEqual(applied.history.present);
 });
 it('scales stroke coordinates and widths while preserving brush settings and prior snapshots',()=>{
  const doc=addStroke(addStroke(createDocument(photo),'paint',stroke),'selection',stroke);
  const scaled=applyResult(doc,{...photo,width:200,height:160},'upscale');
  expect(scaled.history.present.paint[0]).toEqual({...stroke,size:16,points:[{x:20,y:40}]});
  expect(scaled.history.present.selection[0].size).toBe(16);
  expect(doc.history.present.paint[0].size).toBe(8);
 });
 it('scales independently for a custom output size',()=>{
  const doc=addStroke(createDocument(photo),'paint',stroke);
  const resized=applyResult(doc,{...photo,width:150,height:120},'upscale');
  expect(resized.history.present.paint[0]).toEqual({...stroke,size:12,points:[{x:15,y:30}]});
 });
 it('drops only the redo branch on a new edit and reopens complete history',()=>{
  const a=addStroke(createDocument(photo),'paint',stroke);
  const b=addStroke(a,'paint',{...stroke,id:'second'});
  const branch=addStroke(undo(b),'selection',stroke);
  expect(redo(branch)).toEqual(branch);
  const reopened=parseDocument(JSON.parse(JSON.stringify(branch)));
  expect(undo(reopened).history.present.paint).toHaveLength(1);
  expect(undo(reopened).history.present.selection).toHaveLength(0);
 });
 it('rejects malformed history and non-finite stroke coordinates',()=>{
  expect(()=>parseDocument({version:1})).toThrow();
  const doc=addStroke(createDocument(photo),'paint',stroke);
  doc.history.present.paint[0].points[0].x=NaN;
  expect(()=>parseDocument(doc)).toThrow();
 });
});

describe('generative document history',()=>{
 const info={operation:'text_edit' as const,model_id:'klein',model_revision:'a'.repeat(40),seed:7,profile:'low-resource' as const,original_prompt:'Bir kedi.',used_prompt:'Add a cat.',translated_prompt:'Add a cat.'};
 it('bakes paint once and restores photo, paint and selection in one undo step',()=>{
  const before=addStroke(addStroke(createDocument(photo),'paint',stroke),'selection',stroke);
  const next=applyGenerativeResult(before,{...photo,id:'generated'},info);
  expect(next.history.past.length).toBe(before.history.past.length+1);
  expect(next.history.present.paint).toEqual([]);expect(next.history.present.selection).toEqual([]);
  expect(undo(next).history.present).toEqual(before.history.present);
  expect(redo(undo(next)).history.present).toEqual(next.history.present);
  expect(parseDocument(JSON.parse(JSON.stringify(next))).history.present.generation).toEqual(info);
 });
 it('creates a separate generated document and keeps old projects readable',()=>{
  const old=createDocument(photo);const fresh=createGeneratedDocument({...photo,id:'new'}, {...info,operation:'text_to_image'});
  expect(fresh.history.past).toEqual([]);expect(old.history.present.generation).toBeUndefined();expect(parseDocument(old)).toEqual(old);
  expect(()=>parseDocument({...fresh,history:{...fresh.history,present:{...fresh.history.present,generation:{...info,seed:-1}}}})).toThrow();
 });
});

it('commits an 8193-point gesture in one undo step without repeating the initial dab',()=>{
 const input={...stroke,points:Array.from({length:8193},(_,i)=>({x:i%90,y:20}))};
 const doc=addStroke(createDocument(photo),'paint',input),chunks=doc.history.present.paint;
 expect(chunks.length).toBe(2);expect(chunks.every(s=>s.points.length<=8192)).toBe(true);
 expect(chunks[1].continuation).toBe(true);expect(chunks[1].points[0]).toEqual(chunks[0].points.at(-1));
 expect(doc.history.past).toHaveLength(1);expect(parseDocument(doc)).toEqual(doc);expect(undo(doc).history.present.paint).toEqual([]);
});
