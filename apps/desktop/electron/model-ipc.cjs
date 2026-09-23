const MODEL_IDS = new Set(['lama', 'migan-512-places2', 'realesrgan-x4plus','realesrgan-general-x4v3']);
const UPSCALE_MODELS = {'realesrgan-x4plus':'realesrgan_x4plus','realesrgan-general-x4v3':'realesrgan_general_x4v3'};
const REMOVE_MODELS = {'lama':'lama', 'migan-512-places2':'migan_512_places2'};
const ACTIONS = new Set(['install-local', 'install', 'cancel', 'retry', 'probe', 'delete']);

// Only the main process chooses routes and algorithms; no URL or path crosses the bridge.
function modelRoute(id, action) {
  if (!MODEL_IDS.has(id) || !ACTIONS.has(action)) throw new Error('Geçersiz model işlemi');
  return {route:`/models/${id}${action === 'delete' ? '' : `/${action}`}`, method:action === 'delete' ? 'DELETE' : 'POST'};
}
function jobForm(payload, policy = {}, resourceMode = 'automatic') {
  if (!payload || !['remove', 'upscale'].includes(payload.operation) || !/^[a-f0-9]{32}$/.test(payload.assetId)) throw new Error('Geçersiz işlem');
  const upscale = payload.operation === 'upscale';
  const method = payload.upscaleMethod ?? 'lanczos';
  if (!['ai','lanczos'].includes(method)) throw new Error('Geçersiz büyütme yöntemi');
  const form = new FormData();
  form.append('asset_id', payload.assetId);
  const removeMethod = payload.removeMethod ?? 'lama';
  if (!['lama', 'opencv'].includes(removeMethod)) throw new Error('Geçersiz silme yöntemi');
  const modelId=payload.modelId ?? (upscale ? 'realesrgan-x4plus' : 'lama');
  if(upscale && method==='ai' && !Object.hasOwn(UPSCALE_MODELS,modelId) || !upscale && removeMethod==='lama' && !Object.hasOwn(REMOVE_MODELS,modelId))throw new Error('Geçersiz model seçimi');
  const usesAI=upscale ? method==='ai' : removeMethod==='lama';
  if(usesAI)form.append('model_id',modelId);
  const intent=payload.intent ?? 'resize';
  if(!['resize','preserve_size'].includes(intent) || intent==='preserve_size' && (!upscale || !usesAI))throw new Error('Geçersiz iyileştirme amacı');
  form.append('intent',intent);
  if (!['automatic', 'low-resource'].includes(resourceMode)) throw new Error('Geçersiz çalışma modu');
  form.append('resource_mode', resourceMode);
  form.append('algorithms', JSON.stringify([upscale ? method === 'ai' ? UPSCALE_MODELS[modelId] : 'lanczos' : removeMethod === 'lama' ? REMOVE_MODELS[modelId] : 'opencv_telea']));
  form.append('scale', upscale ? '2' : '1');
  if (upscale) {
    const {targetWidth:w, targetHeight:h} = payload;
    const limit = policy.max_output_pixels ?? 200_000_000;
    if (!Number.isSafeInteger(w) || !Number.isSafeInteger(h) || w < 1 || h < 1 || w*h > limit) throw new Error(`Geçersiz çıktı ölçüsü (en fazla ${limit/1e6} MP)`);
    form.append('target_width', String(w));form.append('target_height', String(h));
  }
  if (!upscale) {
    if (!Array.isArray(payload.selectionStrokes)) throw new Error('Geçersiz seçim çizimleri');
    form.append('selection_strokes', JSON.stringify(payload.selectionStrokes));
  }
  return form;
}

// A single authenticated stream serves all renderer listeners with bounded retry/backlog.
function createModelEvents(api) {
  const subscribers = new Map();
  let controller, task, retryTimer, releaseRetry, closed = false;
  const stop = () => { controller?.abort();clearTimeout(retryTimer);releaseRetry?.(); };
  const run = async () => {
    let failures = 0;
    while (!closed && subscribers.size) {
      controller = new AbortController();
      try {
        const response = await api('/models/events', {signal:controller.signal});
        const reader = response.body.getReader();
        const decoder = new TextDecoder();let buffer = '';
        try {
          while (!controller.signal.aborted) {
            const {done,value} = await reader.read();if (done) break;
            buffer += decoder.decode(value, {stream:true});
            if (buffer.length > 1_048_576) throw new Error('Model event too large');
            buffer = buffer.replace(/\r\n/g, '\n');
            let end;
            while ((end = buffer.indexOf('\n\n')) >= 0) {
              const frame = buffer.slice(0,end);buffer = buffer.slice(end+2);
              if (!frame.split('\n').some(line=>line === 'event: models')) continue;
              const data = frame.split('\n').filter(line=>line.startsWith('data:')).map(line=>line.slice(5).trimStart()).join('\n');
              const snapshot = JSON.parse(data);
              if (!Array.isArray(snapshot.models)) continue;
              failures = 0;
              for (const sender of subscribers.values()) if (!sender.isDestroyed()) sender.send('pixelmend:models-event', snapshot);
            }
          }
        } finally { await reader.cancel().catch(()=>{});reader.releaseLock(); }
      } catch { /* The next bounded reconnect also delivers a fresh model snapshot. */ }
      if (!closed && subscribers.size && !controller.signal.aborted) {
        const delay = Math.min(30000, 1000 * 2 ** Math.min(failures++, 5));
        await new Promise(resolve=>{releaseRetry=resolve;retryTimer=setTimeout(resolve,delay);});
        releaseRetry=undefined;
      }
    }
  };
  const start = () => { if (!task && !closed && subscribers.size) task=run().finally(()=>{task=undefined;if(subscribers.size&&!closed)start();}); };
  return {
    subscribe(sender) {
      if (closed || subscribers.has(sender.id)) return;
      subscribers.set(sender.id,sender);
      sender.once('destroyed',()=>{subscribers.delete(sender.id);if(!subscribers.size)stop();});
      start();
    },
    unsubscribe(sender) { subscribers.delete(sender.id);if(!subscribers.size)stop(); },
    close() { closed=true;subscribers.clear();stop(); },
  };
}
function registerModelIpc(ipcMain, api, authorized) {
  const events = createModelEvents(api);
  const requireSender = event => { if (!authorized(event.sender)) throw new Error('Geçersiz pencere'); };
  ipcMain.handle('pixelmend:capabilities',async event=>{requireSender(event);return (await api('/capabilities')).json();});
  ipcMain.handle('pixelmend:models',async event=>{requireSender(event);return (await api('/models')).json();});
  ipcMain.handle('pixelmend:model-action',async (event,id,action)=>{
    requireSender(event);const {route,method}=modelRoute(id,action);
    if (action === 'install-local') {
      const {dialog} = require('electron');
      const selection = await dialog.showOpenDialog({title:'Doğrulanmış ONNX modelini seçin', properties:['openFile'], filters:[{name:'ONNX',extensions:['onnx']}]});
      if (selection.canceled) return (await api('/models')).json();
      return (await api(route,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify({path:selection.filePaths[0]})})).json();
    }
    return (await api(route,{method})).json();
  });
  ipcMain.on('pixelmend:models-subscribe',event=>{if(authorized(event.sender))events.subscribe(event.sender);});
  ipcMain.on('pixelmend:models-unsubscribe',event=>{if(authorized(event.sender))events.unsubscribe(event.sender);});
  return events;
}
module.exports = {modelRoute, jobForm, createModelEvents, registerModelIpc};
