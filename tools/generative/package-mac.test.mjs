import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
test('generative Mac package owns a separate alpha output and embeds no model weights or reports',()=>{
 const config=require('./electron-builder.cjs');assert.match(config.directories.output,/\.local-notes\/generative\/releases\/1\.1\.0-alpha\.1$/);
 const runtime=config.extraResources.find(r=>r.to==='generative-runtime');assert.match(runtime.from,/dist\/pixelmend-generative-runtime$/);
 assert.ok(config.extraResources.every(r=>!r.from.includes('/packages/')&&!r.from.includes('/quality/')&&!r.from.includes('/sessions/')));
 assert.equal(config.mac.hardenedRuntime,true);assert.equal(config.mac.notarize,false);assert.equal(config.mac.identity,process.env.CSC_NAME||null);
});

test('signing skips source/data resources and retains every native entry point',()=>{
 const config=require('./electron-builder.cjs');const ignored=file=>(config.mac.signIgnore||[]).some(pattern=>new RegExp(pattern).test(file));
 const base='/tmp/PixelMend.app/Contents/Resources/';
 for(const file of ['generative-runtime/_internal/transformers/models/seggpt/__init__.py','generative-runtime/_internal/tokenizer.json','generative-runtime/_internal/model/pos_emb.safetensors','engine/_internal/source.py'])assert(ignored(base+file),file);
 for(const file of ['generative-runtime/pixelmend-generative-runtime','generative-runtime/_internal/mlx/core.cpython-312-darwin.so','generative-runtime/_internal/libmlx.dylib','generative-runtime/_internal/Python.framework/Versions/3.12/Python','generative-runtime/_internal/Python.framework','generative-runtime/_internal/mlx/metal.metallib','engine/pixelmend-engine'])assert(!ignored(base+file),file);
 assert(!ignored('/tmp/PixelMend.app/Contents/MacOS/PixelMend'));
});
