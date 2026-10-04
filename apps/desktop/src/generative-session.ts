import type {AssetView,DesktopBridge,GenerationInfo,GenerativeRequest,JobSnapshot} from './bridge';
export type GenerativeCandidate={asset:AssetView;info:GenerationInfo};
export type GenerativeState={busy:boolean;phase:string;candidate?:GenerativeCandidate;error?:string};
const phases:Record<string,string>={validating_models:'Model doğrulanıyor…',preparing_edit:'Seçili alan hazırlanıyor…',preparing_prompt:'Komut hazırlanıyor…',translating:'Komut çevriliyor…',loading_image_model:'Görsel modeli yükleniyor…',generating:'Görsel üretiliyor…',compositing:'Sonuç birleştiriliyor…',releasing_resources:'Kaynaklar bırakılıyor…'};
export function generationPhase(job:JobSnapshot){
 if(job.status==='cancelling')return 'İptal bekleniyor…';if(job.status==='queued')return 'İş sırada bekliyor…';
 const p=job.progress;if(p?.total===4&&p.phase==='generating')return `Görsel üretiliyor — ${p.completed}/4 adım`;
 return phases[p?.phase??'']??'İşlem sürüyor…';
}
export class GenerativeSession{
 private state:GenerativeState={busy:false,phase:''};private listeners=new Set<()=>void>();private jobId?:string;private closed=false;
 constructor(private bridge:DesktopBridge){}
 getSnapshot=()=>this.state;
 subscribe=(callback:()=>void)=>{this.listeners.add(callback);return()=>{this.listeners.delete(callback);};};
 private update(value:Partial<GenerativeState>){if(this.closed)return;this.state={...this.state,...value};for(const fn of this.listeners)fn();}
 async discard(){const candidate=this.state.candidate;if(candidate){await this.bridge.disposeAsset(candidate.asset.asset_id);this.update({candidate:undefined,phase:'Önizlemeden vazgeçildi.'});}}
 take(){const value=this.state.candidate;this.update({candidate:undefined});return value;}
 async start(request:GenerativeRequest){
  if(this.state.busy||this.closed)return;
  this.update({busy:true,error:undefined,phase:'İşlem kontrol ediliyor…'});
  let adopted:AssetView|undefined;
  try{
   await this.discard();const check=await this.bridge.generativePreflight(request);
   if(!check.ready)throw new Error(check.reason?.message??'İşlem başlatılamadı.');
   if(this.closed)return;
   const job=await this.bridge.startGenerativeJob({...request,seed:request.seed??check.seed});this.jobId=job.job_id;
   if(this.closed){await this.bridge.disposeGenerativeJob(job.job_id);this.jobId=undefined;return;}
   while(!this.closed){
    const current=await this.bridge.job(job.job_id);if(this.closed)break;
    this.update({phase:generationPhase(current)});
    if(current.status==='completed'){
     const detail=current.result_details?.[0];if(!detail?.operation||!detail.model_id||!detail.model_revision||detail.seed===undefined||!detail.profile||!detail.original_prompt||!detail.used_prompt||!detail.translated_prompt)throw new Error('Üretim bilgisi doğrulanamadı.');
     adopted=await this.bridge.continueResult(job.job_id,current.result_ids[0]);this.jobId=undefined;
     if(this.closed){await this.bridge.disposeAsset(adopted.asset_id);adopted=undefined;break;}
     this.update({candidate:{asset:adopted,info:detail as GenerationInfo},phase:'Önizleme hazır.'});break;
    }
    if(['failed','cancelled'].includes(current.status)){
     await this.bridge.disposeGenerativeJob(job.job_id);this.jobId=undefined;
     if(current.status==='failed')throw new Error(current.error?.message??'Üretim tamamlanamadı.');
     this.update({phase:'İşlem iptal edildi.'});break;
    }
    await new Promise(r=>setTimeout(r,150));
   }
  }catch(error){
   if(this.jobId){await this.bridge.disposeGenerativeJob(this.jobId).catch(()=>{});this.jobId=undefined;}
   this.update({error:error instanceof Error?error.message:'İşlem tamamlanamadı.'});
  }finally{this.update({busy:false});}
 }
 async cancel(){if(!this.jobId)return;this.update({phase:'İptal bekleniyor…'});await this.bridge.cancel(this.jobId);}
 async close(){this.closed=true;if(this.jobId)await this.bridge.disposeGenerativeJob(this.jobId).catch(()=>{});if(this.state.candidate)await this.bridge.disposeAsset(this.state.candidate.asset.asset_id).catch(()=>{});this.listeners.clear();}
}
