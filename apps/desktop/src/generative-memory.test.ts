import {it,expect,vi,afterEach} from 'vitest';
import {GenerativeMemoryMonitor,memoryMessage} from './generative-memory';
import type {GenerativePreflight} from './bridge';
afterEach(()=>vi.useRealTimers());
const report={ready:true,seed:1,width:512,height:512,profile:'low-resource',available_memory_bytes:8*1024**3,required_available_memory_bytes:7*1024**3} satisfies GenerativePreflight;
it('explains adaptive generation and waiting without calling admitted memory insufficient',()=>{
 expect(memoryMessage({...report,execution_mode:'adaptive',available_memory_bytes:4.2*1024**3})).toBe('Belleğe uyumlu üretim kullanılacak; işlem daha uzun sürebilir.');
 expect(memoryMessage({...report,waiting_for_memory:true,memory_pressure:'critical'})).toBe('Belleğin rahatlaması bekleniyor. İşlem otomatik devam edecek.');
});
it('refreshes idle memory every two seconds and stops when panel closes',async()=>{
 vi.useFakeTimers();const values:GenerativePreflight[]=[];let calls=0;
 const monitor=new GenerativeMemoryMonitor(async()=>{calls++;return report;},value=>values.push(value));
 monitor.start();await vi.advanceTimersByTimeAsync(0);expect(values).toEqual([report]);
 await vi.advanceTimersByTimeAsync(2000);expect(calls).toBe(2);
 monitor.stop();await vi.advanceTimersByTimeAsync(4000);expect(calls).toBe(2);
});
it('does not overlap slow queries or deliver results after closing',async()=>{
 vi.useFakeTimers();let release!:(v:GenerativePreflight)=>void;let calls=0;const values:GenerativePreflight[]=[];
 const monitor=new GenerativeMemoryMonitor(()=>{calls++;return new Promise(resolve=>{release=resolve;});},v=>values.push(v));
 monitor.start();await vi.advanceTimersByTimeAsync(6000);expect(calls).toBe(1);
 monitor.stop();release(report);await vi.advanceTimersByTimeAsync(4000);expect(values).toEqual([]);expect(calls).toBe(1);
});
it('reports required/current memory and a recovered admission without suggesting the same profile',()=>{
 const insufficient={...report,ready:false,available_memory_bytes:6*1024**3,reason:{code:'memory_insufficient',message:'Bellek yetersiz.'}};
 expect(memoryMessage(insufficient)).toContain('6.0 GiB');expect(memoryMessage(insufficient)).toContain('7.0 GiB');
 expect(memoryMessage(insufficient)).not.toContain('profilini seç');
 expect(memoryMessage(report)).toBe('Şu an üretim için yeterli bellek var. Üretime devam edebilirsiniz.');
});
