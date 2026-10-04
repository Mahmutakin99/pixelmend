import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
test('generative Mac package owns a separate alpha output and embeds no model weights or reports',()=>{
 const config=require('./electron-builder.cjs');assert.match(config.directories.output,/\.local-notes\/generative\/releases\/1\.1\.0-alpha\.1$/);
 const runtime=config.extraResources.find(r=>r.to==='generative-runtime');assert.match(runtime.from,/dist\/pixelmend-generative-runtime$/);
 assert.ok(config.extraResources.every(r=>!r.from.includes('/packages/')&&!r.from.includes('/quality/')&&!r.from.includes('/sessions/')));
 assert.equal(config.mac.hardenedRuntime,true);assert.equal(config.mac.notarize,false);assert.equal(config.mac.identity,process.env.CSC_NAME||null);
});
