import {it,expect} from 'vitest';
import {observeModels} from './model-observer';
const deferred=()=>{let resolve!:(v:any)=>void;const promise=new Promise<any>(r=>resolve=r);return {promise,resolve};};
it('keeps newer SSE observations while capabilities finish later',async()=>{
 const model=deferred(),host=deferred(),seen:any[]=[],hosts:any[]=[];let event!:(s:any)=>void;
 const observer=observeModels({models:()=>model.promise,capabilities:()=>host.promise,onModels:fn=>{event=fn;return ()=>{};}},s=>seen.push(s),h=>hosts.push(h),()=>{});
 const refreshing=observer.refresh();model.resolve({models:[{state:'probing'}]});await Promise.resolve();event({models:[{state:'ready'}]});host.resolve({platform:'macos'});await refreshing;
 expect(seen.at(-1)[0].state).toBe('ready');expect(hosts).toHaveLength(1);observer.close();
});
it('ignores old refreshes and pending callbacks after unmount',async()=>{
 const a=deferred(),b=deferred(),hosts=[deferred(),deferred()],seen:any[]=[],caps:any[]=[],errors:string[]=[];let request=0,off=0;
 const observer=observeModels({models:()=>[a,b][request++].promise,capabilities:()=>hosts[request-1].promise,onModels:()=>()=>{off++;}},s=>seen.push(s),h=>caps.push(h),e=>errors.push(e));
 const one=observer.refresh(),two=observer.refresh();b.resolve({models:[{state:'ready'}]});hosts[1].resolve({new:true});await two;
 a.resolve({models:[{state:'probing'}]});hosts[0].resolve({old:true});await one;expect(seen).toEqual([[{state:'ready'}]]);expect(caps).toEqual([{new:true}]);
 observer.close();expect(off).toBe(1);await observer.refresh();expect(seen).toHaveLength(1);
});
