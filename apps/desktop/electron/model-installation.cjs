const {setTimeout:delay}=require('node:timers/promises');
const {classifyError}=require('./diagnostic-runner.cjs');
const pending=new Set(['waiting','downloading','installing','verifying','probing','cancelling','deleting']);
const generative=model=>['mlx','torch-cpu'].includes(model.runtime);
const installationComplete=model=>generative(model)?model.state==='installed'&&model.verified_manifest===true:model.state==='ready';
const needsInstallation=model=>model.published&&!installationComplete(model);
async function installModel({model,api,signal,record,onProgress,setActive,now=Date.now,sleep=delay,timeoutMs=60*60*1000}){
 const id=`install-${model.id}`,name=`${model.name} kurulumu`,began=now();let cancelled=false;
 const deadline=AbortSignal.timeout(timeoutMs);
 const requestSignal=()=>AbortSignal.any([signal,deadline,AbortSignal.timeout(30000)]);
 const cancel=async()=>{if(cancelled)return;cancelled=true;await api(`/models/${model.id}/cancel`,{method:'POST',signal:AbortSignal.timeout(30000)});};
 const check=()=>{if(deadline.aborted)throw Object.assign(new Error('Kurulum bir saat içinde tamamlanamadı.'),{name:'TimeoutError'});if(signal.aborted)throw Object.assign(new Error('cancelled'),{name:'AbortError'});};
 setActive(model.id);record({id,name,status:'running'});
 try{
  check();await api(`/models/${model.id}/${model.state==='installed'?'probe':'install'}`,{method:'POST',signal:requestSignal()});
  while(true){
   check();const current=(await (await api('/models',{signal:requestSignal()})).json()).models.find(m=>m.id===model.id);check();
   if(!current)throw new Error('Model bulunamadı.');
   onProgress(`${model.name}: ${current.state} · ${Math.round((current.downloaded_bytes||0)/1024**2)} MiB`);
   if(installationComplete(current)||!pending.has(current.state)){
    record({id,name,status:installationComplete(current)?'passed':current.state==='cancelled'?'cancelled':'failed',detail:current.error?.message});break;
   }
   if(now()-began>timeoutMs){await cancel();throw Object.assign(new Error('Kurulum bir saat içinde tamamlanamadı.'),{name:'TimeoutError'});}
   await sleep(500,undefined,{signal:requestSignal()});
  }
 }catch(error){if(signal.aborted||deadline.aborted||error.name==='TimeoutError')await cancel().catch(()=>{});record({id,name,status:signal.aborted?'cancelled':classifyError(error),detail:error.message});}
 finally{setActive(undefined);}
}
module.exports={installationComplete,needsInstallation,installModel};
