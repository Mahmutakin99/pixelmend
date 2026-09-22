const {contextBridge, ipcRenderer} = require('electron');
contextBridge.exposeInMainWorld('diagnostics', {
  state:()=>ipcRenderer.invoke('diagnostics:state'),
  start:options=>ipcRenderer.invoke('diagnostics:start',options),
  cancel:()=>ipcRenderer.invoke('diagnostics:cancel'),
  finish:notes=>ipcRenderer.invoke('diagnostics:finish',notes),
  reveal:()=>ipcRenderer.invoke('diagnostics:reveal'),
  onState:callback=>{ipcRenderer.on('diagnostics:update',(_event,state)=>callback(state));},
});
