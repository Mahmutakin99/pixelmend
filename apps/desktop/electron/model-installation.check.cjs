const test=require('node:test'),assert=require('node:assert/strict');
test('verified installed generative packages are successful and need no download',()=>{
 const {installationComplete,needsInstallation}=require('./model-installation.cjs');
 const model={published:true,runtime:'mlx',state:'installed',verified_manifest:true};
 assert.equal(installationComplete(model),true);assert.equal(needsInstallation(model),false);
 assert.equal(needsInstallation({...model,verified_manifest:false}),true);
 assert.equal(installationComplete({state:'ready'}),true);
});
for(const state of ['failed','error','cancelled','absent'])test(`installation terminates on ${state}`,async()=>{
 const {installModel}=require('./model-installation.cjs'),calls=[],records=[];
 await installModel({model:{id:'m',name:'M'},signal:new AbortController().signal,api:async route=>{calls.push(route);return {json:async()=>({models:[{id:'m',state}]})};},record:r=>records.push(r),onProgress:()=>{},setActive:()=>{}});
 assert.equal(records.at(-1).status,state==='cancelled'?'cancelled':'failed');assert.equal(calls.filter(x=>x==='/models').length,1);
});
test('cancelled installation cancels once and immediately ends polling',async()=>{
 const {installModel}=require('./model-installation.cjs'),controller=new AbortController(),calls=[],records=[];
 await installModel({model:{id:'m',name:'M'},signal:controller.signal,api:async route=>{calls.push(route);if(route.endsWith('/install'))controller.abort();return {json:async()=>({models:[]})};},record:r=>records.push(r),onProgress:()=>{},setActive:()=>{}});
 assert.equal(records.at(-1).status,'cancelled');assert.equal(calls.filter(x=>x.endsWith('/cancel')).length,1);assert.ok(!calls.includes('/models'));
});
