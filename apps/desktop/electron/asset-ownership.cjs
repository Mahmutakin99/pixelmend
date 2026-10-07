const opaqueId=v=>typeof v==='string'&&/^[a-f0-9]{32}$/.test(v);
const {AsyncLocalStorage}=require('node:async_hooks');
const terminal=new Set(['completed','failed','cancelled']);
function createOwnership(api,sources){
 const assets=new Map(),jobs=new Map(),released=new Set();let revision=-1,generation=0,resetting;const scope=new AsyncLocalStorage(),operations=new Set();
 const remember=id=>{released.add(id);if(released.size>1024)released.delete(released.values().next().value);};
 const requireAsset=id=>{const entry=assets.get(id);if(!opaqueId(id)||!entry||entry.deleting||entry.generation!==(scope.getStore()??generation))throw new Error('Geçersiz görsel');return entry;};
 const requireJob=id=>{if(!opaqueId(id)||!jobs.has(id)||jobs.get(id).generation!==(scope.getStore()??generation))throw new Error('Geçersiz iş');};
 async function collect(id){
  const e=assets.get(id);if(!e||e.document||e.transient||e.pins)return;
  if(e.deleting)return e.deleting;
  e.deleting=(async()=>{try{await api(`/assets/${id}`,{method:'DELETE'});assets.delete(id);sources.delete(`asset/${id}`);remember(id);}catch(error){if(error.httpStatus===404){assets.delete(id);sources.delete(`asset/${id}`);remember(id);}else throw error;}finally{e.deleting=undefined;}})();
  return e.deleting;
 }
 function pin(ids){const unique=[...new Set(ids)];for(const id of unique)requireAsset(id);for(const id of unique)assets.get(id).pins++;let done=false;return async()=>{if(done)return;done=true;for(const id of unique){const e=assets.get(id);if(e)e.pins--;}await Promise.all(unique.map(collect));};}
 async function finish(id){
  if(!jobs.has(id)){if(released.has(id))return;throw new Error('Geçersiz iş');}
  const e=jobs.get(id);if(e.deleting)return e.deleting;
  e.deleting=(async()=>{try{try{await api(`/jobs/${id}`,{method:'DELETE'});}catch(error){if(error.httpStatus!==404)throw error;}jobs.delete(id);for(const key of sources.keys())if(key.startsWith(`result/${id}/`))sources.delete(key);remember(id);await e.release();}finally{e.deleting=undefined;}})();return e.deleting;
 }
 async function abandon(id){
  if(!jobs.has(id)){if(released.has(id))return;throw new Error('Geçersiz iş');}
  const e=jobs.get(id);if(e.abandoning)return e.abandoning;
  e.abandoning=(async()=>{try{
   let state;
   try{state=await (await api(`/jobs/${id}`)).json();}catch(error){if(error.httpStatus!==404)throw error;await finish(id);return;}
   if(!terminal.has(state.status)){
    await api(`/jobs/${id}/cancel`,{method:'POST'});
    while(!terminal.has(state.status)){await new Promise(r=>setTimeout(r,50));try{state=await (await api(`/jobs/${id}`)).json();}catch(error){if(error.httpStatus!==404)throw error;break;}}
   }
   await finish(id);
  }finally{e.abandoning=undefined;}})();return e.abandoning;
 }
 function run(fn){
  const barrier=resetting,epoch=generation;
  const operation=(async()=>{await barrier;return scope.run(epoch,fn);})();
  operations.add(operation);operation.finally(()=>operations.delete(operation)).catch(()=>{});return operation;
 }
 function reset(){
  if(resetting)return resetting;
  const retiredBefore=++generation;revision=-1;const pending=[...operations];
  const cleanJobs=()=>Promise.allSettled([...jobs].filter(([,e])=>e.generation<retiredBefore).map(([id])=>abandon(id)));
  const cleanup=(async()=>{
   await cleanJobs();await Promise.allSettled(pending);const jobResults=await cleanJobs();
   const retired=[...assets].filter(([,e])=>e.generation<retiredBefore);
   for(const [,e]of retired){e.document=false;e.transient=false;}
   const results=await Promise.allSettled(retired.map(([id])=>collect(id)));
   const failed=[...jobResults,...results].find(r=>r.status==='rejected');if(failed)throw failed.reason;
  })();
  resetting=cleanup;cleanup.finally(()=>{if(resetting===cleanup)resetting=undefined;}).catch(()=>{});return cleanup;
 }
 return {
  requireAsset,requireJob,pin,run,ownsJob:id=>jobs.has(id),
  adoptAsset(id){if(!opaqueId(id))throw new Error('Geçersiz görsel');if(!assets.has(id))assets.set(id,{document:false,transient:true,pins:0,generation:scope.getStore()??generation});released.delete(id);},
  adoptJob(id,ids=[]){if(!opaqueId(id))throw new Error('Geçersiz iş');if(!jobs.has(id))jobs.set(id,{release:pin(ids),generation:scope.getStore()??generation});released.delete(id);},
  async disposeAsset(id){if(assets.get(id)?.deleting)return assets.get(id).deleting;if(released.has(id)&&!assets.has(id))return;const e=requireAsset(id);e.transient=false;await collect(id);},
  async setDocumentAssets(next,ids){if(!Number.isSafeInteger(next)||!Array.isArray(ids))throw new Error('project_invalid');if((scope.getStore()??generation)!==generation||next<=revision)return;const keep=new Set(ids);for(const id of keep)requireAsset(id);revision=next;for(const [id,e]of assets){if(e.generation!==generation)continue;e.document=keep.has(id);if(e.document)e.transient=false;}await Promise.all([...assets].filter(([,e])=>e.generation===generation).map(([id])=>collect(id)));},
  finish,abandon,reset,
 };
}
module.exports={createOwnership};
