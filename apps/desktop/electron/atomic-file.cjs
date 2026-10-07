const fs=require('node:fs/promises'),path=require('node:path'),crypto=require('node:crypto');
const {pipeline}=require('node:stream/promises');

async function writeStreamAtomic(destination,source){
 const temporary=path.join(path.dirname(destination),`.${path.basename(destination)}.${crypto.randomUUID()}.tmp`);
 let handle;
 try{
  await pipeline(source,require('node:fs').createWriteStream(temporary,{flags:'wx',mode:0o600}));
  handle=await fs.open(temporary,'r+');
  await handle.sync();await handle.close();handle=undefined;
  await fs.rename(temporary,destination);
 }finally{
  await handle?.close().catch(()=>{});
  await fs.rm(temporary,{force:true}).catch(()=>{});
 }
}
module.exports={writeStreamAtomic};
