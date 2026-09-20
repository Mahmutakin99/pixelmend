const {_electron:electron,expect}=require('@playwright/test');
const fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const temp=await fs.mkdtemp(path.join(os.tmpdir(),'pixelmend-model-acceptance-'));
 const executablePath=process.env.PIXELMEND_E2E_APP || path.resolve('out.noindex/mac-arm64/PixelMend.app/Contents/MacOS/PixelMend');
 const fresh=process.env.PIXELMEND_E2E_FRESH === '1';
 const launch=()=>electron.launch({executablePath,args:[`--user-data-dir=${temp}/profile`],env:{...process.env,...(fresh?{PIXELMEND_MODELS_DIR:path.join(temp,'models')}:{})},timeout:60000});
 let app=await launch();
 try {
 let page=await app.firstWindow();page.on('console',m=>{if(m.type()==='error')console.log(m.text());});
 await expect(page.getByRole('heading',{name:'PixelMend',exact:true})).toBeVisible();
 if(fresh){
   const before=await page.evaluate(()=>window.pixelmend.models());assert(before.models.every(m=>m.state==='absent'));
   const candidates={lama:'/Users/gladius/Library/Caches/PixelMend/models/lama/a3ee2fca54baebec351b8fa7786154ffa7555aa6/lama_fp32.onnx','realesrgan-x4plus':'/Users/gladius/Library/Caches/PixelMend/models/realesrgan-x4plus/c4e5303b53044767c94bb78f49365cb710ee459e/realesrgan-x4plus-fp32.onnx'};
   for(const [id,original] of Object.entries(candidates)){
     const local=path.join(temp,id+'.onnx');await fs.copyFile(original,local);
     await app.evaluate(({dialog},local)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[local]});},local);
     await page.evaluate(id=>window.pixelmend.modelAction(id,'install-local'),id);
     await expect.poll(async()=>{const x=await page.evaluate(()=>window.pixelmend.models());return x.models.find(m=>m.id===id).state;},{timeout:60000}).toBe('ready');
     await fs.unlink(local);
   }
   await app.close();app=await launch();page=await app.firstWindow();
   await expect(page.getByRole('heading',{name:'PixelMend',exact:true})).toBeVisible();
 }
 const models=await page.evaluate(()=>window.pixelmend.models());assert(models.models.every(m=>m.state==='ready'));
 const source=path.join(temp,'source.png');
 const bytes=await page.evaluate(()=>{const c=document.createElement('canvas');c.width=96;c.height=64;const x=c.getContext('2d');x.fillStyle='#aabbcc';x.fillRect(0,0,96,64);return c.toDataURL().split(',')[1];});
 await fs.writeFile(source,Buffer.from(bytes,'base64'));
 await app.evaluate(({dialog},source)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[source]});},source);
 const asset=await page.evaluate(()=>window.pixelmend.openImage());
 const project=path.join(temp,'roundtrip.pixelmend');
 await app.evaluate(({dialog},project)=>{dialog.showSaveDialog=async()=>({canceled:false,filePath:project});dialog.showOpenDialog=async()=>({canceled:false,filePaths:[project]});},project);
 assert(await page.evaluate(asset=>{const photo={id:asset.asset_id,uri:asset.preview,width:asset.width,height:asset.height};return window.pixelmend.saveProject({version:1,original:photo,history:{past:[],present:{photo,paint:[],selection:[],label:'opened'},future:[]}},true);},asset));
 const revived=await page.evaluate(()=>window.pixelmend.openProject());
 assert.equal(revived.history.present.photo.width,96);assert.notEqual(revived.original.id,asset.asset_id);

 for(const operation of ['remove','upscale']){
 const job=await page.evaluate(({asset,operation})=>window.pixelmend.startJob({assetId:asset.asset_id,operation,removeMethod:'lama',upscaleMethod:'ai',targetWidth:192,targetHeight:128,selectionStrokes:[{mode:'draw',points:[{x:48,y:32}],color:'#ff0000',opacity:1,size:10,hardness:1}]}),{asset,operation});
 let state;
 await expect.poll(async()=>{state=await page.evaluate(id=>window.pixelmend.job(id),job.job_id);return state.status;},{timeout:120000}).toBe('completed');
 console.log(JSON.stringify(state));assert.equal(state.result_details[0].algorithm,operation==='remove'?'lama':'realesrgan_x4plus');assert.equal(state.provider,operation==='remove'?'CPUExecutionProvider':'CoreMLExecutionProvider');assert(state.model_revision);
 }
 const cancelJob=await page.evaluate(asset=>window.pixelmend.startJob({assetId:asset.asset_id,operation:'upscale',upscaleMethod:'ai',targetWidth:384,targetHeight:256}),asset);
 await page.evaluate(id=>window.pixelmend.cancel(id),cancelJob.job_id);
 await expect.poll(async()=> (await page.evaluate(id=>window.pixelmend.job(id),cancelJob.job_id)).status,{timeout:120000}).toBe('cancelled');
 console.log('PASS: packaged actual LaMa CPU and RealESRGAN Core ML metadata');
 }finally{await app.close();await fs.rm(temp,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
