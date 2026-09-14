import {describe,it,expect} from 'vitest';
import {createDocument,addStroke,undo,redo,applyResult,parseDocument} from './document';
const photo={id:'a'.repeat(64),uri:'pixelmend://blob/a',width:100,height:80};
const stroke={id:'s',mode:'draw' as const,points:[{x:10,y:20}],color:'#ff0000',opacity:.4,size:8,hardness:.7};
describe('immutable project history',()=>{
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
