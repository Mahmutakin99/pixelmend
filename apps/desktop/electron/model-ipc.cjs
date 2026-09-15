const MODEL_IDS = new Set(['lama', 'realesrgan-x4plus']);
const ACTIONS = new Set(['install', 'cancel', 'retry', 'probe', 'delete']);

// Only the main process chooses routes and algorithms; no URL or path crosses the bridge.
function modelRoute(id, action) {
  if (!MODEL_IDS.has(id) || !ACTIONS.has(action)) throw new Error('Geçersiz model işlemi');
  return {route:`/models/${id}${action === 'delete' ? '' : `/${action}`}`, method:action === 'delete' ? 'DELETE' : 'POST'};
}
function jobForm(payload, policy = {}) {
  if (!payload || !['remove', 'upscale'].includes(payload.operation) || !/^[a-f0-9]{32}$/.test(payload.assetId)) throw new Error('Geçersiz işlem');
  const upscale = payload.operation === 'upscale';
  const method = payload.upscaleMethod ?? 'lanczos';
  if (!['ai','lanczos'].includes(method)) throw new Error('Geçersiz büyütme yöntemi');
  const form = new FormData();
  form.append('asset_id', payload.assetId);
  form.append('algorithms', JSON.stringify([upscale ? method === 'ai' ? 'realesrgan_x4plus' : 'lanczos' : 'lama']));
  form.append('scale', upscale ? '2' : '1');
  if (upscale) {
    const {targetWidth:w, targetHeight:h} = payload;
    const limit = policy.max_output_pixels ?? 200_000_000;
    if (!Number.isSafeInteger(w) || !Number.isSafeInteger(h) || w < 1 || h < 1 || w*h > limit) throw new Error(`Geçersiz çıktı ölçüsü (en fazla ${limit/1e6} MP)`);
    form.append('target_width', String(w));form.append('target_height', String(h));
  }
  if (payload.mask) form.append('mask', new Blob([Buffer.from(payload.mask, 'base64')]), 'mask.png');
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
  ipcMain.handle('pixelmend:model-action',async (event,id,action)=>{requireSender(event);const {route,method}=modelRoute(id,action);return (await api(route,{method})).json();});
  ipcMain.on('pixelmend:models-subscribe',event=>{if(authorized(event.sender))events.subscribe(event.sender);});
  ipcMain.on('pixelmend:models-unsubscribe',event=>{if(authorized(event.sender))events.unsubscribe(event.sender);});
  return events;
}
module.exports = {modelRoute, jobForm, createModelEvents, registerModelIpc};
