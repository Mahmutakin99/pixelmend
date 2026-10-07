import type {AssetView,DesktopBridge,GenerationInfo,GenerativeRequest,JobSnapshot} from './bridge';
export type GenerativeCandidate={asset:AssetView;info:GenerationInfo};
export type GenerativeState={busy:boolean;phase:string;candidate?:GenerativeCandidate;error?:string;errorCode?:string};
const phases:Record<string,string>={waiting_for_memory:'Belleğin rahatlaması bekleniyor…',validating_models:'Model doğrulanıyor…',preparing_edit:'Seçili alan hazırlanıyor…',preparing_prompt:'Komut hazırlanıyor…',translating:'Komut çevriliyor…',loading_image_model:'Görsel modeli yükleniyor…',generating:'Görsel üretiliyor…',compositing:'Sonuç birleştiriliyor…',releasing_resources:'Kaynaklar bırakılıyor…'};
export function generationPhase(job:JobSnapshot){
 if(job.status==='cancelling')return 'İptal bekleniyor…';if(job.status==='queued')return 'İş sırada bekliyor…';
 const p=job.progress;if(p?.total===4&&p.phase==='generating')return `Görsel üretiliyor — ${p.completed}/4 adım`;
 return phases[p?.phase??'']??'İşlem sürüyor…';
}
export class GenerativeSession{
 private state:GenerativeState={busy:false,phase:''};private listeners=new Set<()=>void>();private jobId?:string;private closed=false;private cancelRequested=false;private disposal?:{candidate:GenerativeCandidate;promise:Promise<void>};
 constructor(private bridge:DesktopBridge){}
 getSnapshot=()=>this.state;
 subscribe=(callback:()=>void)=>{this.listeners.add(callback);return()=>{this.listeners.delete(callback);};};
 private update(value:Partial<GenerativeState>){if(this.closed)return;this.state={...this.state,...value};for(const fn of this.listeners)fn();}
 async discard(){
  if(this.disposal)return this.disposal.promise;
  const candidate=this.state.candidate;if(!candidate)return;
  // Remove the transferable handle immediately; disposal crosses async IPC.
  this.update({candidate:undefined,phase:'Önizlemeden vazgeçildi.'});
  const promise=Promise.resolve().then(()=>this.bridge.disposeAsset(candidate.asset.asset_id))
   .catch(error=>{this.update({candidate});throw error;})
   .finally(()=>{this.disposal=undefined;});
  this.disposal={candidate,promise};await promise;
 }
 take(){if(this.state.busy||this.disposal)return;const value=this.state.candidate;this.update({candidate:undefined});return value;}
 async start(request:GenerativeRequest){
  if(this.state.busy||this.closed)return;
  this.cancelRequested=false;
  this.update({busy:true,error:undefined,errorCode:undefined,phase:'İşlem kontrol ediliyor…'});
  const previousSeed=this.state.candidate?.info.seed;
  let adopted:AssetView|undefined;
  try{
   await this.discard();
   if(this.cancelRequested){this.update({phase:'İşlem iptal edildi.'});return;}
   const check=await this.bridge.generativePreflight(request);
   if(this.cancelRequested){this.update({phase:'İşlem iptal edildi.'});return;}
   this.update({phase:'Kontrol tamamlandı.'});
   if(!check.ready){this.update({errorCode:check.reason?.code});throw new Error(check.reason?.message??'İşlem başlatılamadı.');}
   if(this.closed)return;
   const seed=request.seed??(check.seed===previousSeed?(check.seed+1)>>>0:check.seed);
   this.update({phase:'Model hazırlanıyor; işlem zaman alabilir.'});
   const job=await this.bridge.startGenerativeJob({...request,seed});this.jobId=job.job_id;
   if(this.closed){await this.bridge.disposeGenerativeJob(job.job_id);this.jobId=undefined;return;}
   if(this.cancelRequested)await this.bridge.cancel(job.job_id);
   while(!this.closed){
    const current=await this.bridge.job(job.job_id);if(this.closed)break;
    this.update({phase:this.cancelRequested?'İptal bekleniyor…':generationPhase(current)});
    if(this.cancelRequested&&['completed','failed','cancelled'].includes(current.status)){
     await this.bridge.disposeGenerativeJob(job.job_id);this.jobId=undefined;this.update({phase:'İşlem iptal edildi.'});break;
    }
    if(current.status==='completed'){
     const detail=current.result_details?.[0];if(!detail?.operation||!detail.model_id||!detail.model_revision||detail.seed===undefined||!detail.profile||!detail.original_prompt||!detail.used_prompt||!detail.translated_prompt)throw new Error('Üretim bilgisi doğrulanamadı.');
     adopted=await this.bridge.continueResult(job.job_id,current.result_ids[0]);this.jobId=undefined;
     if(this.closed||this.cancelRequested){await this.bridge.disposeAsset(adopted.asset_id);adopted=undefined;this.update({phase:'İşlem iptal edildi.'});break;}
     this.update({candidate:{asset:adopted,info:detail as GenerationInfo},phase:'Önizleme hazır.'});break;
    }
    if(['failed','cancelled'].includes(current.status)){
     await this.bridge.disposeGenerativeJob(job.job_id);this.jobId=undefined;
     if(current.status==='failed'){this.update({errorCode:current.error?.code});throw new Error(current.error?.message??'Üretim tamamlanamadı.');}
     this.update({phase:'İşlem iptal edildi.'});break;
    }
    await new Promise(r=>setTimeout(r,150));
   }
  }catch(error){
   if(this.jobId){await this.bridge.disposeGenerativeJob(this.jobId).catch(()=>{});this.jobId=undefined;}
   this.update({phase:this.state.phase==='Kontrol tamamlandı.'?'Kontrol tamamlandı.':'İşlem tamamlanamadı.',error:error instanceof Error?error.message:'İşlem tamamlanamadı.'});
  }finally{this.update({busy:false});}
 }
 async cancel(){if(!this.state.busy)return;this.cancelRequested=true;this.update({phase:'İptal bekleniyor…'});if(this.jobId)await this.bridge.cancel(this.jobId);}
 async close(){
  this.closed=true;const disposal=this.disposal,candidate=this.state.candidate;
  if(this.jobId)await this.bridge.disposeGenerativeJob(this.jobId).catch(()=>{});
  if(disposal)await disposal.promise.catch(()=>this.bridge.disposeAsset(disposal.candidate.asset.asset_id).catch(()=>{}));
  if(candidate)await this.bridge.disposeAsset(candidate.asset.asset_id).catch(()=>{});
  this.listeners.clear();
 }
}
