// Real Electron + real cached models; only native file dialogs are automated.
const {_electron:electron,expect} = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');

(async()=>{
  const output=path.resolve(process.env.PIXELMEND_E2E_OUTPUT || 'test-results/startup');
  await fs.mkdir(output,{recursive:true});
  const results=[];
  for(let attempt=1;attempt<=3;attempt++) {
    const temp=await fs.mkdtemp(path.join(os.tmpdir(),'pixelmend-rc4-startup-'));
    const began=performance.now();
    const executablePath=process.env.PIXELMEND_E2E_APP;
    const application=await electron.launch({...(executablePath?{executablePath}:{}),
      args:[...(executablePath?[]:['.']),`--user-data-dir=${temp}/profile`],timeout:30000});
    const childProcess=application.process();
    const errors=[];
    let page;
    try {
      page=await application.firstWindow();
      page.on('pageerror',error=>errors.push(error.message));
      await expect(page.getByRole('heading',{name:'PixelMend',exact:true})).toBeVisible();
      const interactiveMs=Math.round(performance.now()-began);
      assert(interactiveMs<=5000,`interactive window took ${interactiveMs} ms`);
      const initial=await page.evaluate(()=>window.pixelmend.models());
      const pending=initial.models.filter(m=>['waiting','verifying','probing'].includes(m.state));
      assert(pending.length>0,'fixture requires real installed models still preparing');
      await expect(page.getByRole('note')).toContainText('arka planda');
      await page.getByRole('button',{name:'Ayarlar',exact:true}).click();
      await page.getByRole('button',{name:'Hakkında',exact:true}).click();
      await expect(page.getByText('1.0.0-rc.4',{exact:true})).toBeVisible();
      await page.getByRole('button',{name:'AI modelleri',exact:true}).click();
      await expect(page.getByRole('heading',{name:'Kurulu modeller',exact:true})).toBeVisible();
      await page.getByRole('button',{name:'Bitti',exact:true}).click();
      const png=await page.evaluate(()=>{
        const c=document.createElement('canvas');c.width=96;c.height=64;
        const ctx=c.getContext('2d');ctx.fillStyle='#b4b4b4';ctx.fillRect(0,0,96,64);
        ctx.fillStyle='#000';ctx.fillRect(43,27,10,10);return c.toDataURL().split(',')[1];
      });
      const sourcePath=path.join(temp,'source.png'),savedPath=path.join(temp,'saved.png');
      await fs.writeFile(sourcePath,Buffer.from(png,'base64'));
      await application.evaluate(({dialog},paths)=>{
        dialog.showOpenDialog=async()=>({canceled:false,filePaths:[paths.sourcePath]});
        dialog.showSaveDialog=async()=>({canceled:false,filePath:paths.savedPath});
      },{sourcePath,savedPath});
      await page.getByRole('button',{name:'Görsel Aç',exact:true}).click();
      await expect(page.locator('.canvas img')).toBeVisible();
      const canvas=page.locator('.canvas canvas.paint'),rect=await canvas.boundingBox();
      await page.mouse.move(rect.x+rect.width/2,rect.y+rect.height/2);
      await page.mouse.down();await page.mouse.up();
      assert(await canvas.evaluate(c=>c.getContext('2d').getImageData(48,32,1,1).data[3])>0);
      await page.getByRole('button',{name:'Nesne silme',exact:true}).click();
      await page.getByRole('button',{name:'Nesne Seçici',exact:true}).click();
      await page.mouse.move(rect.x+rect.width/2,rect.y+rect.height/2);
      await page.mouse.down();await page.mouse.up();
      await page.getByRole('radio',{name:'Hızlı — OpenCV',exact:true}).check();
      await page.getByRole('button',{name:'Nesneyi Sil',exact:true}).click();
      await expect(page.getByRole('button',{name:'Uygula',exact:true})).toBeVisible({timeout:10000});
      await page.getByRole('button',{name:'Uygula',exact:true}).click();
      await page.getByRole('button',{name:'Büyütme',exact:true}).click();
      await page.getByRole('button',{name:'2×',exact:true}).click();
      await expect(page.getByRole('button',{name:'Uygula',exact:true})).toBeVisible({timeout:10000});
      await page.getByRole('button',{name:'Uygula',exact:true}).click();
      const basicEditingMs=Math.round(performance.now()-began);
      const mid=await page.evaluate(()=>window.pixelmend.models());
      assert(mid.models.some(m=>['waiting','verifying','probing'].includes(m.state)),
        'basic editing must complete before all model preparation finishes');
      await page.getByRole('button',{name:'Kaydet',exact:true}).click();
      await page.getByRole('button',{name:'Görsel olarak kaydet (PNG)',exact:true}).click();
      await expect(page.getByRole('status')).toContainText('kaydedildi');
      assert((await fs.stat(savedPath)).size>0);
      await page.screenshot({path:path.join(output,`startup-${attempt}.png`)});
      await expect.poll(async()=>{
        const {models}=await page.evaluate(()=>window.pixelmend.models());
        return models.filter(m=>m.published).every(m=>m.state==='ready'&&m.probe?.status==='passed');
      },{timeout:180000}).toBe(true);
      const modelsReadyMs=Math.round(performance.now()-began);
      await page.getByRole('button',{name:'Nesne silme',exact:true}).click();
      await page.getByRole('radio',{name:/AI ile nesne sil/}).check();
      await expect(page.getByRole('button',{name:'Nesneyi Sil',exact:true})).toBeEnabled();
      assert.deepEqual(errors,[]);
      results.push({attempt,interactiveMs,basicEditingMs,modelsReadyMs,initialModels:initial.models.map(({id,state})=>({id,state})),pageErrors:errors});
      // Save was confirmed; let the app's own close handshake drain the sidecar.
      const exited=new Promise(resolve=>childProcess.once('exit',resolve));
      await application.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].close());
      await exited;
    } finally {
      // This is only the isolated synthetic fixture, never a user's document.
      // Explicit close confirmation still uses the production graceful drain.
      if(childProcess.exitCode===null && childProcess.signalCode===null)
        await page?.evaluate(()=>window.pixelmend.confirmClose()).catch(()=>{});
      await application.close().catch(()=>{});
      await fs.rm(temp,{recursive:true,force:true});
    }
  }
  const closingTemp=await fs.mkdtemp(path.join(os.tmpdir(),'pixelmend-rc4-early-close-'));
  const executablePath=process.env.PIXELMEND_E2E_APP;
  const closing=await electron.launch({...(executablePath?{executablePath}:{}),
    args:[...(executablePath?[]:['.']),`--user-data-dir=${closingTemp}/profile`],timeout:30000});
  const closingProcess=closing.process();
  let closePage;
  try {
    closePage=await closing.firstWindow();
    await expect(closePage.getByRole('heading',{name:'PixelMend',exact:true})).toBeVisible();
    const {models}=await closePage.evaluate(()=>window.pixelmend.models());
    assert(models.some(m=>['waiting','verifying','probing'].includes(m.state)));
    const began=performance.now();
    const exited=new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>reject(new Error('early close did not drain within 30 seconds')),30000);
      closingProcess.once('exit',()=>{clearTimeout(timer);resolve();});
    });
    await closing.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].close());
    await exited;
    await fs.writeFile(path.join(output,'early-close.json'),JSON.stringify({closedDuringPreparation:true,
      gracefulCloseMs:Math.round(performance.now()-began)},null,2)+'\n');
  } finally {
    if(closingProcess.exitCode===null && closingProcess.signalCode===null)
      await closePage?.evaluate(()=>window.pixelmend.confirmClose()).catch(()=>{});
    await closing.close().catch(()=>{});
    await fs.rm(closingTemp,{recursive:true,force:true});
  }
  await fs.writeFile(path.join(output,'timings.json'),JSON.stringify(results,null,2)+'\n');
  console.log(JSON.stringify(results.map(({attempt,interactiveMs,basicEditingMs,modelsReadyMs})=>({attempt,interactiveMs,basicEditingMs,modelsReadyMs})),null,2));
})().catch(error=>{console.error(error);process.exitCode=1;});
