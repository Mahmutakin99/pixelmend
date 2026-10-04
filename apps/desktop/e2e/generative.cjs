// Explicit native acceptance flow; requires installed packages and an accepted
// profile. Never downloads models or rewrites the production profile catalog.
const {_electron:electron,expect}=require('@playwright/test');
const fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const output=path.resolve(process.env.PIXELMEND_E2E_OUTPUT||'test-results/generative');await fs.mkdir(output,{recursive:true});
 const temp=await fs.mkdtemp(path.join(os.tmpdir(),'pixelmend-generative-ui-'));
 const app=await electron.launch(process.env.PIXELMEND_E2E_APP?{executablePath:process.env.PIXELMEND_E2E_APP,args:[`--user-data-dir=${temp}/profile`]}:{args:['.',`--user-data-dir=${temp}/profile`]});
 let page;const errors=[];
 try{
  page=await app.firstWindow();page.on('pageerror',e=>errors.push(e.message));
  await expect(page.getByRole('button',{name:'Yazıyla Oluştur',exact:true})).toBeVisible();
  const facts=await page.evaluate(()=>window.pixelmend.capabilities());
  assert(facts.generative?.accepted_profiles.includes('low-resource'),'explicit low-resource profile acceptance required');
  const source=path.resolve('../../engine/bench/fixtures/original-coffee.png'),project=path.join(temp,'test.pixelmend'),png=path.join(temp,'test.png');
  await app.evaluate(({dialog},files)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[files.source]});dialog.showSaveDialog=async (...args)=>({canceled:false,filePath:args.at(-1).defaultPath.endsWith('.pixelmend')?files.project:files.png});},{source,project,png});
  await page.getByRole('button',{name:'Görsel Aç',exact:true}).click();
  await page.getByRole('button',{name:'Yazıyla Düzenle',exact:true}).click();
  const mask=page.locator('.canvas .mask'),rect=await mask.boundingBox();
  await page.getByLabel('Seçim boyutu').evaluate(node=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(node,'200');node.dispatchEvent(new Event('input',{bubbles:true}));});
  await page.mouse.click(rect.x+rect.width*.79,rect.y+rect.height*.55);
  const original=await page.locator('.canvas img').getAttribute('src');
  await page.getByLabel('Komut',{exact:true}).fill('Masanın sağ tarafına oturan küçük turuncu bir kedi ekle.');
  await page.getByRole('button',{name:'Üret',exact:true}).click();
  await expect(page.getByRole('button',{name:'Geri al',exact:true})).toBeDisabled();
  await expect(page.getByRole('button',{name:'Uygula',exact:true})).toBeVisible({timeout:300000});
  await page.screenshot({path:path.join(output,'edit-preview.png')});
  await page.getByLabel('Orijinali göster').check();expect(await page.locator('.canvas img').getAttribute('src')).toBe(original);
  await page.getByRole('button',{name:'Vazgeç',exact:true}).click();expect(await page.locator('.canvas img').getAttribute('src')).toBe(original);
  await page.getByRole('button',{name:'Üret',exact:true}).click();await expect(page.getByRole('button',{name:'Uygula',exact:true})).toBeVisible({timeout:300000});
  await page.getByRole('button',{name:'Uygula',exact:true}).click();const applied=await page.locator('.canvas img').getAttribute('src');assert.notEqual(applied,original);
  await page.getByRole('button',{name:'Geri al',exact:true}).click();expect(await page.locator('.canvas img').getAttribute('src')).toBe(original);
  await page.getByRole('button',{name:'Yinele',exact:true}).click();expect(await page.locator('.canvas img').getAttribute('src')).toBe(applied);
  await page.getByRole('button',{name:'Kaydet',exact:true}).click();await page.getByRole('button',{name:'Projeyi kaydet (.pixelmend)',exact:true}).click();
  await expect.poll(()=>fs.stat(project).then(s=>s.size).catch(()=>0)).toBeGreaterThan(100);const saved=JSON.parse(await fs.readFile(project,'utf8'));assert.equal(saved.version,1);assert.equal(saved.document.history.present.generation.operation,'text_edit');
  await page.getByRole('button',{name:'Çizim',exact:true}).click();await page.mouse.click(rect.x+rect.width*.2,rect.y+rect.height*.2);
  await page.getByRole('button',{name:'Yazıyla Oluştur',exact:true}).click();const dialog=page.getByRole('dialog',{name:'Yazıyla Oluştur',exact:true});
  await dialog.getByLabel('Komut',{exact:true}).fill('Yağmurlu bir sokakta yürüyen beyaz bir kedi.');
  await dialog.getByRole('button',{name:'Üret',exact:true}).click();await expect(dialog.getByRole('button',{name:'İptal',exact:true})).toBeVisible();
  const cancelStarted=Date.now();await dialog.getByRole('button',{name:'İptal',exact:true}).click();await expect(dialog.getByRole('status')).toHaveText(/İptal|iptal/);const cancelUiMilliseconds=Date.now()-cancelStarted;
  await expect(dialog.getByRole('button',{name:'Üret',exact:true})).toBeVisible({timeout:10000});
  await dialog.getByRole('button',{name:'Üret',exact:true}).click();await expect(dialog.getByRole('button',{name:'Düzenleyicide Aç',exact:true})).toBeVisible({timeout:300000});
  await page.screenshot({path:path.join(output,'generated-preview.png')});await dialog.getByRole('button',{name:'Düzenleyicide Aç',exact:true}).click();
  const guard=page.getByRole('alertdialog',{name:'Değişiklikler kaydedilsin mi?'});await expect(guard).toBeVisible();expect(await page.locator('.canvas img').getAttribute('src')).toBe(applied);await guard.getByRole('button',{name:'Vazgeç',exact:true}).click();await expect(dialog).toBeVisible();await dialog.getByRole('button',{name:'Düzenleyicide Aç',exact:true}).click();await guard.getByRole('button',{name:'Kaydetmeden çık',exact:true}).click();
  await expect(page.locator('.canvas img')).toBeVisible();await expect(page.getByRole('button',{name:'Geri al',exact:true})).toBeDisabled();
  await page.getByRole('button',{name:'Kaydet',exact:true}).click();await page.getByRole('button',{name:'Görsel olarak kaydet (PNG)',exact:true}).click();await expect.poll(()=>fs.stat(png).then(s=>s.size).catch(()=>0)).toBeGreaterThan(1000);
  await page.getByRole('button',{name:'Başlangıç',exact:true}).click();await app.evaluate(({dialog},project)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[project]});},project);await page.getByRole('button',{name:'Proje Aç',exact:true}).click();await expect(page.locator('.canvas img')).toBeVisible();await expect.poll(()=>page.locator('.canvas img').evaluate(img=>[img.naturalWidth,img.naturalHeight])).toEqual([600,400]);
  assert.deepEqual(errors,[]);await fs.writeFile(path.join(output,'result.json'),JSON.stringify({passed:true,cancelUiMilliseconds,profileAcceptanceBypass:process.env.PIXELMEND_NATIVE_MEASUREMENT==='1'}));
  console.log('PASS: native edit preview/discard/apply/history/project, generation/cancel/editor/PNG');
 }catch(error){console.error('Renderer errors:',errors);if(page)await page.screenshot({path:path.join(output,'failure.png')}).catch(()=>{});throw error;}
 finally{if(page&&!page.isClosed())await page.evaluate(()=>window.pixelmend.confirmClose()).catch(()=>{});await app.close();await fs.rm(temp,{recursive:true,force:true});}
})().catch(error=>{console.error(error);process.exitCode=1;});
