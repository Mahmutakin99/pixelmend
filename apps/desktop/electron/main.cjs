const { app, BrowserWindow, dialog, ipcMain, protocol } = require('electron');
const { spawn } = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
let engine; let token; const sources = new Map();
function request(route, options={}) { return fetch(`http://127.0.0.1:${engine.port}${route}`, { ...options, headers: {'X-PixelMend-Token': token, ...(options.headers || {})} }); }
async function api(route, options={}) { const response = await request(route, options); if (!response.ok) { let detail = `Motor hatası (${response.status})`; try { detail = (await response.json()).detail || detail; } catch {} throw new Error(detail); } return response; }
async function startEngine() {
  token = crypto.randomBytes(32).toString('hex');
  const executable = app.isPackaged ? path.join(process.resourcesPath, 'engine', 'pixelmend-engine') : path.join(__dirname, '../../../engine/.venv/bin/python');
  const args = app.isPackaged ? [] : ['-m', 'pixelmend_engine'];
  engine = spawn(executable, args, {env: {...process.env, PIXELMEND_SESSION_TOKEN: token}, stdio: ['ignore', 'pipe', 'pipe']});
  const line = await new Promise((resolve, reject) => { let buf=''; engine.stdout.on('data', d => { buf += d; const i=buf.indexOf('\n'); if(i>=0) resolve(buf.slice(0,i)); }); engine.once('error', reject); setTimeout(() => reject(new Error('Engine startup timed out')), 15000); });
  engine.port = JSON.parse(line).port;
  await api('/health');
}
function createWindow() { const window = new BrowserWindow({width: 1320, height: 900, minWidth: 760, minHeight: 600, webPreferences: {preload:path.join(__dirname,'preload.cjs'), contextIsolation:true, sandbox:true, nodeIntegration:false}}); window.loadFile(path.join(__dirname,'../dist/index.html')); return window; }
app.whenReady().then(async () => { protocol.handle('pixelmend', async requestUrl => { const key = requestUrl.url.replace('pixelmend://',''); const value=sources.get(key); return new Response(value || '', {status:value ? 200 : 404, headers:{'Content-Type':'image/png'}}); }); await startEngine(); const window=createWindow();
 ipcMain.handle('pixelmend:open-image', async () => { const result=await dialog.showOpenDialog(window,{properties:['openFile'],filters:[{name:'Images',extensions:['png','jpg','jpeg','webp','tif','tiff']}]}); if(result.canceled) return null; const form=new FormData(); form.append('image', new Blob([fs.readFileSync(result.filePaths[0])]), path.basename(result.filePaths[0])); const asset=await (await api('/assets',{method:'POST',body:form})).json(); const preview=await (await api(`/assets/${asset.asset_id}/preview`)).arrayBuffer(); sources.set(`asset/${asset.asset_id}`,preview); return {...asset, preview:`pixelmend://asset/${asset.asset_id}`}; });
 ipcMain.handle('pixelmend:start-job', async (_e, payload) => { const form=new FormData(); form.append('asset_id',payload.assetId); form.append('algorithms',JSON.stringify(payload.algorithms)); form.append('scale',String(payload.scale || 1)); if(payload.mask) form.append('mask',new Blob([Buffer.from(payload.mask,'base64')]),'mask.png'); return (await api('/jobs',{method:'POST',body:form})).json(); });
 ipcMain.handle('pixelmend:job', async (_e,id) => (await api(`/jobs/${id}`)).json()); ipcMain.handle('pixelmend:cancel',async(_e,id)=>(await api(`/jobs/${id}/cancel`,{method:'POST'})).json());
 ipcMain.handle('pixelmend:result', async (_e,j,r,f='PNG') => { const bytes=await (await api(`/jobs/${j}/results/${r}?format=${f}`)).arrayBuffer(); const key=`result/${j}/${r}`; sources.set(key,bytes); return `pixelmend://${key}`; });
 ipcMain.handle('pixelmend:save', async (_e,j,r,f='PNG') => { const save=await dialog.showSaveDialog(window,{defaultPath:`PixelMend.${f.toLowerCase()}`}); if(save.canceled)return null; const bytes=await (await api(`/jobs/${j}/results/${r}?format=${f}`)).arrayBuffer(); fs.writeFileSync(save.filePath,Buffer.from(bytes)); return save.filePath; }); });
app.on('window-all-closed',()=>app.quit()); app.on('before-quit',()=>engine?.kill('SIGTERM'));
