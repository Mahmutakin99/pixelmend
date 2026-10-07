const fs=require('node:fs'),fsp=require('node:fs/promises'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const {Readable,Transform}=require('node:stream'),{pipeline}=require('node:stream/promises');
const yazl=require('yazl'),yauzl=require('yauzl');
const {validDocument,photosOf}=require('./project-schema.mjs');
const {writeStreamAtomic}=require('./atomic-file.cjs');
const MAX_MANIFEST=64*1024**2,MAX_PHOTOS=32,DEFAULT_PHOTO_LIMIT=200000000*4+16*1024**2;
const invalid=()=>new Error('project_invalid');
function packDocument(doc){
 if(!validDocument(doc))throw invalid();
 const photos={},strokes={},photoKeys=new Map(),strokeKeys=new Map(),objectKeys=new WeakMap(),originals=new Map();
 const photo=p=>{let key=photoKeys.get(p.id);if(!key){key=`p${photoKeys.size}`;photoKeys.set(p.id,key);photos[key]={entry:`photos/${key}.png`,width:p.width,height:p.height};originals.set(key,p);}else{const old=originals.get(key);if(old.uri!==p.uri||old.width!==p.width||old.height!==p.height)throw invalid();}return key;};
 const stroke=s=>{let key=objectKeys.get(s);if(key)return key;const text=JSON.stringify(s);key=strokeKeys.get(text);if(!key){key=`s${strokeKeys.size}`;strokeKeys.set(text,key);strokes[key]=s;}objectKeys.set(s,key);return key;};
 const snapshot=s=>({...s,photo:photo(s.photo),paint:s.paint.map(stroke),selection:s.selection.map(stroke)});
 const document={original:photo(doc.original),history:{past:doc.history.past.map(snapshot),present:snapshot(doc.history.present),future:doc.history.future.map(snapshot)}};
 if(photoKeys.size>MAX_PHOTOS)throw invalid();
 return {manifest:{format:'pixelmend',version:2,photos,strokes,document},originals};
}
async function writeProject(file,doc,exportPhoto){
 const {manifest,originals}=packDocument(doc),zip=new yazl.ZipFile(),active=new Set();
 zip.on('error',error=>zip.outputStream.destroy(error));
 for(const [key,p]of originals){
  zip.addReadStreamLazy(manifest.photos[key].entry,{compress:false},callback=>{
   Promise.resolve().then(()=>exportPhoto(p)).then(source=>{
    let bytes=0;const digest=crypto.createHash('sha256');
    const hash=new Transform({transform(chunk,_encoding,next){bytes+=chunk.length;digest.update(chunk);next(null,chunk);},flush(next){manifest.photos[key].size_bytes=bytes;manifest.photos[key].sha256=digest.digest('hex');next();}});
    active.add(source);active.add(hash);hash.on('error',error=>zip.emit('error',error));source.on('error',error=>hash.destroy(error));hash.once('end',()=>{active.delete(source);active.delete(hash);});
    source.pipe(hash);callback(null,hash);
   },callback);
  });
 }
 zip.addReadStreamLazy('manifest.json',{},callback=>{
  try{const data=Buffer.from(JSON.stringify(manifest));if(data.length>MAX_MANIFEST)throw invalid();callback(null,Readable.from([data]));}catch(error){callback(error);}
 });
 zip.end({forceZip64Format:true});
 try{await writeStreamAtomic(file,zip.outputStream);}finally{for(const stream of active)stream.destroy();zip.outputStream.destroy();}
}
const openZip=file=>new Promise((resolve,reject)=>yauzl.open(file,{lazyEntries:true,autoClose:false,validateEntrySizes:true,strictFileNames:true},(error,zip)=>error?reject(error):resolve(zip)));
const entryStream=(zip,entry)=>new Promise((resolve,reject)=>zip.openReadStream(entry,(error,stream)=>error?reject(error):resolve(stream)));
async function indexZip(zip){
 if(zip.entryCount>MAX_PHOTOS+1)throw invalid();
 return new Promise((resolve,reject)=>{const entries=new Map();zip.on('error',reject);zip.on('entry',entry=>{if(entries.has(entry.fileName)||!(/^(manifest\.json|photos\/p\d+\.png)$/.test(entry.fileName))||entry.generalPurposeBitFlag&1){reject(invalid());return;}entries.set(entry.fileName,entry);zip.readEntry();});zip.once('end',()=>resolve(entries));zip.readEntry();});
}
async function bytesOf(stream,limit){let length=0;const chunks=[];for await(const chunk of stream){length+=chunk.length;if(length>limit)throw invalid();chunks.push(chunk);}return Buffer.concat(chunks,length);}
function unpack(manifest,photoRefs){
 if(manifest?.format!=='pixelmend'||manifest.version!==2||!manifest.document?.history||!manifest.strokes||Array.isArray(manifest.strokes))throw invalid();
 const layer=keys=>{if(!Array.isArray(keys))throw invalid();return keys.map(key=>{if(typeof key!=='string'||!Object.hasOwn(manifest.strokes,key))throw invalid();return manifest.strokes[key];});};
 const photo=key=>{if(typeof key!=='string'||!Object.hasOwn(photoRefs,key))throw invalid();return photoRefs[key];};
 const snapshot=s=>({...s,photo:photo(s?.photo),paint:layer(s?.paint),selection:layer(s?.selection)});
 const h=manifest.document.history;if(!Array.isArray(h.past)||!Array.isArray(h.future))throw invalid();
 const document={version:1,original:photo(manifest.document.original),history:{past:h.past.map(snapshot),present:snapshot(h.present),future:h.future.map(snapshot)}};
 if(!validDocument(document))throw invalid();return document;
}
async function readProject(file,importPhoto,releasePhoto,{maxPhotoBytes=DEFAULT_PHOTO_LIMIT}={}){
 const folder=await fsp.mkdtemp(path.join(os.tmpdir(),'pixelmend-project-')),provisional=[];let zip;
 try{
  const handle=await fsp.open(file,'r');let magic;try{const b=Buffer.alloc(4);await handle.read(b,0,4,0);magic=b.readUInt32LE();}finally{await handle.close();}
  if(magic!==0x04034b50){
   const saved=JSON.parse(await fsp.readFile(file,'utf8'));
   if(saved?.format!=='pixelmend'||saved.version!==1||!validDocument(saved.document)||!saved.blobs||typeof saved.blobs!=='object')throw invalid();
   const refs=new Map();let index=0;
   for(const photo of photosOf(saved.document)){
    if(refs.has(photo.uri))continue;
    const encoded=saved.blobs[photo.uri];if(typeof encoded!=='string'||encoded.length>Math.ceil(maxPhotoBytes/3)*4)throw invalid();
    const temporary=path.join(folder,`${index++}.png`);await fsp.writeFile(temporary,Buffer.from(encoded,'base64'),{mode:0o600});
    const imported=await importPhoto(temporary,photo);provisional.push(imported.id);if(imported.width!==photo.width||imported.height!==photo.height)throw invalid();refs.set(photo.uri,imported);await fsp.rm(temporary);
   }
   const doc=saved.document;doc.original=refs.get(doc.original.uri);for(const s of [...doc.history.past,doc.history.present,...doc.history.future])s.photo=refs.get(s.photo.uri);
   return doc;
  }
  zip=await openZip(file);const entries=await indexZip(zip),header=entries.get('manifest.json');if(!header||header.uncompressedSize>MAX_MANIFEST)throw invalid();
  const manifest=JSON.parse((await bytesOf(await entryStream(zip,header),MAX_MANIFEST)).toString('utf8'));
  if(!manifest.photos||Array.isArray(manifest.photos))throw invalid();const rows=Object.entries(manifest.photos),fake={},refs={};
  if(!rows.length||rows.length>MAX_PHOTOS||entries.size!==rows.length+1)throw invalid();
  for(const [key,p]of rows){if(!/^p\d+$/.test(key)||p?.entry!==`photos/${key}.png`||!entries.has(p.entry)||!Number.isSafeInteger(p.size_bytes)||p.size_bytes<=0||p.size_bytes>maxPhotoBytes||!/^[a-f0-9]{64}$/.test(p.sha256)||entries.get(p.entry).uncompressedSize!==p.size_bytes)throw invalid();fake[key]={id:key,uri:`pixelmend://asset/${key}`,width:p.width,height:p.height};}
  const checked=unpack(manifest,fake);if(new Set(photosOf(checked).map(p=>p.id)).size!==rows.length)throw invalid();
  for(const [key,p]of rows){
   const temporary=path.join(folder,`${key}.png`),digest=crypto.createHash('sha256');let bytes=0;
   const hash=new Transform({transform(chunk,_encoding,next){bytes+=chunk.length;if(bytes>p.size_bytes)return next(invalid());digest.update(chunk);next(null,chunk);}});
   await pipeline(await entryStream(zip,entries.get(p.entry)),hash,fs.createWriteStream(temporary,{flags:'wx',mode:0o600}));
   if(bytes!==p.size_bytes||digest.digest('hex')!==p.sha256)throw invalid();
   const imported=await importPhoto(temporary,p);provisional.push(imported.id);if(imported.width!==p.width||imported.height!==p.height)throw invalid();refs[key]=imported;await fsp.rm(temporary);
  }
  return unpack(manifest,refs);
 }catch(error){await Promise.all(provisional.map(id=>releasePhoto(id).catch(()=>{})));throw error;}
 finally{zip?.close();await fsp.rm(folder,{recursive:true,force:true});}
}
module.exports={writeProject,readProject};
