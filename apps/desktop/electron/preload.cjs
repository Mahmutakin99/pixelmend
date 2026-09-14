const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('pixelmend', {
  openImage: () => ipcRenderer.invoke('pixelmend:open-image'),
  startJob: (payload) => ipcRenderer.invoke('pixelmend:start-job', payload),
  job: (id) => ipcRenderer.invoke('pixelmend:job', id),
  result: (jobId, resultId, format) => ipcRenderer.invoke('pixelmend:result', jobId, resultId, format),
  save: (jobId, resultId, format) => ipcRenderer.invoke('pixelmend:save', jobId, resultId, format),
  cancel: (id) => ipcRenderer.invoke('pixelmend:cancel', id),
  onJob: (callback) => { const fn = (_event, value) => callback(value); ipcRenderer.on('pixelmend:job-event', fn); return () => ipcRenderer.removeListener('pixelmend:job-event', fn); }
});
