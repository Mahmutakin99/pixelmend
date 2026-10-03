const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const {EventEmitter} = require('node:events');
const {createRequire} = require('node:module');

// Exercise the real main process and IPC registration. Electron/child I/O are
// boundaries here; the native E2E suite additionally exercises real windows.
function launch({smoke = false, fail = false, diagnosticFailure = false, stallShutdown = false} = {}) {
  const app = new EventEmitter();
  const windows = [], handlers = new Map(), errors = [], exits = [];
  let readyCallback, releaseHealth;
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
  const electron = {app,BrowserWindow,dialog:{showErrorBox(){},showMessageBox:async()=>{}},
    ipcMain:{handle:(name,fn)=>handlers.set(name,fn),on(){}},protocol:{handle(){}},Menu:{buildFromTemplate:x=>x,setApplicationMenu(){}}};
  const filename = path.join(__dirname,'main.cjs'), localRequire = createRequire(filename);
  const diagnosticHost={ready:async()=>{throw Object.assign(new Error('preparation timeout'),{name:'TimeoutError'});},
    failed:async()=>{failureRecorded=true;},report:{artifact(){}}};
  const context = {require:name => name==='electron' ? electron : name==='child_process' ? {spawn:()=>child}
    : name==='./diagnostic-host.cjs'&&diagnosticFailure ? {createDiagnosticHost:async()=>diagnosticHost} : localRequire(name),
    __dirname,Buffer,Response,FormData,Blob,AbortSignal,setTimeout,clearTimeout,console,
    process:{argv:diagnosticFailure?['--self-test','--self-test-auto']:[],env:smoke?{PIXELMEND_CI_SMOKE:'1'}:{},platform:'darwin',resourcesPath:'/app/resources'},
    fetch:async url=>{
      if(url.endsWith('/health')) {await health;if(fail)throw new Error('fixture startup failure');return Response.json({status:'ok'});}
      if(url.endsWith('/models'))return Response.json({models:[{id:'lama',state:'waiting'}]});
      if(url.endsWith('/shutdown')) {if(!stallShutdown){child.exitCode=0;child.emit('exit');}return Response.json({status:'stopping'});}
      throw new Error(`Unexpected route: ${url}`);
    }};
  vm.runInNewContext(fs.readFileSync(filename,'utf8'),context,{filename});
  const startup = readyCallback().catch(errors[0]);
  return {app,windows,handlers,child,exits,startup,failed:()=>failureRecorded,release:()=>releaseHealth(),
    port:()=>child.stdout.emit('data',Buffer.from('{"port":12345}\n'))};
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
