// Runs the real Electron app and sidecar; only native file dialogs are automated.
const { _electron: electron, expect } = require('@playwright/test');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  const artifacts = path.resolve(process.env.PIXELMEND_E2E_OUTPUT || 'test-results/editor');
  await fs.mkdir(artifacts, {recursive: true});
  const temp = await fs.mkdtemp(path.join(os.tmpdir(), 'pixelmend-editor-'));
  const sourcePath = path.join(temp, 'source.png');
  const savedPath = path.join(temp, 'saved.png');
  const launch = process.env.PIXELMEND_E2E_APP
    ? {executablePath: process.env.PIXELMEND_E2E_APP, args: [`--user-data-dir=${temp}/profile`]}
    : {args: ['.', `--user-data-dir=${temp}/profile`]};
  const application = await electron.launch({...launch, timeout: 30000});
  let page;
  const errors = [];
  try {
    page = await application.firstWindow();
    page.on('pageerror', error => errors.push(error.message));
    await expect(page.getByRole('heading', {name: 'PixelMend', exact: true})).toBeVisible();
    const png = await page.evaluate(() => {
      const c = document.createElement('canvas'); c.width = 96; c.height = 64;
      const x = c.getContext('2d'); x.fillStyle = '#b4b4b4'; x.fillRect(0, 0, 96, 64);
      x.fillStyle = '#000'; x.fillRect(43, 27, 10, 10);
      return c.toDataURL().split(',')[1];
    });
    await fs.writeFile(sourcePath, Buffer.from(png, 'base64'));
    await application.evaluate(({dialog}, paths) => {
      dialog.showOpenDialog = async () => ({canceled: false, filePaths: [paths.sourcePath]});
      dialog.showSaveDialog = async () => ({canceled: false, filePath: paths.savedPath});
    }, {sourcePath, savedPath});
    await page.getByRole('button', {name: 'Görsel Aç', exact: true}).click();
    await expect(page.locator('.canvas img')).toBeVisible();
    const canvas = page.locator('.canvas canvas.mask');
    const paintCanvas = page.locator('.canvas canvas.paint');
    const rect = await canvas.boundingBox();
    const point = {x: rect.x + rect.width / 2, y: rect.y + rect.height / 2};
    await page.mouse.move(point.x, point.y);
    await page.mouse.down();
    const alpha = () => paintCanvas.evaluate(c => c.getContext('2d').getImageData(48,32,1,1).data[3]);
    assert(await alpha() > 0, 'paint visible before mouse up');
    await page.mouse.up();
    await expect(page.getByRole('button', {name:'Yinele',exact:true})).toBeDisabled();
    // A long, angular translucent stroke must not change when it becomes history.
    // This caught the prior mismatch: live segments used round caps, replay used a mitered path.
    const zigzag = [
      [rect.x + rect.width * .18, rect.y + rect.height * .22],
      [rect.x + rect.width * .31, rect.y + rect.height * .57],
      [rect.x + rect.width * .44, rect.y + rect.height * .19],
      [rect.x + rect.width * .57, rect.y + rect.height * .55],
    ];
    await page.mouse.move(...zigzag[0]); await page.mouse.down();
    for (const point of zigzag.slice(1)) await page.mouse.move(...point);
    const liveStroke = await paintCanvas.evaluate(c => c.toDataURL());
    await page.mouse.up();
    await expect.poll(() => paintCanvas.evaluate(c => c.toDataURL())).toBe(liveStroke);
    await page.getByRole('button', {name:'Geri al',exact:true}).click();
    await page.getByRole('button', {name:'Geri al',exact:true}).click();
    assert.equal(await alpha(),0);
    await page.getByRole('button', {name:'Yinele',exact:true}).click();
    assert(await alpha() > 0);
    await page.getByRole('button', {name:'Silgi',exact:true}).click();
    await page.mouse.move(point.x,point.y); await page.mouse.down();
    assert.equal(await alpha(),0,'erase visible before mouse up');
    await page.mouse.up();
    assert.equal(await alpha(),0,'paint eraser stays erased after pointerup');
    await page.getByRole('button', {name:'Geri al',exact:true}).click();
    assert(await alpha() > 0);
    await page.getByRole('button', {name: 'Nesne Boyası', exact: true}).click();
    await page.mouse.move(point.x, point.y); await page.mouse.down(); await page.mouse.up();
    const maskAlpha=()=>canvas.evaluate(c=>c.getContext('2d').getImageData(48,32,1,1).data[3]);
    assert.equal(await maskAlpha(),255,'selection is opaque data under translucent display');
    await page.getByRole('button',{name:'Seçimi Sil',exact:true}).click();
    await page.mouse.move(point.x,point.y);await page.mouse.down();
    assert.equal(await maskAlpha(),0,'selection eraser is fully opaque');
    await page.mouse.up();assert.equal(await maskAlpha(),0,'selection stays erased after pointerup');
    await page.getByRole('button',{name:'Geri al',exact:true}).click();
    assert.equal(await maskAlpha(),255,'undo restores erased selection');
    await page.getByRole('button', {name: 'Nesneyi Sil', exact: true}).click();
    await expect(page.getByRole('region',{name:'İşlem durumu'})).toBeVisible();
    await expect(page.getByRole('button',{name:'Nesneyi Sil',exact:true})).toBeDisabled();
    await expect(page.getByRole('button', {name: 'Uygula', exact: true})).toBeVisible({timeout: 120000});
    await page.getByRole('button', {name: 'Vazgeç', exact: true}).click();
    await expect(page.getByRole('status')).toContainText('Seçim korunuyor');
    await page.getByRole('button', {name: 'Nesneyi Sil', exact: true}).click();
    await expect(page.getByRole('button', {name: 'Uygula', exact: true})).toBeVisible({timeout: 120000});
    await page.getByRole('button', {name: 'Uygula', exact: true}).click();
    await page.getByRole('button', {name: 'Kaydet', exact: true}).click();
    await page.getByRole('button', {name: 'Görsel olarak kaydet (PNG)', exact: true}).click();
    await expect(page.getByRole('status')).toContainText('kaydedildi');
    assert((await fs.stat(savedPath)).size > 0);
    await page.screenshot({path: path.join(artifacts, 'opencv-result.png')});
    await page.getByRole('button',{name:'2× Büyüt',exact:true}).click();
    await expect(page.getByRole('button',{name:'Uygula',exact:true})).toBeVisible({timeout:15000});
    await page.getByRole('button',{name:'Uygula',exact:true}).click();
    await expect(page.getByRole('status')).toContainText('2× büyütüldü',{timeout:15000});
    await expect.poll(()=>page.locator('.canvas img').evaluate(img=>[img.naturalWidth,img.naturalHeight])).toEqual([192,128]);
    assert.equal(await page.getByRole('button', {name: 'Ayarlar', exact: true}).count(), 0, 'editor settings button is removed');
    await page.getByRole('button', {name: 'Başlangıç', exact: true}).click();
    await expect(page.getByRole('heading', {name: 'Değişiklikler kaydedilsin mi?', exact: true})).toBeVisible();
    await page.getByRole('dialog').getByRole('button', {name: 'Kaydet', exact: true}).click();
    await expect(page.getByRole('heading', {name: 'Nasıl kaydetmek istersiniz?', exact: true})).toBeVisible();
    await page.getByRole('button', {name: 'Vazgeç', exact: true}).click();
    await expect(page.locator('.canvas img')).toBeVisible();
    await page.getByRole('button', {name: 'Başlangıç', exact: true}).click();
    await page.getByRole('button', {name: 'Kaydetmeden çık', exact: true}).click();
    await expect(page.getByRole('button', {name: 'Görsel Aç', exact: true})).toBeVisible();
    await page.screenshot({path:path.join(artifacts,'lanczos-result.png')});
    assert.deepEqual(errors, []);
    console.log('PASS: real Electron paint/paint eraser, undo/redo, remove preview/discard/apply, export and 2x upscale');
  } catch (error) {
    console.error('Renderer errors:',errors);
    if (page) {
      console.error('UI status:', await page.getByRole('status').textContent({timeout:2000}).catch(()=>'(renderer unavailable)'));
      await page.screenshot({path: path.join(artifacts, 'failure.png')});
    }
    throw error;
  } finally {
    await application.close();
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
