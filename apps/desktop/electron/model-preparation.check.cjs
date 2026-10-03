const test = require('node:test');
const assert = require('node:assert/strict');

test('diagnostics wait for every queued/verifying/probing model, not unpublished ones', async () => {
  const {waitForModelPreparation} = require('./model-preparation.cjs');
  const states = ['waiting','verifying','probing','ready'];
  const snapshots = states.map(state=>({models:[{id:'lama',state},{id:'sdxl',state:'unavailable'}]}));
  let calls=0;const progress=[];
  const result = await waitForModelPreparation({api:async()=>({json:async()=>snapshots[calls++]}),
    onProgress:snapshot=>progress.push(snapshot.models[0].state),sleep:async()=>{}});
  assert.deepEqual(progress,['waiting','verifying','probing','ready']);
  assert.equal(result.models[0].state,'ready');
});

test('preparation timeout includes latest models for a partial report', async () => {
  const {waitForModelPreparation} = require('./model-preparation.cjs');
  let time=0;
  await assert.rejects(waitForModelPreparation({api:async()=>({json:async()=>({models:[{id:'lama',state:'probing'}]})}),
    timeoutMs:10,now:()=>time,sleep:async()=>{time=11;}}), error=>
    error.name==='TimeoutError' && error.models[0].state==='probing');
});

test('model failure is terminal, and cancelled preparation never starts tests', async () => {
  const {waitForModelPreparation} = require('./model-preparation.cjs');
  const snapshot={models:[{id:'lama',state:'error'}]};
  assert.deepEqual(await waitForModelPreparation({api:async()=>({json:async()=>snapshot})}),snapshot);
  const controller=new AbortController();controller.abort();
  await assert.rejects(waitForModelPreparation({api:async()=>{throw new Error('must not request');},signal:controller.signal}), {name:'AbortError'});
});
