const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {createReport, overallStatus, sanitize} = require('./diagnostic-report.cjs');

test('missing, cancelled and unexecuted cases cannot produce a successful report', () => {
  assert.equal(overallStatus([]), 'incomplete');
  assert.equal(overallStatus([{status:'passed'}, {status:'not_installed'}]), 'incomplete');
  assert.equal(overallStatus([{status:'cancelled'}]), 'incomplete');
  assert.equal(overallStatus([{status:'running'}]), 'incomplete');
  assert.equal(overallStatus([{status:'failed'}, {status:'not_installed'}]), 'failed');
  assert.equal(overallStatus([{status:'passed'}]), 'passed');
});

test('redacts Windows/POSIX personal paths, tokens, emails and escapes HTML', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pixelmend-report-'));
  try {
    const report = createReport(root, {appVersion:'test', mode:'standard'});
    report.record({id:'error', name:'<img src=x onerror=alert(1)>', status:'failed',
      detail:'Failed /Users/Ayşe/Desktop/private.png C:\\Users\\Ayşe\\secret.png token=abcdef user@example.com'});
    const checkpoint = JSON.parse(fs.readFileSync(path.join(report.directory,'sonuclar.json')));
    assert.equal(checkpoint.tests.length, 1);
    const archive = await report.finish('Kişisel /home/ayse/photo.png');
    assert.equal(fs.readFileSync(archive).readUInt32LE(0), 0x04034b50);
    const html = fs.readFileSync(path.join(report.directory,'Rapor.html'),'utf8');
    assert(!html.includes('<img'));
    assert(html.includes('&lt;img'));
    for (const secret of ['Ayşe','private.png','secret.png','abcdef','user@example.com']) {
      assert(!html.includes(secret), secret);
    }
    assert(!fs.readFileSync(path.join(report.directory,'kullanici-notlari.txt'),'utf8').includes('/home/ayse'));
  } finally { fs.rmSync(root,{recursive:true,force:true}); }
});

test('only bounded safe artifact names are accepted', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pixelmend-report-'));
  try {
    const report = createReport(root, {});
    assert.throws(()=>report.artifact('../personal.txt', Buffer.from('x')));
    assert.throws(()=>report.artifact('/absolute.png', Buffer.from('x')));
    report.artifact('gorseller/fixture.png', Buffer.from('fixture'));
    assert.equal(fs.readFileSync(path.join(report.directory,'gorseller/fixture.png'),'utf8'),'fixture');
    assert.equal(sanitize('X-PixelMend-Token: abc123'), 'X-PixelMend-Token: [REDACTED]');
  } finally { fs.rmSync(root,{recursive:true,force:true}); }
});
