const {setTimeout: delay} = require('node:timers/promises');
const algorithms = {'lama':'lama', 'migan-512-places2':'migan_512_places2', 'realesrgan-x4plus':'realesrgan_x4plus','realesrgan-general-x4v3':'realesrgan_general_x4v3'};
function classifyError(error) {
  if (error.name === 'AbortError') return 'cancelled';
  if (error.name === 'TimeoutError') return 'timeout';
  if (['memory_limit','disk_full','insufficient_memory','insufficient_disk','result_budget','adaptive_limit','intermediate_limit'].includes(error.code)) return 'insufficient_resources';
  return 'failed';
}
function modelCases(models) {
  return models.flatMap(model => {
    const base = {id:`model-${model.id}`,name:model.name,modelId:model.id,algorithm:algorithms[model.id]};
    if (!algorithms[model.id] || model.state === 'unavailable') return [{...base,status:'unsupported',detail:'Bu sürümde doğrulanmış model entegrasyonu yok.'}];
    if (model.state !== 'ready') return [{...base,status:model.state === 'error' ? 'failed' : 'not_installed',detail:model.error?.message || 'Model kurulu ve sınanmış değil.'}];
    return (model.operation === 'upscale' ? [1,2] : [1]).map(scale => ({...base,
      id:`${base.id}-auto-${scale}`,name:`${model.name} · ${scale}× · Otomatik`,scale,provider:'automatic'}))
      .concat([{...base,id:`${base.id}-cpu`,name:`${model.name} · CPU`,scale:1,provider:'CPUExecutionProvider'}]);
  });
}
async function runCases(cases, {signal, report, execute, onProgress=()=>{}}) {
  for (const c of cases) report.record({...c,status:c.status || 'pending'});
  for (const c of cases) {
    if (c.status) continue;
    if (signal.aborted) { report.record({...c,status:'cancelled'}); continue; }
    const started = performance.now();
    report.record({...c,status:'running'}); onProgress(c.name || c.id);
    try {
      const result = await execute(c);
      report.record({...c,...result,status:result?.status || 'passed',durationMs:performance.now()-started});
    } catch (error) {
      report.record({...c,status:classifyError(error),detail:String(error.message),durationMs:performance.now()-started});
      if (error.fatal) throw error;
    }
  }
}

async function runDiagnostics({api, report, models, signal, onProgress, timeoutMs=30*60*1000,
  fixture:inputFixture, cases:inputCases, fixtureName='synthetic'}) {
  const json = async (route, options) => (await api(route, options)).json();
  const fixture = inputFixture || await json('/diagnostics/fixture',{method:'POST'});
  report.metadata({fixture:{version:fixture.fixture_version,width:fixture.width,height:fixture.height,description:fixture.description},
    timingNote:'Startup model probes may already have warmed sessions. Per-case elapsed time includes queue, processing and validation; this is not a cold-start benchmark.'});
  report.artifact(`gorseller/source-${fixtureName}.png`, Buffer.from(await (await api(`/assets/${fixture.asset_id}/export?format=PNG`)).arrayBuffer()));
  const cases = inputCases || [
    {id:'opencv',name:'Klasik nesne silme · maske ve alfa',algorithm:'opencv_telea',scale:1},
    {id:'lanczos',name:'Standart büyütme · ölçüler ve alfa',algorithm:'lanczos',scale:2},
    ...modelCases(models),
    {id:'cancel',name:'İptal · sıradaki işin durdurulması',algorithm:'lanczos',scale:2,cancel:true},
    {id:'after-cancel',name:'İptal sonrasında yeni işlem',algorithm:'lanczos',scale:1},
  ];
  await runCases(cases,{signal,report,onProgress,execute:async c => {
    const job = await json('/diagnostics/jobs',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({asset_id:fixture.asset_id,algorithm:c.algorithm,scale:c.scale,provider:c.provider || 'automatic',cancel_immediately:!!c.cancel})});
    const start = performance.now(); let cancelled=false, timedOut=false, maxRss=0, rssComplete=true, state;
    try {
      while (true) {
        if ((signal.aborted || c.cancel || performance.now()-start > timeoutMs) && !cancelled) {
          timedOut = !signal.aborted && !c.cancel;
          await json(`/jobs/${job.job_id}/cancel`,{method:'POST'});cancelled=true;
        }
        state = await json(`/jobs/${job.job_id}`);
        const runtime = await json('/diagnostics/runtime');
        maxRss = Math.max(maxRss,runtime.process_tree_rss_bytes); rssComplete &&= runtime.process_tree_complete;
        if (['completed','failed','cancelled'].includes(state.status)) break;
        // Stop scheduling work if a native operation does not honor cancellation.
        // The host shuts down only this diagnostic sidecar and preserves checkpoints.
        if (performance.now()-start > timeoutMs+60_000) throw Object.assign(new Error('Motor iptal isteğinden sonra yanıt vermedi.'),{name:'TimeoutError',fatal:true});
        await delay(250);
      }
      if (timedOut) throw Object.assign(new Error('İşlem süre sınırını aştı; iptal edildi.'),{name:'TimeoutError'});
      if (signal.aborted) throw Object.assign(new Error('Kullanıcı testi iptal etti.'),{name:'AbortError'});
      if (c.cancel) {
        if (state.status === 'cancelled') return {detail:'İş iptal edildi; sonuç yayımlanmadı.'};
        if (state.status === 'completed') return {status:'incomplete',detail:'İş, iptal isteğinden önce tamamlandı; bu koşuda iptal doğrulanamadı.'};
      }
      if (state.status !== 'completed') throw Object.assign(new Error(state.error?.message || `İş sonucu: ${state.status}`),{code:state.error?.code});
      const checked = await json(`/diagnostics/jobs/${job.job_id}/check`);
      const bytes = Buffer.from(await (await api(`/jobs/${job.job_id}/results/${state.result_ids[0]}?format=PNG`)).arrayBuffer());
      if (bytes.subarray(0,8).toString('hex') !== '89504e470d0a1a0a') throw new Error('PNG çıktısı geçersiz.');
      report.artifact(`gorseller/${c.id}.png`,bytes);
      return {checks:checked, sampledEngineTreePeakRssBytes:maxRss, memorySampleComplete:rssComplete,
        detail:`${checked.width} × ${checked.height}; alfa${checked.unmasked_pixels_preserved === true ? ' ve maske dışı pikseller' : ''} korundu. Sağlayıcı: ${state.provider || 'CPU'}.`};
    } finally {
      if (['completed','failed','cancelled'].includes(state?.status)) await api(`/jobs/${job.job_id}`,{method:'DELETE'});
    }
  }});
  await api(`/assets/${fixture.asset_id}`,{method:'DELETE'});
}
module.exports = {classifyError, modelCases, runCases, runDiagnostics};
