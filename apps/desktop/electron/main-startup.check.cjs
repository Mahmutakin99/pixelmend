const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const {EventEmitter} = require('node:events');
const {createRequire} = require('node:module');

// Exercise the real main process and IPC registration. Electron/child I/O are
// boundaries here; the native E2E suite additionally exercises real windows.
function launch({smoke = false, fail = false, diagnosticFailure = false, stallShutdown = false, projectFixture} = {}) {
  const app = new EventEmitter();
  const windows = [], handlers = new Map(), errors = [], exits = [];
  let readyCallback, releaseHealth, protocolHandler;
  let failureRecorded=false;
  const health = new Promise(resolve => {releaseHealth = resolve;});
  Object.assign(app, {
    isPackaged: true, commandLine: {appendSwitch() {}},
    requestSingleInstanceLock: () => true,
    whenReady: () => ({then(fn) {readyCallback = fn;return {catch(fn) {errors.push(fn);}};}}),
    getPath: () => '/tmp/pixelmend-startup-fixture',
    setPath() {},
    quit: () => exits.push('quit'), exit: code => exits.push(code),
  });
  class BrowserWindow extends EventEmitter {
    constructor() {super();this.webContents = new EventEmitter();Object.assign(this.webContents, {id:1,isDestroyed:()=>false,send(){}});windows.push(this);}
    loadFile() {return Promise.resolve();}
    isDestroyed() {return false;}
  }
  const child = new EventEmitter();
  Object.assign(child, {exitCode:null,signalCode:null,stdout:new EventEmitter(),stderr:new EventEmitter()});
  child.stdout.resume = () => {};
  child.kill = signal => {child.signalCode=signal;child.emit('exit');};
  const electron = {app,BrowserWindow,dialog:{showErrorBox(){},showMessageBox:async()=>{},...projectFixture?.dialog},
    ipcMain:{handle:(name,fn)=>handlers.set(name,fn),on(){}},protocol:{handle(_scheme,handler){protocolHandler=handler;}},Menu:{buildFromTemplate:x=>x,setApplicationMenu(){}}};
  const filename = path.join(__dirname,'main.cjs'), localRequire = createRequire(filename);
  const diagnosticHost={ready:async()=>{throw Object.assign(new Error('preparation timeout'),{name:'TimeoutError'});},
    failed:async()=>{failureRecorded=true;},report:{artifact(){}}};
  const context = {require:name => name==='electron' ? electron : name==='child_process' ? {spawn:()=>child}
    : name==='fs'&&projectFixture ? {...fs,...projectFixture.fs} : name==='./diagnostic-host.cjs'&&diagnosticFailure ? {createDiagnosticHost:async()=>diagnosticHost} : localRequire(name),
    __dirname,Buffer,Response,FormData,Blob,AbortSignal,setTimeout,clearTimeout,console,
    process:{argv:diagnosticFailure?['--self-test','--self-test-auto']:[],env:smoke?{PIXELMEND_CI_SMOKE:'1'}:{},platform:'darwin',resourcesPath:'/app/resources'},
    fetch:async (url,options)=>{
      if(projectFixture?.api){const response=await projectFixture.api(new URL(url).pathname,options);if(response)return response;}
      if(url.endsWith('/health')) {await health;if(fail)throw new Error('fixture startup failure');return Response.json({status:'ok'});}
      if(url.endsWith('/models'))return Response.json({models:[{id:'lama',state:'waiting'}]});
      if(url.endsWith('/shutdown')) {if(!stallShutdown){child.exitCode=0;child.emit('exit');}return Response.json({status:'stopping'});}
      throw new Error(`Unexpected route: ${url}`);
    }};
  vm.runInNewContext(fs.readFileSync(filename,'utf8'),context,{filename});
  const startup = readyCallback().catch(errors[0]);
  return {app,windows,handlers,child,exits,startup,failed:()=>failureRecorded,release:()=>releaseHealth(),
    protocol:request=>protocolHandler(request),port:()=>child.stdout.emit('data',Buffer.from('{"port":12345}\n'))};
}

test('window and IPC exist while engine startup is still pending', async () => {
  const fixture = launch();
  try {
    assert.equal(fixture.windows.length,1,'window must not wait for engine health');
    const handler = fixture.handlers.get('pixelmend:models');
    assert.equal(typeof handler,'function');
    let settled = false;
    const request = handler({sender:fixture.windows[0].webContents}).then(value=>{settled=true;return value;});
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(settled,false,'engine requests must wait for readiness');
    fixture.port();fixture.release();
    assert.deepEqual(JSON.parse(JSON.stringify(await request)),{models:[{id:'lama',state:'waiting'}]});
  } finally {fixture.port();fixture.release();await fixture.startup;}
});

test('startup failure rejects pending IPC and stops the owned child', async () => {
  const fixture = launch({fail:true});
  try {
    assert.equal(fixture.windows.length,1);
    const request = fixture.handlers.get('pixelmend:models')({sender:fixture.windows[0].webContents});
    const rejected = assert.rejects(request,/fixture startup failure/);
    fixture.port();fixture.release();
    await rejected;await fixture.startup;
    assert.equal(fixture.child.exitCode,0,'startup failure must not orphan the engine');
  } finally {fixture.port();fixture.release();await fixture.startup;}
});

