const { _electron: electron } = require('@playwright/test');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  const temp = await fs.mkdtemp(path.join(os.tmpdir(), 'pixelmend-paint-'));
  const source = path.join(temp, 'source.png');
  const app = await electron.launch(process.env.PIXELMEND_E2E_APP
    ? { executablePath: process.env.PIXELMEND_E2E_APP, args: [`--user-data-dir=${temp}/profile`] }
    : { args: ['.', `--user-data-dir=${temp}/profile`] });
  const page = await app.firstWindow(); const errors = [];
  page.on('pageerror', error => errors.push(error.stack || error.message));
  try {
    const png = await page.evaluate(() => { const c=document.createElement('canvas');c.width=32;c.height=32;c.getContext('2d').fillRect(0,0,32,32);return c.toDataURL().split(',')[1]; });
    await fs.writeFile(source, Buffer.from(png, 'base64'));
    await app.evaluate(({dialog}, file) => { dialog.showOpenDialog = async () => ({canceled:false,filePaths:[file]}); }, source);
    await page.getByRole('button', {name:'Görsel Aç',exact:true}).click();
    const canvas = page.locator('canvas.mask'); const box = await canvas.boundingBox();
    await page.mouse.move(box.x + box.width/2, box.y + box.height/2); await page.mouse.down(); await page.mouse.up();
    await page.waitForTimeout(500);
    const headings = await page.getByRole('heading',{name:'PixelMend'}).count();
    if (headings !== 1) console.error('Renderer body after pointerup:', await page.locator('body').innerText(), 'errors:', errors);
    assert.equal(headings, 1, 'renderer remains mounted after paint pointerup');
    assert.deepEqual(errors, [], `renderer page errors: ${errors.join('\n')}`);
    console.log('PASS: paint pointerup keeps packaged renderer mounted');
  } finally { await app.close(); }
})().catch(error => { console.error(error); process.exitCode=1; });
