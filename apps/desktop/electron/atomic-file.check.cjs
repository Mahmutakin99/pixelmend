const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs/promises'),path=require('node:path'),os=require('node:os');
const {Readable}=require('node:stream');
test('failed stream preserves the destination and removes staging files',async()=>{
 const {writeStreamAtomic}=require('./atomic-file.cjs');
 const folder=await fs.mkdtemp(path.join(os.tmpdir(),'pixelmend-atomic-')),file=path.join(folder,'image.png');
 try{
  await fs.writeFile(file,'previous');
  const stream=Readable.from((async function*(){yield Buffer.from('partial');throw new Error('broken stream');})());
  await assert.rejects(writeStreamAtomic(file,stream),/broken stream/);
  assert.equal(await fs.readFile(file,'utf8'),'previous');assert.deepEqual(await fs.readdir(folder),['image.png']);
 }finally{await fs.rm(folder,{recursive:true,force:true});}
});
test('successful stream replaces the complete destination',async()=>{
 const {writeStreamAtomic}=require('./atomic-file.cjs');
 const folder=await fs.mkdtemp(path.join(os.tmpdir(),'pixelmend-atomic-')),file=path.join(folder,'image.png');
 try{await fs.writeFile(file,'previous');await writeStreamAtomic(file,Readable.from(['new',' complete']));assert.equal(await fs.readFile(file,'utf8'),'new complete');assert.deepEqual(await fs.readdir(folder),['image.png']);}
 finally{await fs.rm(folder,{recursive:true,force:true});}
});
