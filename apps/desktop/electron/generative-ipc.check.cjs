const test=require('node:test');const assert=require('node:assert/strict');
const {generativeBody,registerGenerativeIpc}=require('./generative-ipc.cjs');
const request={operation:'text_to_image',prompt:'Bir kedi.',promptLanguage:'tr',profile:'low-resource',aspect:'square'};
test('generative bridge is discriminated, bounded and chooses its own seed',()=>{
 const value=generativeBody(request);assert.equal(value.prompt_language,'tr');assert.ok(Number.isInteger(value.seed)&&value.seed>=0&&value.seed<2**32);
 for(const patch of [{model_dir:'/tmp'},{width:4096},{operation:'remove'},{seed:-1},{seed:true},{prompt:'ğ'.repeat(1001)},{prompt:'\ud800'},{assetId:'a'.repeat(32)},{profile:'auto'},{aspect:'film'}])assert.throws(()=>generativeBody({...request,...patch}));
 const edit={operation:'text_edit',prompt:'Add a cat.',promptLanguage:'en',profile:'balanced',assetId:'a'.repeat(32),selectionStrokes:[{mode:'draw',points:[{x:1,y:2}],size:32,opacity:1,hardness:1,color:'#ffffff'}],paintStrokes:[]};
 assert.equal(generativeBody(edit).asset_id,edit.assetId);
 assert.throws(()=>generativeBody({...edit,selectionStrokes:[{...edit.selectionStrokes[0],points:[{x:NaN,y:1}]}]}));
});
test('only authorized IPC and owned generative jobs/assets can be disposed',async()=>{
 const handlers=new Map();const calls=[];const job='b'.repeat(32),asset='c'.repeat(32);
 const api=async(route)=>{calls.push(route);return {json:async()=>route==='/generative/jobs'?{job_id:job}:{}}};
 const owner=registerGenerativeIpc({handle:(id,fn)=>handlers.set(id,fn)},api,s=>s==='window',new Map());
 await assert.rejects(handlers.get('pixelmend:start-generative-job')({sender:'foreign'},request));
 await handlers.get('pixelmend:start-generative-job')({sender:'window'},request);
 await assert.rejects(handlers.get('pixelmend:dispose-generative-job')({sender:'window'},'../../models'));
 await owner.finish(job,asset);assert.ok(calls.includes(`/jobs/${job}`));
 await handlers.get('pixelmend:dispose-asset')({sender:'window'},asset);
 await assert.rejects(handlers.get('pixelmend:dispose-asset')({sender:'window'},'d'.repeat(32)));
});
