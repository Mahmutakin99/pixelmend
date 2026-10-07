import type {DesktopBridge} from './bridge';
import type {Capabilities,ModelView} from './models';
export function observeModels(bridge:Pick<DesktopBridge,'models'|'capabilities'|'onModels'>,models:(v:ModelView[])=>void,capabilities:(v:Capabilities)=>void,error:(v:string)=>void){
 let live=true,request=0,observation=0;
 const off=bridge.onModels(snapshot=>{if(live){observation++;models(snapshot.models);}});
 return {
  async refresh(){
   if(!live)return;
   const ownRequest=++request,ownObservation=++observation;
   const current=()=>live&&request===ownRequest;
   const results=await Promise.allSettled([
    bridge.models().then(snapshot=>{if(current()&&observation===ownObservation)models(snapshot.models);},cause=>{if(current()&&observation===ownObservation)error(`Model bilgileri alınamadı: ${String(cause)}`);throw cause;}),
    bridge.capabilities().then(host=>{if(current())capabilities(host);},cause=>{if(current())error(`Model bilgileri alınamadı: ${String(cause)}`);throw cause;})
   ]);
   if(current()&&results.every(r=>r.status==='fulfilled'))error('');
  },
  close(){if(!live)return;live=false;off();}
 };
}
