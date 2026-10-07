const opaqueId=v=>typeof v==='string'&&/^[a-f0-9]{32}$/.test(v);
const terminal=new Set(['completed','failed','cancelled']);
function createOwnership(api,sources){
 const assets=new Map(),jobs=new Map(),released=new Set();let revision=-1;
 const remember=id=>{released.add(id);if(released.size>1024)released.delete(released.values().next().value);};
 const requireAsset=id=>{const entry=assets.get(id);if(!opaqueId(id)||!entry||entry.deleting)throw new Error('Geçersiz görsel');return entry;};
 const requireJob=id=>{if(!opaqueId(id)||!jobs.has(id))throw new Error('Geçersiz iş');};
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
  e.deleting=(async()=>{try{await api(`/jobs/${id}`,{method:'DELETE'});jobs.delete(id);for(const key of sources.keys())if(key.startsWith(`result/${id}/`))sources.delete(key);remember(id);await e.release();}finally{e.deleting=undefined;}})();return e.deleting;
 }
 async function abandon(id){requireJob(id);let state=await (await api(`/jobs/${id}`)).json();if(!terminal.has(state.status)){await api(`/jobs/${id}/cancel`,{method:'POST'});while(!terminal.has(state.status)){await new Promise(r=>setTimeout(r,50));state=await (await api(`/jobs/${id}`)).json();}}await finish(id);}
 return {
  requireAsset,requireJob,pin,ownsJob:id=>jobs.has(id),
  adoptAsset(id){if(!opaqueId(id))throw new Error('Geçersiz görsel');if(!assets.has(id))assets.set(id,{document:false,transient:true,pins:0});released.delete(id);},
  adoptJob(id,ids=[]){if(!opaqueId(id))throw new Error('Geçersiz iş');if(!jobs.has(id))jobs.set(id,{release:pin(ids)});released.delete(id);},
  async disposeAsset(id){if(released.has(id)&&!assets.has(id))return;const e=requireAsset(id);e.transient=false;await collect(id);},
  async setDocumentAssets(next,ids){if(!Number.isSafeInteger(next)||!Array.isArray(ids))throw new Error('project_invalid');if(next<=revision)return;const keep=new Set(ids);for(const id of keep)requireAsset(id);revision=next;for(const [id,e]of assets){e.document=keep.has(id);if(e.document)e.transient=false;}await Promise.all([...assets.keys()].map(collect));},
  finish,abandon,
  async reset(){await Promise.all([...jobs.keys()].map(id=>abandon(id)));for(const e of assets.values()){e.document=false;e.transient=false;}await Promise.all([...assets.keys()].map(collect));revision=-1;},
 };
}
module.exports={createOwnership};
