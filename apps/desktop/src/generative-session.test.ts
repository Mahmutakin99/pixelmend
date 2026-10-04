import {it,expect,vi} from 'vitest';
import {GenerativeSession} from './generative-session';
import type {DesktopBridge,GenerativeRequest} from './bridge';
const request:GenerativeRequest={operation:'text_to_image',prompt:'Bir kedi.',promptLanguage:'tr',profile:'low-resource',aspect:'square'};
function fixture(){
 const bridge={generativePreflight:vi.fn(async()=>({ready:true,seed:7})),startGenerativeJob:vi.fn(async(_request:GenerativeRequest)=>({job_id:'j',status:'queued',result_ids:[]})),
 job:vi.fn(async()=>({job_id:'j',status:'completed',result_ids:['r'],result_details:[{operation:'text_to_image',model_id:'klein',model_revision:'a'.repeat(40),seed:7,profile:'low-resource',original_prompt:'Bir kedi.',used_prompt:'A cat.',translated_prompt:'A cat.'}]})),
 continueResult:vi.fn(async()=>({asset_id:'a',preview:'pixelmend://asset/a',width:512,height:512})),disposeAsset:vi.fn(async()=>{}),disposeGenerativeJob:vi.fn(async()=>{}),cancel:vi.fn(async()=>{})};
 return {bridge,session:new GenerativeSession(bridge as unknown as DesktopBridge)};
}
it('previews without applying and frees the previous candidate before regeneration',async()=>{
 const {bridge,session}=fixture();await session.start(request);
 expect(session.getSnapshot().candidate?.info.seed).toBe(7);
 expect(bridge.startGenerativeJob.mock.calls[0][0]).toEqual({...request,seed:7});
 await session.start(request);expect(bridge.disposeAsset).toHaveBeenCalledWith('a');
 const taken=session.take();expect(taken?.asset.asset_id).toBe('a');expect(session.getSnapshot().candidate).toBeUndefined();
 await session.close();expect(bridge.disposeAsset).toHaveBeenCalledTimes(1);
});
it('preflight failure starts no model and exposes its specific reason',async()=>{
 const {bridge,session}=fixture();bridge.generativePreflight.mockResolvedValue({ready:false,seed:7,reason:{code:'memory_insufficient',message:'Bellek yetersiz.'}} as never);
 await session.start(request);expect(bridge.startGenerativeJob).not.toHaveBeenCalled();expect(session.getSnapshot().error).toBe('Bellek yetersiz.');
});
it('cancellation appears before IPC responds and releases terminal jobs',async()=>{
 const {bridge,session}=fixture();let resolve:any;bridge.job.mockImplementation(()=>new Promise(r=>{resolve=r}));
 const pending=session.start(request);await vi.waitFor(()=>expect(resolve).toBeDefined());
 await session.cancel();expect(session.getSnapshot().phase).toBe('İptal bekleniyor…');
 resolve({job_id:'j',status:'cancelled',result_ids:[]});await pending;
 expect(bridge.disposeGenerativeJob).toHaveBeenCalledWith('j');expect(session.getSnapshot().busy).toBe(false);
});
