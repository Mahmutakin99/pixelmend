import type {GenerativePreflight} from './bridge';
export class GenerativeMemoryMonitor{
 private stopped=true;private timer?:ReturnType<typeof setTimeout>;
 constructor(private query:()=>Promise<GenerativePreflight>,private receive:(v:GenerativePreflight)=>void,private failed:(error:unknown)=>void=()=>{}){}
 start(){if(!this.stopped)return;this.stopped=false;void this.refresh();}
 stop(){this.stopped=true;clearTimeout(this.timer);}
 private async refresh(){
  try{const report=await this.query();if(!this.stopped)this.receive(report);}
  catch(error){if(!this.stopped)this.failed(error);}
  finally{if(!this.stopped)this.timer=setTimeout(()=>{void this.refresh();},2000);}
 }
}
export const memoryGiB=(bytes:number)=>`${(bytes/1024**3).toFixed(1)} GiB`;
export function memoryMessage(report:GenerativePreflight){
 if(report.ready&&report.waiting_for_memory)return 'Belleğin rahatlaması bekleniyor. İşlem otomatik devam edecek.';
 if(report.ready&&report.execution_mode==='adaptive')return 'Belleğe uyumlu üretim kullanılacak; işlem daha uzun sürebilir.';
 if(report.ready)return 'Şu an üretim için yeterli bellek var. Üretime devam edebilirsiniz.';
 if(report.reason?.code==='memory_insufficient')return `Üretim için ${memoryGiB(report.required_available_memory_bytes!)} gerekiyor; şu an ${memoryGiB(report.available_memory_bytes!)} kullanılabilir. Diğer uygulamaları kapatıp yeniden deneyin.`;
 return report.reason?.message??'';
}
