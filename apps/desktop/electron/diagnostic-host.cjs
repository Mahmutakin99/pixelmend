const {app, BrowserWindow, dialog, ipcMain, shell} = require('electron');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const {setTimeout:delay} = require('node:timers/promises');
const {createReport, sanitize} = require('./diagnostic-report.cjs');
const {runDiagnostics, classifyError} = require('./diagnostic-runner.cjs');

async function createDiagnosticHost() {
  let parent = process.env.PIXELMEND_DIAGNOSTIC_OUTPUT || app.getPath('desktop');
  let report;
  while (!report) {
    try { report=createReport(parent,{appVersion:app.getVersion(),electronVersion:process.versions.electron,
      platform:process.platform,processArchitecture:process.arch,osVersion:os.release(),mode:'standard'}); }
    catch {
      const selection=await dialog.showOpenDialog({title:'Rapor için yazılabilir bir klasör seçin',properties:['openDirectory','createDirectory']});
      if(selection.canceled)throw new Error('Rapor klasörü seçilmedi.');
      parent=selection.filePaths[0];
    }
  }
  const window = new BrowserWindow({title:'PixelMend · Bilgisayar testi',width:860,height:850,minWidth:540,minHeight:550,
    webPreferences:{preload:path.join(__dirname,'diagnostic-preload.cjs'),sandbox:true,contextIsolation:true,nodeIntegration:false}});
  let state={phase:'preparing',message:'Motor ve model dosyaları hazırlanıyor…',models:[],tests:[],downloadBytes:0,hasReport:false};
  let archive, api, editorWindow, stopEngine, shutdown, running, controller, activeDownload;
  const send=()=>{if(!window.isDestroyed())window.webContents.send('diagnostics:update',sanitize(state));};
  const record=report.record.bind(report);
  report.record=value=>{record(value);state.tests=report.state.tests;send();};
  const authorized=event=>{if(event.sender!==window.webContents)throw new Error('Geçersiz pencere');};
  function handler(name,fn){ipcMain.handle(`diagnostics:${name}`,(event,...args)=>{authorized(event);return fn(...args);});}
  handler('state',()=>sanitize(state));
  handler('cancel',async()=>{
    controller?.abort();state.message='İptal ediliyor; tamamlanan sonuçlar korunuyor…';send();
    if(activeDownload)await api(`/models/${activeDownload}/cancel`,{method:'POST'});
  });
  async function finish(notes='') {
    if(state.phase!=='done')throw new Error('Test henüz sona ermedi.');
    archive=await report.finish(typeof notes==='string'?notes.slice(0,8000):'');
    state.hasReport=true;state.message='Rapor klasörünüzde hazır. ZIP dosyasını paylaşabilirsiniz.';send();
  }
  handler('finish',finish);
  handler('reveal',()=>{shell.showItemInFolder(archive || report.directory);});
  async function start(options) {
    if(state.phase!=='ready' || !['standard','comprehensive'].includes(options?.mode) || typeof options.installMissing!=='boolean')throw new Error('Geçersiz test isteği.');
    controller=new AbortController();state.phase='running';report.metadata({mode:options.mode});send();
    const onProgress=message=>{state.message=message;send();};
    running=(async()=>{
      try {
        if(options.installMissing) {
          for(const model of state.models.filter(m=>m.published && m.state!=='ready')) {
            if(controller.signal.aborted)break;
            activeDownload=model.id;const began=Date.now();
            report.record({id:`install-${model.id}`,name:`${model.name} kurulumu`,status:'running'});
            try {
              await api(`/models/${model.id}/install`,{method:'POST'});
              while(true){
                if(controller.signal.aborted)await api(`/models/${model.id}/cancel`,{method:'POST'});
                const current=(await (await api('/models')).json()).models.find(m=>m.id===model.id);
                onProgress(`${model.name}: ${current.state} · ${Math.round((current.downloaded_bytes||0)/1024**2)} MiB`);
                if(['ready','error','cancelled'].includes(current.state)){
                  report.record({id:`install-${model.id}`,name:`${model.name} kurulumu`,status:current.state==='ready'?'passed':current.state==='cancelled'?'cancelled':'failed',detail:current.error?.message});break;
                }
                if(Date.now()-began>60*60*1000){await api(`/models/${model.id}/cancel`,{method:'POST'});throw Object.assign(new Error('Kurulum bir saat içinde tamamlanamadı.'),{name:'TimeoutError'});}
                await delay(500);
              }
            }catch(error){report.record({id:`install-${model.id}`,name:`${model.name} kurulumu`,status:classifyError(error),detail:error.message});}
            finally{activeDownload=undefined;}
          }
        }
        state.models=(await (await api('/models')).json()).models;
        report.metadata({models:state.models.map(({id,name,state,revision,sha256,probe,source})=>({id,name,state,revision,sha256,probe,source}))});
        await runDiagnostics({api,report,models:state.models,signal:controller.signal,onProgress});
        if(!controller.signal.aborted) {
          const {runEditorChecks}=require('./diagnostic-ui.cjs');
          await runEditorChecks({window:editorWindow,api,report,signal:controller.signal,onProgress});
        } else report.record({id:'editor',name:'Editör ve arayüz',status:'cancelled'});
        if(options.mode==='comprehensive' && !controller.signal.aborted) {
          const {runPhotographs}=require('./diagnostic-photographs.cjs');
          await runPhotographs({api,report,models:state.models,signal:controller.signal,onProgress});
        }
      }catch(error){report.record({id:'runner',name:'Test yürütücüsü',status:classifyError(error),detail:error.message});}
      finally {
        try {await stopEngine();report.record({id:'shutdown',name:'Motorun kapanması',status:'passed'});}
        catch(error){report.record({id:'shutdown',name:'Motorun kapanması',status:'failed',detail:error.message});}
        state.phase='done';
        try{await finish();}catch{state.message='ZIP oluşturulamadı. Kısmi rapor klasöründe sonuçlar korundu.';state.hasReport=true;send();}
        if(process.argv.includes('--self-test-auto')) {
          const code=report.state.status==='passed'?0:report.state.status==='failed'?1:2;
          await shutdown(code);
        }
      }
    })();
    return true;
  }
  handler('start',start);
  window.on('close',event=>{
    if(state.phase==='running' || state.phase==='preparing'){
      event.preventDefault();controller?.abort();state.message='İşlem tamamlanıp rapor korunana kadar bekleyin…';send();
    }else if(shutdown){event.preventDefault();void shutdown(report.state.status==='failed'?1:report.state.status==='passed'?0:2);}
  });
  await window.loadFile(path.join(__dirname,'diagnostic.html'));
  return {
    report,
    async ready(dependencies) {
      ({api,editorWindow,stopEngine,shutdown}=dependencies);
      const capabilities=await (await api('/capabilities')).json();
      const runtime=await (await api('/diagnostics/runtime')).json();
      report.metadata({capabilities,runtime});
      state.models=(await (await api('/models')).json()).models;
      state.device=`${capabilities.accelerator?.identity || os.type()} · ${(capabilities.host_ram_total_bytes/1024**3).toFixed(0)} GB bellek · ${process.arch}`;
      state.downloadBytes=state.models.filter(m=>m.published && m.state!=='ready').reduce((total,m)=>total+(m.size_bytes||0),0);
      state.phase='ready';state.message='Testi başlatabilirsiniz. Süre, modellerinize ve bilgisayarınıza bağlıdır.';send();
      await delay(200);
      report.artifact('gorseller/test-window.png',(await window.webContents.capturePage()).toPNG());
      if(process.argv.includes('--self-test-auto'))void start({mode:process.argv.includes('--self-test-comprehensive')?'comprehensive':'standard',installMissing:false});
    },
    async failed(error) {
      report.record({id:'startup',name:'Uygulama başlangıcı',status:'failed',detail:error.message});
      state.phase='done';await finish();
    },
  };
}
module.exports={createDiagnosticHost};
