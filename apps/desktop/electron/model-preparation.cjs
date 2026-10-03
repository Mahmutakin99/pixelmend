const {setTimeout:delay} = require('node:timers/promises');
const preparing = new Set(['waiting','verifying','probing','cancelling']);

// Diagnostics require settled observations; ordinary editing does not.
async function waitForModelPreparation({api,onProgress=()=>{},signal,timeoutMs=180000,
  now=Date.now,sleep=delay}) {
  const deadline=now()+timeoutMs;
  let snapshot={models:[]};
  while(true) {
    signal?.throwIfAborted();
    const remaining=deadline-now();
    if(remaining<=0) throw Object.assign(new Error('Model hazırlığı 180 saniye içinde tamamlanamadı.'),
      {name:'TimeoutError',models:snapshot.models});
    const timeout=AbortSignal.timeout(Math.ceil(remaining));
    try {
      snapshot=await (await api('/models',{signal:signal ? AbortSignal.any([signal,timeout]) : timeout})).json();
    } catch(error) {
      error.models=snapshot.models;
      throw error;
    }
    onProgress(snapshot);
    if(!snapshot.models.some(model=>preparing.has(model.state))) return snapshot;
    await sleep(Math.min(250,remaining),undefined,{signal});
  }
}
module.exports={waitForModelPreparation};
