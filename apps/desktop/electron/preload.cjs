const { contextBridge, ipcRenderer, webUtils } = require('electron');
const modelListeners = new Set();
ipcRenderer.on('pixelmend:models-event', (_event, snapshot) => {
  for (const callback of modelListeners) callback(snapshot);
});
contextBridge.exposeInMainWorld('pixelmend', {
  generativeMemory: request => ipcRenderer.invoke('pixelmend:generative-memory', request),
  generativePreflight: request => ipcRenderer.invoke('pixelmend:generative-preflight', request),
  startGenerativeJob: request => ipcRenderer.invoke('pixelmend:start-generative-job', request),
  disposeAsset: id => ipcRenderer.invoke('pixelmend:dispose-asset', id),
  disposeGenerativeJob: id => ipcRenderer.invoke('pixelmend:dispose-generative-job', id),
  confirmClose: () => ipcRenderer.invoke('pixelmend:confirm-close'),
  capabilities: () => ipcRenderer.invoke('pixelmend:capabilities'),
  models: () => ipcRenderer.invoke('pixelmend:models'),
  modelAction: (id, action) => ipcRenderer.invoke('pixelmend:model-action', id, action),
  onModels: callback => {
    if (typeof callback !== 'function') throw new Error('Geçersiz model dinleyicisi');
    modelListeners.add(callback);
    if (modelListeners.size === 1) ipcRenderer.send('pixelmend:models-subscribe');
    return () => { modelListeners.delete(callback); if (!modelListeners.size) ipcRenderer.send('pixelmend:models-unsubscribe'); };
  },
  openImage: () => ipcRenderer.invoke('pixelmend:open-image'),
  startJob: payload => ipcRenderer.invoke('pixelmend:start-job', payload), job: id => ipcRenderer.invoke('pixelmend:job', id),
  result: (jobId, resultId) => ipcRenderer.invoke('pixelmend:result', jobId, resultId), cancel: id => ipcRenderer.invoke('pixelmend:cancel', id),
  continueResult: (jobId, resultId) => ipcRenderer.invoke('pixelmend:continue-result', jobId, resultId),
  renderAsset: payload => ipcRenderer.invoke('pixelmend:render-asset', payload),
  exportSource: id => ipcRenderer.invoke('pixelmend:export-source', id),
  saveImage: payload => ipcRenderer.invoke('pixelmend:save-image', payload),
  settings: () => ipcRenderer.invoke('pixelmend:settings'), setSettings: value => ipcRenderer.invoke('pixelmend:set-settings', value),
  saveProject: (value, saveAs) => ipcRenderer.invoke('pixelmend:save-project', value, saveAs), openProject: () => ipcRenderer.invoke('pixelmend:open-project'),
  saveRecovery: value => ipcRenderer.invoke('pixelmend:save-recovery', value), recovery: () => ipcRenderer.invoke('pixelmend:recovery'), clearRecovery: () => ipcRenderer.invoke('pixelmend:clear-recovery'),
  recent: () => ipcRenderer.invoke('pixelmend:recent'), importDropped: file => ipcRenderer.invoke('pixelmend:import-dropped', webUtils.getPathForFile(file)),
  onAction: callback => { const fn = (_e, action) => callback(action); ipcRenderer.on('pixelmend:action', fn); return () => ipcRenderer.removeListener('pixelmend:action', fn); }
});
