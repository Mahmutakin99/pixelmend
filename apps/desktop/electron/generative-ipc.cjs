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
function registerGenerativeIpc(ipcMain,api,authorized,sources){
 const jobs=new Set(),assets=new Set();
 const requireSender=e=>{if(!authorized(e.sender))throw new Error('Geçersiz pencere');};
 const removeJob=async id=>{
  if(!opaqueId(id)||!jobs.has(id))throw new Error('Geçersiz üretim işi');
  await api(`/jobs/${id}`,{method:'DELETE'});jobs.delete(id);
 };
 const abandon=async id=>{
  if(!opaqueId(id)||!jobs.has(id))throw new Error('Geçersiz üretim işi');
  let state=await (await api(`/jobs/${id}`)).json();
  if(!['completed','failed','cancelled'].includes(state.status)){
   await api(`/jobs/${id}/cancel`,{method:'POST'});
   const deadline=Date.now()+6000;
   do{await new Promise(r=>setTimeout(r,50));state=await (await api(`/jobs/${id}`)).json();}
   while(!['completed','failed','cancelled'].includes(state.status)&&Date.now()<deadline);
  }
  await removeJob(id);
 };
 ipcMain.handle('pixelmend:generative-preflight',async(e,request)=>{requireSender(e);return (await api('/generative/preflight',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(generativeBody(request))})).json();});
 ipcMain.handle('pixelmend:start-generative-job',async(e,request)=>{requireSender(e);const job=await (await api('/generative/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(generativeBody(request))})).json();jobs.add(job.job_id);return job;});
 ipcMain.handle('pixelmend:dispose-generative-job',async(e,id)=>{requireSender(e);await abandon(id);});
 ipcMain.handle('pixelmend:dispose-asset',async(e,id)=>{requireSender(e);if(!opaqueId(id)||!assets.has(id))throw new Error('Geçersiz aday görsel');await api(`/assets/${id}`,{method:'DELETE'});sources.delete(`asset/${id}`);assets.delete(id);});
 return {owns:id=>jobs.has(id),async finish(id,asset){if(!jobs.has(id))return;assets.add(asset);await removeJob(id);},async reset(){for(const id of [...jobs])await abandon(id).catch(()=>{});for(const id of [...assets]){await api(`/assets/${id}`,{method:'DELETE'}).catch(()=>{});sources.delete(`asset/${id}`);assets.delete(id);}}};
}
module.exports={generativeBody,registerGenerativeIpc,opaqueId};
