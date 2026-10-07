const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path');
const {Readable}=require('node:stream');
const a={id:'a'.repeat(32),uri:`pixelmend://asset/${'a'.repeat(32)}`,width:16,height:16};
const stroke={id:'s',mode:'draw',points:[{x:8,y:8}],color:'#ff0000',opacity:.5,size:4,hardness:1};
const snapshot={photo:a,paint:[stroke],selection:[],label:'paint'};
const document={version:1,original:a,history:{past:[snapshot],present:{...snapshot,generation:{operation:'text_edit',model_id:'klein',model_revision:'a'.repeat(40),seed:1,profile:'balanced',original_prompt:'pixelmend://asset/not-a-reference',used_prompt:'Add a cat',translated_prompt:'Add a cat'}},future:[snapshot]}};
test('v2 stores a photo once and shares strokes on round-trip without interpreting prompt URIs',async()=>{
 const {writeProject,readProject}=require('./project-codec.cjs');const folder=await fs.mkdtemp(path.join(os.tmpdir(),'pixelmend-project-')),file=path.join(folder,'test.pixelmend');let exports=0,imports=0;
 try{
  await writeProject(file,document,async()=>{exports++;return Readable.from([Buffer.from('photo bytes')]);});
  const reopened=await readProject(file,async photoFile=>{imports++;assert.equal(await fs.readFile(photoFile,'utf8'),'photo bytes');return {...a,id:'b'.repeat(32),uri:`pixelmend://asset/${'b'.repeat(32)}`};},async()=>{});
  assert.equal(exports,1);assert.equal(imports,1);assert.equal(reopened.history.present.paint[0],reopened.history.past[0].paint[0]);assert.equal(reopened.history.future[0].photo,reopened.original);
  assert.equal(reopened.history.present.generation.original_prompt,document.history.present.generation.original_prompt);
 }finally{await fs.rm(folder,{recursive:true,force:true});}
});
test('v1 projects still load and invalid strokes are rejected before importing',async()=>{
 const {readProject}=require('./project-codec.cjs');const folder=await fs.mkdtemp(path.join(os.tmpdir(),'pixelmend-project-')),file=path.join(folder,'old.pixelmend');let imports=0;
 try{
  const saved={format:'pixelmend',version:1,document,blobs:{[a.uri]:Buffer.from('legacy').toString('base64')}};
  await fs.writeFile(file,JSON.stringify(saved));const opened=await readProject(file,async f=>{imports++;assert.equal(await fs.readFile(f,'utf8'),'legacy');return a;},async()=>{});assert.equal(opened.history.past.length,1);
  saved.document=structuredClone(document);saved.document.history.present.paint[0].size=-2;await fs.writeFile(file,JSON.stringify(saved));await assert.rejects(readProject(file,async()=>{imports++;return a;},async()=>{}),/project_invalid/);assert.equal(imports,1);
 }finally{await fs.rm(folder,{recursive:true,force:true});}
});
test('failed project export preserves previous file and failed import releases provisional assets',async()=>{
 const {writeProject,readProject}=require('./project-codec.cjs');const folder=await fs.mkdtemp(path.join(os.tmpdir(),'pixelmend-project-')),file=path.join(folder,'test.pixelmend');
 const b={...a,id:'b'.repeat(32),uri:`pixelmend://asset/${'b'.repeat(32)}`},doc={...document,original:b};
 try{
  await fs.writeFile(file,'previous');await assert.rejects(writeProject(file,doc,async()=>{throw new Error('export failed');}),/export failed/);assert.equal(await fs.readFile(file,'utf8'),'previous');
  await writeProject(file,doc,async()=>Readable.from(['photo']));let imports=0;const released=[];
  await assert.rejects(readProject(file,async()=>{if(++imports===2)throw new Error('import failed');return b;},async id=>released.push(id)),/import failed/);assert.deepEqual(released,[b.id]);
 }finally{await fs.rm(folder,{recursive:true,force:true});}
});
