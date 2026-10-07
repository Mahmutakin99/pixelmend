const test=require('node:test'),assert=require('node:assert/strict');
test('document history and active export pins protect assets; release clears previews',async()=>{
 const {createOwnership}=require('./asset-ownership.cjs'),calls=[],sources=new Map();
 const owner=createOwnership(async(route)=>{calls.push(route);return {json:async()=>({status:'completed'})};},sources);
 const a='a'.repeat(32),b='b'.repeat(32);owner.adoptAsset(a);owner.adoptAsset(b);sources.set(`asset/${a}`,new ArrayBuffer(1));
 await owner.setDocumentAssets(1,[a]);await owner.disposeAsset(b);assert.ok(calls.includes(`/assets/${b}`));
 const release=owner.pin([a]);await owner.setDocumentAssets(2,[]);assert.ok(!calls.includes(`/assets/${a}`));
 await release();assert.ok(calls.includes(`/assets/${a}`));assert.equal(sources.size,0);
 await owner.disposeAsset(a);assert.equal(calls.filter(x=>x===`/assets/${a}`).length,1);
});
test('stale document updates cannot unpin newer assets and ordinary jobs are deleted',async()=>{
 const {createOwnership}=require('./asset-ownership.cjs'),calls=[],sources=new Map();
 const owner=createOwnership(async(route)=>{calls.push(route);return {json:async()=>({status:'completed'})};},sources);
 const a='a'.repeat(32),j='b'.repeat(32);owner.adoptAsset(a);await owner.setDocumentAssets(4,[a]);await owner.setDocumentAssets(3,[]);
 assert.ok(!calls.includes(`/assets/${a}`));owner.adoptJob(j);sources.set(`result/${j}/r`,Buffer.from('x'));
 await owner.finish(j);assert.ok(calls.includes(`/jobs/${j}`));assert.equal(sources.size,0);
 await assert.rejects(owner.disposeAsset('c'.repeat(32)));
});

test('reset preserves a fresh renderer asset while old cleanup is pending',async()=>{
 const {createOwnership}=require('./asset-ownership.cjs');let unblock,entered;
 const started=new Promise(r=>entered=r),pending=new Promise(r=>unblock=r),deleted=[];
 const old='a'.repeat(32),fresh='b'.repeat(32),job='c'.repeat(32);
 const owner=createOwnership(async(route,options)=>{if(route===`/jobs/${job}`&&options?.method==='DELETE'){entered();await pending;}if(route.startsWith('/assets/')&&options?.method==='DELETE')deleted.push(route);return {json:async()=>({status:'completed'})};},new Map());
 owner.adoptAsset(old);owner.adoptJob(job);const resetting=owner.reset();await started;
 owner.adoptAsset(fresh);await owner.setDocumentAssets(1,[fresh]);unblock();await resetting;
 owner.requireAsset(fresh);assert.ok(!deleted.includes(`/assets/${fresh}`));assert.ok(deleted.includes(`/assets/${old}`));
});
test('reset waits for old IPC work and releases late adoptions; new work waits for cleanup',async()=>{
 const {createOwnership}=require('./asset-ownership.cjs');let unblock,entered;
 const started=new Promise(r=>entered=r),pending=new Promise(r=>unblock=r),deleted=[];
 const old='a'.repeat(32),fresh='b'.repeat(32),owner=createOwnership(async(route)=>{deleted.push(route);return {json:async()=>({status:'completed'})};},new Map());
 const operation=owner.run(async()=>{entered();await pending;owner.adoptAsset(old);});await started;
 const resetting=owner.reset();let newRan=false;const next=owner.run(()=>{newRan=true;owner.adoptAsset(fresh);});await Promise.resolve();assert.equal(newRan,false);
 unblock();await operation;await resetting;await next;assert.ok(deleted.includes(`/assets/${old}`));owner.requireAsset(fresh);
});
test('missing terminal jobs do not abort remaining reset cleanup',async()=>{
 const {createOwnership}=require('./asset-ownership.cjs'),calls=[];
 const a='a'.repeat(32),j='b'.repeat(32),owner=createOwnership(async(route)=>{calls.push(route);if(route.startsWith('/jobs/'))throw Object.assign(new Error('not found'),{httpStatus:404});return {};},new Map());
 owner.adoptAsset(a);owner.adoptJob(j,[a]);await owner.reset();assert.ok(calls.includes(`/assets/${a}`));
});

test('reset also retires IPC work queued immediately before reload',async()=>{
 const {createOwnership}=require('./asset-ownership.cjs'),deleted=[],a='a'.repeat(32);
 const owner=createOwnership(async route=>{deleted.push(route);return {};},new Map());
 const work=owner.run(()=>owner.adoptAsset(a));const reset=owner.reset();await work;await reset;
 assert.ok(deleted.includes(`/assets/${a}`));
});
