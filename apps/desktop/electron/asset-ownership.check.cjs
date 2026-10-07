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
