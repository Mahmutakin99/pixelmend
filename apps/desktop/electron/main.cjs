const { app, BrowserWindow, dialog, ipcMain, protocol, Menu } = require('electron');
const { spawn } = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const {jobForm, registerModelIpc} = require('./model-ipc.cjs');
const {engineCommand} = require('./engine-path.cjs');
const {registerGenerativeIpc,opaqueId} = require('./generative-ipc.cjs');
const {writeStreamAtomic} = require('./atomic-file.cjs');
const selfTest = process.argv.includes('--self-test');
const ownsApplication = process.env.PIXELMEND_CI_SMOKE === '1' || app.requestSingleInstanceLock({selfTest});
let diagnosticHost, diagnosticTemp;
if (selfTest) {
  diagnosticTemp = fs.mkdtempSync(path.join(require('node:os').tmpdir(), 'pixelmend-diagnostic-'));
  app.setPath('userData', path.join(diagnosticTemp, 'profile'));
  process.env.PIXELMEND_DIAGNOSTICS = '1';
  process.env.PIXELMEND_SESSIONS_DIR = path.join(diagnosticTemp, 'sessions');
}

if (process.env.PIXELMEND_CI_SMOKE === '1') {
  app.commandLine.appendSwitch('headless');
  app.commandLine.appendSwitch('disable-gpu');
}
let modelEvents;
let allowClose=false; let shutdownComplete=false; let shuttingDown=false;
let engine; let engineReady; let token; let mainWindow; let projectFile; let projectAssetId; const sources = new Map();
const settingsPath = () => path.join(app.getPath('userData'), 'settings.json');
const defaults = { language: 'tr', theme: 'system', maskColor: '#ff3b6b', maskOpacity: .42, zoomSensitivity: 1.5, removeModelTier: 'balanced', upscaleModelTier: 'balanced', performanceMode: 'automatic' };
const readSettings = () => { try { return {...defaults, ...JSON.parse(fs.readFileSync(settingsPath(), 'utf8'))}; } catch { return defaults; } };
const writeAtomic = (file, data) => { const tmp = `${file}.tmp`; fs.writeFileSync(tmp, data); fs.renameSync(tmp, file); };
function request(route, options={}) { return fetch(`http://127.0.0.1:${engine.port}${route}`, { signal:AbortSignal.timeout(30000), ...options, headers: {'X-PixelMend-Token': token, ...(options.headers || {})} }); }
async function engineApi(route, options={}) { const response = await request(route, options); if (!response.ok) { let detail = `Motor hatası (${response.status})`; try { detail = (await response.json()).detail || detail; } catch {} throw Object.assign(new Error(typeof detail === 'object' ? `${detail.code || 'engine'}: ${detail.message || JSON.stringify(detail)}` : detail), {code:detail?.code, httpStatus:response.status}); } return response; }
async function api(route, options={}) {
  await engineReady;
  if(shuttingDown || shutdownComplete) throw new Error('Motor kapanıyor.');
  return engineApi(route, options);
}
async function startEngine() {
  token = crypto.randomBytes(32).toString('hex');
  const {executable, args} = engineCommand({isPackaged:app.isPackaged, resourcesPath:process.resourcesPath, dirname:__dirname});
  engine = spawn(executable, args, {env: {...process.env, PIXELMEND_SESSION_TOKEN: token}, stdio: ['ignore', 'pipe', 'pipe']});
  engine.stderr.on('data', d => {
    if (diagnosticHost) {
      const previous = engine.diagnosticLog || '';
      engine.diagnosticLog = (previous + String(d).split(token).join('[REDACTED]')).slice(-64000);
    }
  });
  const line = await new Promise((resolve, reject) => {
    let buf='';
    const timeout=setTimeout(()=>{cleanup();reject(new Error('Engine startup timed out'));},30000);
    const failed=error=>{cleanup();reject(error);};
    const exited=()=>failed(new Error('Engine exited before startup'));
    const cleanup=()=>{clearTimeout(timeout);engine.stdout.off('data',data);engine.off('error',failed);engine.off('exit',exited);};
    const data=d=>{buf+=d;if(buf.length>65536)return failed(new Error('Invalid engine startup response'));const i=buf.indexOf('\n');if(i>=0){cleanup();resolve(buf.slice(0,i));}};
    engine.stdout.on('data',data);engine.once('error',failed);engine.once('exit',exited);
  });
  engine.stdout.resume();
  engine.port = JSON.parse(line).port;
  await engineApi('/health',{signal:AbortSignal.timeout(180000)});
}
async function stopEngine() {
  const child = engine;
  if (!child || child.exitCode !== null || child.signalCode !== null) return;
  // Windows signals terminate processes rather than running uvicorn's cleanup.
  // Use the authenticated server hook consistently on all platforms.
  if (child.port) {
    try { await engineApi('/shutdown',{method:'POST',signal:AbortSignal.timeout(3000)}); }
    catch { if(process.platform!=='win32')child.kill('SIGTERM'); }
  } else child.kill('SIGTERM');
  await new Promise(resolve => {
    if(child.exitCode!==null || child.signalCode!==null){resolve();return;}
    const timeout = setTimeout(resolve, 5000);
    child.once('exit', () => { clearTimeout(timeout); resolve(); });
  });
  if (child.exitCode === null && child.signalCode === null) throw new Error('sidecar did not stop');
}
async function drainEngine() {
  try { await stopEngine(); }
  catch(error) {
    console.error(error);
    const child=engine;
    if(child && child.exitCode===null && child.signalCode===null)
      await new Promise(resolve=>child.once('exit',resolve));
  }
}
async function runSmoke() {
  const health = await (await api('/health')).json();
  const capabilities = await (await api('/capabilities')).json();
  if (health.status !== 'ok' || !capabilities.policy) throw new Error('sidecar health or capabilities failed');
  // A tiny opaque PNG: the app's real main process submits the light OpenCV path
  // and reads a native PNG export without shipping a fixture image.
  const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAFUlEQVR4nGP8//8/AzbAhFV00EoAAFbUAw037MyjAAAAAElFTkSuQmCC', 'base64');
  const form = new FormData(); form.append('image', new Blob([png]), 'smoke.png');
  const asset = await (await api('/assets', {method:'POST', body:form})).json();
  const jobForm = new FormData();
  jobForm.append('asset_id', asset.asset_id); jobForm.append('algorithms', '["opencv_telea"]');
  jobForm.append('selection_strokes', JSON.stringify([{mode:'draw',points:[{x:4,y:4}],color:'#ff3b6b',opacity:1,size:2,hardness:1}]));
  const job = await (await api('/jobs', {method:'POST',body:jobForm})).json();
  let state;
  for (let attempt=0; attempt<100; attempt++) { state = await (await api(`/jobs/${job.job_id}`)).json(); if (['completed','failed','cancelled'].includes(state.status)) break; await new Promise(resolve=>setTimeout(resolve, 50)); }
  if (state?.status !== 'completed') throw new Error(`OpenCV smoke job failed: ${state?.status}`);
  const exportResponse = await api(`/jobs/${job.job_id}/results/${state.result_ids[0]}?format=PNG`);
  if ((await exportResponse.arrayBuffer()).byteLength < 16) throw new Error('native PNG export was empty');
}
function createWindow() { const window = new BrowserWindow({show:!selfTest, width: 1320, height: 900, minWidth: 760, minHeight: 600, webPreferences: {preload:path.join(__dirname,'preload.cjs'), contextIsolation:true, sandbox:true, nodeIntegration:false}}); window.on('close', event => { if (!allowClose) { event.preventDefault(); window.webContents.send('pixelmend:action','request-close'); } }); window.loadFile(path.join(__dirname,'../dist/index.html')); return window; }
app.whenReady().then(async () => { if(!ownsApplication){await dialog.showMessageBox({type:'info',title:'PixelMend zaten açık',message:'Önce açık PixelMend çalışmanızı kaydedip uygulamayı kapatın, ardından testi yeniden başlatın.'});app.exit(3);return;} if(selfTest) diagnosticHost=await require('./diagnostic-host.cjs').createDiagnosticHost(); protocol.handle('pixelmend', async requestUrl => { const key = requestUrl.url.replace('pixelmend://',''); const value=sources.get(key); return new Response(value || '', {status:value ? 200 : 404, headers:{'Content-Type':'image/png'}}); }); engineReady=startEngine(); engineReady.catch(()=>{}); if (process.env.PIXELMEND_CI_SMOKE === '1') { let code=0; try { await engineReady; await runSmoke(); } catch (error) { console.error(error); code=1; } finally { try { await stopEngine(); } catch (error) { console.error(error); code=1; } } app.exit(code); return; } const window=mainWindow=createWindow();
 modelEvents = registerModelIpc(ipcMain, api, sender => sender === mainWindow?.webContents);
 const ownership=require('./asset-ownership.cjs').createOwnership(api,sources);
 const authorized=event=>{if(event.sender!==mainWindow.webContents)throw new Error('Geçersiz pencere');};
 const adoptAsset=async asset=>{ownership.adoptAsset(asset.asset_id);try{const preview=await (await api(`/assets/${asset.asset_id}/preview`)).arrayBuffer();sources.set(`asset/${asset.asset_id}`,preview);return {...asset,preview:`pixelmend://asset/${asset.asset_id}`};}catch(error){await ownership.disposeAsset(asset.asset_id).catch(()=>{});throw error;}};
 const generative = registerGenerativeIpc(ipcMain,api,sender=>sender===mainWindow?.webContents,sources,ownership);
 const requireJob = (event,id,result) => {if(event.sender!==mainWindow.webContents||!opaqueId(id)||result!==undefined&&!opaqueId(result))throw new Error('Geçersiz iş');ownership.requireJob(id);};
 window.webContents.on('did-start-loading', () => {modelEvents.unsubscribe(window.webContents);void generative.reset();});
 ipcMain.handle('pixelmend:open-image', async (event) => { authorized(event); const result=await dialog.showOpenDialog(window,{properties:['openFile'],filters:[{name:'Images',extensions:['png','jpg','jpeg','webp','tif','tiff']}]}); if(result.canceled) return null; const form=new FormData(); form.append('image', new Blob([fs.readFileSync(result.filePaths[0])]), path.basename(result.filePaths[0])); const asset=await (await api('/assets',{method:'POST',body:form})).json(); return adoptAsset(asset); });
 ipcMain.handle('pixelmend:start-job', async (event, payload) => { if(event.sender !== mainWindow.webContents) throw new Error('Geçersiz pencere'); const capabilities=await (await api('/capabilities')).json();const {performanceMode}=readSettings();const release=ownership.pin([payload.assetId]);try{const job=await (await api('/jobs',{method:'POST',body:jobForm(payload,capabilities.policy,performanceMode)})).json();ownership.adoptJob(job.job_id,[payload.assetId]);return job;}finally{await release();} });
 ipcMain.handle('pixelmend:job', async (e,id) => {requireJob(e,id);return (await api(`/jobs/${id}`)).json();}); ipcMain.handle('pixelmend:cancel',async(e,id)=>{requireJob(e,id);return (await api(`/jobs/${id}/cancel`,{method:'POST'})).json();});
 ipcMain.handle('pixelmend:result', async (_e,j,r,f='PNG') => { requireJob(_e,j,r); const bytes=await (await api(`/jobs/${j}/results/${r}?format=${f}`)).arrayBuffer(); const key=`result/${j}/${r}`; sources.set(key,bytes); return `pixelmend://${key}`; });
 ipcMain.handle('pixelmend:continue-result', async (e,j,r) => { requireJob(e,j,r);const asset=await adoptAsset(await (await api(`/jobs/${j}/results/${r}/asset`,{method:'POST'})).json());try{await generative.finish(j,asset.asset_id);return asset;}catch(error){await ownership.disposeAsset(asset.asset_id).catch(()=>{});throw error;} });
 ipcMain.handle('pixelmend:save', async (_e,j,r,f='PNG') => { requireJob(_e,j,r); const save=await dialog.showSaveDialog(window,{defaultPath:`PixelMend.${f.toLowerCase()}`}); if(save.canceled)return null; const bytes=await (await api(`/jobs/${j}/results/${r}?format=${f}`)).arrayBuffer(); await writeStreamAtomic(save.filePath,require('node:stream').Readable.from([Buffer.from(bytes)])); return save.filePath; });
 ipcMain.handle('pixelmend:save-image', async (event, payload) => { authorized(event);const release=ownership.pin([payload?.assetId]);try{const save=await dialog.showSaveDialog(window,{defaultPath:'PixelMend.png'});if(save.canceled)return false;const response=await api(`/assets/${payload.assetId}/export?format=PNG`);await writeStreamAtomic(save.filePath,require('node:stream').Readable.fromWeb(response.body));return true;}finally{await release();} });
 ipcMain.handle('pixelmend:render-asset', async (event, payload) => { authorized(event);if(!payload||!Array.isArray(payload.paintStrokes))throw new Error('project_invalid');const release=ownership.pin([payload.assetId]);try{return await adoptAsset(await (await api(`/assets/${payload.assetId}/rendered`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paint_strokes:payload.paintStrokes})})).json());}finally{await release();} });
 ipcMain.handle('pixelmend:confirm-close',event=>{if(event.sender!==mainWindow.webContents)throw new Error('Geçersiz pencere');allowClose=true;app.quit();});
 ipcMain.handle('pixelmend:settings', () => readSettings()); ipcMain.handle('pixelmend:set-settings', (_e, value) => writeAtomic(settingsPath(), JSON.stringify({...defaults,...value})));
 ipcMain.handle('pixelmend:export-source', async (_e, id) => { if(typeof id!=='string'||!/^[a-f0-9]{32}$/.test(id)) throw new Error('Geçersiz görsel'); const bytes=await (await api(`/assets/${id}/export?format=PNG`)).arrayBuffer();return `data:image/png;base64,${Buffer.from(bytes).toString('base64')}`; });
 ipcMain.handle('pixelmend:save-project', async (_e, document, saveAs) => { if(!document || document.version !== 1 || !opaqueId(document.original?.id)) throw new Error('project_invalid'); let destination=!saveAs&&document.original.id===projectAssetId?projectFile:undefined; if(!destination) { const chosen=await dialog.showSaveDialog(window,{defaultPath:'PixelMend.pixelmend',filters:[{name:'PixelMend proje',extensions:['pixelmend']}]}); if(chosen.canceled) return false; destination=chosen.filePath; } const ids=[...new Set(JSON.stringify(document).match(/pixelmend:\/\/(?:asset|result)\/[^"\\]+/g)||[])]; const blobs={}; for(const uri of ids){const key=uri.replace('pixelmend://','');if(key.startsWith('asset/')){const id=key.slice(6);if(!/^[a-f0-9]{32}$/.test(id))throw new Error('project_invalid');blobs[uri]=Buffer.from(await (await api(`/assets/${id}/export?format=PNG`)).arrayBuffer()).toString('base64');}else if(sources.has(key)) blobs[uri]=Buffer.from(sources.get(key)).toString('base64');} writeAtomic(destination,JSON.stringify({format:'pixelmend',version:1,document,blobs})); projectFile=destination;projectAssetId=document.original.id;return true; });
 ipcMain.handle('pixelmend:open-project', async () => { const chosen=await dialog.showOpenDialog(window,{properties:['openFile'],filters:[{name:'PixelMend proje',extensions:['pixelmend']}]});if(chosen.canceled)return null;let saved;try{saved=JSON.parse(fs.readFileSync(chosen.filePaths[0],'utf8'))}catch{throw new Error('project_invalid')}if(saved?.format!=='pixelmend'||saved.version!==1||!saved.document||typeof saved.blobs!=='object')throw new Error('project_invalid');const document=structuredClone(saved.document), replacements=new Map();const capabilities=await (await api('/capabilities')).json();const projectBlobLimit=Math.ceil(Math.max(256*1024*1024,(capabilities.policy?.max_output_pixels??200000000)*4+16*1024*1024)/3)*4;const revive=async photo=>{if(!photo?.uri||replacements.has(photo.uri))return replacements.get(photo?.uri);const b64=saved.blobs[photo.uri];if(typeof b64!=='string'||b64.length>projectBlobLimit)throw new Error('project_invalid');const revived=await (async()=>{const form=new FormData();form.append('image',new Blob([Buffer.from(b64,'base64')]),'project.png');const asset=await (await api('/assets',{method:'POST',body:form})).json();await adoptAsset(asset);return {id:asset.asset_id,uri:`pixelmend://asset/${asset.asset_id}`,width:asset.width,height:asset.height}})();replacements.set(photo.uri,revived);return revived};for(const snapshot of [...document.history.past,document.history.present,...document.history.future])snapshot.photo=await revive(snapshot.photo);document.original=await revive(document.original);projectFile=chosen.filePaths[0];projectAssetId=document.original.id;return document; });
 Menu.setApplicationMenu(Menu.buildFromTemplate([{label:'PixelMend',submenu:[{label:'Ayarlar',accelerator:'Cmd+,',click:()=>mainWindow.webContents.send('pixelmend:action','settings')},{role:'quit'}]},{label:'Düzen',submenu:[{label:'Geri al',accelerator:'Cmd+Z',click:()=>mainWindow.webContents.send('pixelmend:action','undo')},{label:'Yinele',accelerator:'Shift+Cmd+Z',click:()=>mainWindow.webContents.send('pixelmend:action','redo')}]}]));
 await engineReady;
 if(shuttingDown || shutdownComplete || window.isDestroyed()) return;
 if (selfTest) await diagnosticHost.ready({api,editorWindow:window,stopEngine:async()=>{
   // SSE readers must close before uvicorn can finish its graceful shutdown.
   modelEvents?.close();
   try {await stopEngine();} finally {
     if(engine?.diagnosticLog) diagnosticHost.report.artifact('gunlukler/engine.txt',engine.diagnosticLog);
   }
 },shutdown:async code=>{
   allowClose=true;shutdownComplete=true;
   await drainEngine();
   window.destroy();
   fs.rmSync(diagnosticTemp,{recursive:true,force:true});
   app.exit(code);
 }});
 }).catch(async error=>{
   modelEvents?.close();
   // A timed-out/cancelled preparation must expose its partial report even
   // when native inference is still draining. Never wait to record evidence.
   if(diagnosticHost && !shutdownComplete) await diagnosticHost.failed(error);
   await drainEngine();
   if(shuttingDown || shutdownComplete) return;
   if(diagnosticHost){if(process.argv.includes('--self-test-auto'))app.exit(1);}
   else{dialog.showErrorBox('PixelMend başlatılamadı',String(error.message));app.exit(1);}
 });
app.on('window-all-closed',()=>app.quit());
// Do not stop the engine until the renderer has resolved unsaved changes.
app.on('before-quit', event => {
  if (!allowClose && mainWindow && !mainWindow.isDestroyed()) {
    event.preventDefault();mainWindow.webContents.send('pixelmend:action','request-close');return;
  }
  if (!shutdownComplete) {
    event.preventDefault();
    if (shuttingDown) return;
    shuttingDown=true;modelEvents?.close();
    stopEngine().then(()=>{shutdownComplete=true;app.quit();}).catch(error=>{
      console.error(error);shuttingDown=false;
      // Native work may need longer than the initial grace period; never force-kill it.
      engine?.once('exit',()=>{shutdownComplete=true;app.quit();});
    });
  }
});
