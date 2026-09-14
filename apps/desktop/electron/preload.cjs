const { contextBridge, ipcRenderer, webUtils } = require('electron');
contextBridge.exposeInMainWorld('pixelmend', {
  openImage: () => ipcRenderer.invoke('pixelmend:open-image'),
  startJob: payload => ipcRenderer.invoke('pixelmend:start-job', payload), job: id => ipcRenderer.invoke('pixelmend:job', id),
  result: (jobId, resultId) => ipcRenderer.invoke('pixelmend:result', jobId, resultId), cancel: id => ipcRenderer.invoke('pixelmend:cancel', id),
  continueResult: (jobId, resultId) => ipcRenderer.invoke('pixelmend:continue-result', jobId, resultId),
  saveRendered: (base64, format) => ipcRenderer.invoke('pixelmend:save-rendered', base64, format),
  exportSource: id => ipcRenderer.invoke('pixelmend:export-source', id),
  saveImage: payload => ipcRenderer.invoke('pixelmend:save-image', payload),
  settings: () => ipcRenderer.invoke('pixelmend:settings'), setSettings: value => ipcRenderer.invoke('pixelmend:set-settings', value),
  saveProject: (value, saveAs) => ipcRenderer.invoke('pixelmend:save-project', value, saveAs), openProject: () => ipcRenderer.invoke('pixelmend:open-project'),
  saveRecovery: value => ipcRenderer.invoke('pixelmend:save-recovery', value), recovery: () => ipcRenderer.invoke('pixelmend:recovery'), clearRecovery: () => ipcRenderer.invoke('pixelmend:clear-recovery'),
  recent: () => ipcRenderer.invoke('pixelmend:recent'), importDropped: file => ipcRenderer.invoke('pixelmend:import-dropped', webUtils.getPathForFile(file)),
  onAction: callback => { const fn = (_e, action) => callback(action); ipcRenderer.on('pixelmend:action', fn); return () => ipcRenderer.removeListener('pixelmend:action', fn); }
});
