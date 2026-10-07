const crypto=require('node:crypto');
const opaqueId=value=>typeof value==='string'&&/^[a-f0-9]{32}$/.test(value);
function text(value){
 if(typeof value!=='string'||!value.trim()||[...value].length>1000||!value.isWellFormed())throw new Error('Geçersiz komut: en fazla 1000 karakter girin.');
 return value.trim();
}
function strokes(value){
 if(!Array.isArray(value)||value.length>10000)throw new Error('Geçersiz çizimler');
 let count=0;
 for(const s of value){
  if(!s||!['draw','erase'].includes(s.mode)||!Array.isArray(s.points)||!s.points.length||
     !Number.isFinite(s.size)||s.size<=0||!Number.isFinite(s.opacity)||s.opacity<0||s.opacity>1||
     !Number.isFinite(s.hardness)||s.hardness<0||s.hardness>1||!/^#[a-f0-9]{6}$/i.test(s.color)||
     s.points.some(p=>!Number.isFinite(p?.x)||!Number.isFinite(p?.y)))throw new Error('Geçersiz çizimler');
  count+=s.points.length;if(count>200000)throw new Error('Seçim çok ayrıntılı. Daha kısa çizimler kullanın.');
 }
 return structuredClone(value);
}
function generativeBody(value){
 if(!value||typeof value!=='object'||!['text_edit','text_to_image'].includes(value.operation))throw new Error('Geçersiz üretim isteği');
 const common=['operation','prompt','promptLanguage','englishOverride','profile','seed'];
 const specific=value.operation==='text_edit'?['assetId','selectionStrokes','paintStrokes']:['aspect'];
 if(Object.keys(value).some(k=>![...common,...specific].includes(k)))throw new Error('Geçersiz üretim alanı');
 if(!['tr','en'].includes(value.promptLanguage)||!['low-resource','balanced'].includes(value.profile))throw new Error('Geçersiz profil veya dil');
 const seed=value.seed===undefined?crypto.randomBytes(4).readUInt32LE():value.seed;
 if(!Number.isInteger(seed)||seed<0||seed>=2**32)throw new Error('Geçersiz seed');
 const body={operation:value.operation,prompt:text(value.prompt),prompt_language:value.promptLanguage,profile:value.profile,seed};
 if(value.englishOverride!==undefined)body.english_override=text(value.englishOverride);
 if(value.operation==='text_to_image'){
  if(!['square','landscape','portrait'].includes(value.aspect))throw new Error('Geçersiz oran');body.aspect=value.aspect;
 }else{
  if(!opaqueId(value.assetId))throw new Error('Geçersiz kaynak görsel');
  body.asset_id=value.assetId;body.selection_strokes=strokes(value.selectionStrokes);body.paint_strokes=strokes(value.paintStrokes);
 }
 if(Buffer.byteLength(JSON.stringify(body))>16*1024**2)throw new Error('Üretim isteği çok büyük.');
 return body;
}
function registerGenerativeIpc(ipcMain,api,authorized,sources,ownership){
 const owner=ownership||require('./asset-ownership.cjs').createOwnership(api,sources);
 const requireSender=e=>{if(!authorized(e.sender))throw new Error('Geçersiz pencere');};
 ipcMain.handle('pixelmend:generative-preflight',async(e,request)=>{requireSender(e);return (await api('/generative/preflight',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(generativeBody(request))})).json();});
 ipcMain.handle('pixelmend:generative-memory',async(e,request)=>{requireSender(e);return (await api('/generative/memory',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(generativeBody(request))})).json();});
 ipcMain.handle('pixelmend:start-generative-job',async(e,request)=>{requireSender(e);const body=generativeBody(request);const release=body.asset_id?owner.pin([body.asset_id]):async()=>{};try{const job=await (await api('/generative/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})).json();owner.adoptJob(job.job_id,body.asset_id?[body.asset_id]:[]);return job;}finally{await release();}});
 ipcMain.handle('pixelmend:dispose-generative-job',async(e,id)=>{requireSender(e);await owner.abandon(id);});
 ipcMain.handle('pixelmend:dispose-job',async(e,id)=>{requireSender(e);await owner.abandon(id);});
 ipcMain.handle('pixelmend:dispose-asset',async(e,id)=>{requireSender(e);await owner.disposeAsset(id);});
 ipcMain.handle('pixelmend:set-document-assets',async(e,{revision,assetIds})=>{requireSender(e);await owner.setDocumentAssets(revision,assetIds);});
 return {owns:owner.ownsJob,async finish(id,asset){if(asset)owner.adoptAsset(asset);await owner.finish(id);},reset:owner.reset};
}
module.exports={generativeBody,registerGenerativeIpc,opaqueId};