test('diagnostic timeout is reported before a stalled native child drains', async () => {
  const fixture=launch({diagnosticFailure:true,stallShutdown:true});
  try {
    await new Promise(resolve=>setImmediate(resolve));
    fixture.port();fixture.release();
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(fixture.failed(),true,'timeout report must be available before native exit');
    assert.equal(fixture.child.exitCode,null);
  } finally {
    fixture.port();fixture.release();
    fixture.child.exitCode=0;fixture.child.emit('exit');
    await fixture.startup;
  }
});

test('closing during startup terminates only the owned child and rejects pending IPC', async () => {
  const fixture=launch();
  try {
    const request=fixture.handlers.get('pixelmend:models')({sender:fixture.windows[0].webContents});
    const rejected=assert.rejects(request,/Engine exited before startup/);
    // The close confirmation sets allowClose; the native runtime then emits before-quit.
    fixture.handlers.get('pixelmend:confirm-close')({sender:fixture.windows[0].webContents});
    let prevented=false;
    fixture.app.emit('before-quit',{preventDefault(){prevented=true;}});
    await rejected;await fixture.startup;
    assert.equal(prevented,true);
    assert.equal(fixture.child.signalCode,'SIGTERM');
    assert(fixture.exits.includes('quit'));
  } finally {fixture.port();fixture.release();await fixture.startup;}
});

test('a new generated document requests its own v2 project path and preserves the prior project',async()=>{
 const fsp=require('node:fs/promises'),os=require('node:os'),{readProject}=require('./project-codec.cjs');
 const folder=await fsp.mkdtemp(path.join(os.tmpdir(),'pixelmend-main-project-'));let chosen=0,imports=0;
 const source=path.join(folder,'source.png');await fsp.writeFile(source,'synthetic photo');
 const oldFile=path.join(folder,'old.pixelmend'),newFile=path.join(folder,'generated.pixelmend');
 const fixture=launch({projectFixture:{dialog:{showOpenDialog:async()=>({canceled:false,filePaths:[source]}),showSaveDialog:async()=>({canceled:false,filePath:++chosen===1?oldFile:newFile})},api:async route=>{
  if(route==='/assets')return Response.json({asset_id:(++imports===1?'a':'b').repeat(32),width:16,height:16});
  if(route.startsWith('/assets/'))return new Response('synthetic photo');
 }}});
 fixture.port();fixture.release();await fixture.startup;const event={sender:fixture.windows[0].webContents};
 const document=a=>({version:1,original:{id:a.asset_id,uri:a.preview,width:16,height:16},history:{past:[],present:{photo:{id:a.asset_id,uri:a.preview,width:16,height:16},paint:[],selection:[],label:'opened'},future:[]}});
 try{
  const previous=document(await fixture.handlers.get('pixelmend:open-image')(event));
  await fixture.handlers.get('pixelmend:save-project')(event,previous,false);const old=await fsp.readFile(oldFile);
  const generated=document(await fixture.handlers.get('pixelmend:open-image')(event));
  await fixture.handlers.get('pixelmend:save-project')(event,generated,false);
  assert.equal(chosen,2);assert.ok((await fsp.readFile(oldFile)).equals(old));
  const saved=await readProject(newFile,async()=>generated.original,async()=>{});assert.equal(saved.original.id,generated.original.id);
  await fixture.handlers.get('pixelmend:save-project')(event,generated,false);assert.equal(chosen,2);
 }finally{await fsp.rm(folder,{recursive:true,force:true});}
});

test('100 rendered export cycles leave only the document asset and remove disposed previews',async()=>{
 const fsp=require('node:fs/promises'),os=require('node:os');const folder=await fsp.mkdtemp(path.join(os.tmpdir(),'pixelmend-main-assets-'));
 const source=path.join(folder,'source.png');await fsp.writeFile(source,'source');const assets=new Set();let index=0;
 const fixture=launch({projectFixture:{dialog:{showOpenDialog:async()=>({canceled:false,filePaths:[source]}),showSaveDialog:async()=>({canceled:true})},api:async(route,options)=>{
  if(route==='/assets'||route.endsWith('/rendered')){if(assets.size>=32)return Response.json({detail:'capacity'},{status:409});const asset_id=(++index).toString(16).padStart(32,'0');assets.add(asset_id);return Response.json({asset_id,width:16,height:16});}
  if(route.startsWith('/assets/')){const id=route.split('/')[2];if(options?.method==='DELETE'){assets.delete(id);return new Response(null,{status:204});}return new Response('preview');}
 }}});
 fixture.port();fixture.release();await fixture.startup;const event={sender:fixture.windows[0].webContents},invoke=(name,...args)=>fixture.handlers.get(`pixelmend:${name}`)(event,...args);
 try{
  const sourceAsset=await invoke('open-image');await invoke('set-document-assets',{revision:1,assetIds:[sourceAsset.asset_id]});
  for(let i=0;i<100;i++){
   const rendered=await invoke('render-asset',{assetId:sourceAsset.asset_id,paintStrokes:[]});assert.equal(await invoke('save-image',{assetId:rendered.asset_id}),false);await invoke('dispose-asset',rendered.asset_id);
   assert.equal((await fixture.protocol({url:rendered.preview})).status,404);assert.equal(assets.size,1);
  }
  await invoke('set-document-assets',{revision:2,assetIds:[]});assert.equal(assets.size,0);
 }finally{await fsp.rm(folder,{recursive:true,force:true});}
});
