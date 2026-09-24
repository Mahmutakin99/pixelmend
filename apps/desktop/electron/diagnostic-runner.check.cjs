const {test} = require('node:test');
const assert = require('node:assert/strict');
const {modelCases, runCases, classifyError} = require('./diagnostic-runner.cjs');

test('every catalog model receives a case, including unverified artifacts', () => {
  const cases = modelCases([{id:'lama',name:'LaMa',state:'ready',operation:'remove'},
    {id:'swin2sr-realworld-x4',name:'Swin2SR',state:'unavailable',operation:'upscale'},
    {id:'realesrgan-x4plus',name:'ESRGAN',state:'absent',operation:'upscale'}]);
  assert(cases.some(c=>c.modelId==='lama' && c.provider==='CPUExecutionProvider'));
  assert(cases.some(c=>c.modelId==='swin2sr-realworld-x4' && c.status==='unsupported'));
  assert(cases.some(c=>c.modelId==='realesrgan-x4plus' && c.status==='not_installed'));
});

test('cancellation preserves completed results and explicitly marks remaining cases', async () => {
  const controller = new AbortController(), results = new Map();
  let calls = 0;
  await runCases([{id:'one'}, {id:'two'}], {
    signal:controller.signal, report:{record:r=>results.set(r.id,r)},
    execute:async()=>{calls++;controller.abort();return {detail:'done'};},
  });
  assert.equal(calls,1);
  assert.equal(results.get('one').status,'passed');
  assert.equal(results.get('two').status,'cancelled');
});

test('an independent failure does not suppress later tests', async () => {
  const results = new Map();
  await runCases([{id:'one'}, {id:'two'}], {
    signal:new AbortController().signal, report:{record:r=>results.set(r.id,r)},
    execute:async c=>{if(c.id==='one')throw new Error('bad pixels'); return {};},
  });
  assert.equal(results.get('one').status,'failed');
  assert.equal(results.get('two').status,'passed');
  assert.equal(classifyError(new Error('unexpected model output')), 'failed');
  assert.equal(classifyError(Object.assign(new Error('capacity'),{code:'insufficient_memory'})), 'insufficient_resources');
});
