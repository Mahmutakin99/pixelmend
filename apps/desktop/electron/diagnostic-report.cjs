// Offline, checkpointed reports. Only explicit test artifacts enter the archive.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {pipeline} = require('node:stream/promises');
const {ZipFile} = require('yazl');

const labels = {passed:'Başarılı', failed:'Başarısız', pending:'Bekliyor', running:'Çalışıyor',
  not_installed:'Kurulu değil', unsupported:'Desteklenmiyor', insufficient_resources:'Kaynak yetersiz',
  cancelled:'İptal edildi', timeout:'Zaman aşımı', incomplete:'Tam doğrulama tamamlanmadı'};
function overallStatus(tests) {
  if (tests.some(t => ['failed','timeout'].includes(t.status))) return 'failed';
  return tests.length && tests.every(t => t.status === 'passed') ? 'passed' : 'incomplete';
}
function sanitize(value) {
  if (typeof value === 'string') return value.slice(0, 16000)
    .replace(/((?:X-PixelMend-Token|token|authorization|api[_-]?key)\s*[:=]\s*)(?:Bearer\s+)?[^\s,;]+/gi, '$1[REDACTED]')
    .replace(/\b[A-Z]:[\\/][^\r\n<>"']*/gi, '[PATH]')
    .replace(/\/(?:Users|home|private|var|tmp|mnt|media)\/[^\r\n<>"']*/g, '[PATH]')
    .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, '[EMAIL]');
  if (Array.isArray(value)) return value.map(sanitize);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value)
    .filter(([key]) => !/^(?:hostname|username|serial|serialNumber|uuid|deviceId|path|filePath|token|environment)$/i.test(key))
    .map(([key, item]) => [key, sanitize(item)]));
  return value;
}
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function createReport(parent, metadata) {
  const id = crypto.randomBytes(4).toString('hex');
  const name = `PixelMend-Test-${new Date().toISOString().replace(/[:.]/g,'-')}-${id}`;
  const directory = path.join(parent, name);
  fs.mkdirSync(directory, {recursive:true, mode:0o700});
  const state = {schemaVersion:1, runnerVersion:1, id, startedAt:new Date().toISOString(),
    finishedAt:null, status:'incomplete', metadata:sanitize(metadata), tests:[], artifacts:[]};
  const files = new Set(['sonuclar.json', 'Rapor.html']);
  function atomic(filename, data) {
    const target = path.join(directory,filename);
    fs.mkdirSync(path.dirname(target), {recursive:true});
    fs.writeFileSync(`${target}.tmp`,data,{mode:0o600});
    fs.renameSync(`${target}.tmp`,target);
  }
  function checkpoint() {
    state.status = overallStatus(state.tests);
    atomic('sonuclar.json', JSON.stringify(state,null,2));
    atomic('Rapor.html', `<!doctype html><html lang="tr"><meta charset="utf-8">
<meta name="viewport" content="width=device-width"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'self'">
<title>PixelMend test raporu</title><style>body{font:16px system-ui;max-width:1000px;margin:40px auto;padding:0 24px;color:#222;background:#fafafa}table{border-collapse:collapse;width:100%}td,th{padding:12px;text-align:left;border-bottom:1px solid #ccc}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#0056b3}img{max-width:100%}</style>
<h1>PixelMend test raporu</h1><p><strong>${escapeHtml(labels[state.status])}</strong> · ${state.finishedAt ? 'Test sona erdi' : 'Kısmi rapor — test henüz tamamlanmadı'}</p>
<p>Bu rapor yalnız çalıştırılan senaryoları doğrular. Görsel kalite ve kullanım kolaylığı ayrıca insan tarafından değerlendirilmelidir. CPU sonucu GPU doğrulaması değildir.</p>
<table><thead><tr><th>Test</th><th>Sonuç</th><th>Süre</th></tr></thead><tbody>${state.tests.map(t=>`<tr><td>${escapeHtml(t.name || t.id)}</td><td>${escapeHtml(labels[t.status] || t.status)}</td><td>${Number.isFinite(t.durationMs) ? (t.durationMs/1000).toFixed(2)+' sn' : '—'}</td></tr><tr><td colspan="3"><pre>${escapeHtml(t.detail || '')}</pre></td></tr>`).join('')}</tbody></table>
<h2>Test görselleri</h2>${state.artifacts.filter(f=>f.endsWith('.png')).map(f=>`<p><a href="${escapeHtml(f)}">${escapeHtml(f)}</a></p>`).join('')}
<h2>Teknik ayrıntılar</h2><pre>${escapeHtml(JSON.stringify(state,null,2))}</pre>
<p>Kullanıcı değerlendirmesi varsa <a href="kullanici-notlari.txt">notlar dosyasındadır</a>. Hiçbir dosya otomatik gönderilmez.</p></html>`);
  }
  checkpoint();
  return {
    directory, state,
    metadata(value) { Object.assign(state.metadata,sanitize(value)); checkpoint(); },
    record(test) {
      if (!test.id || !Object.hasOwn(labels,test.status)) throw new Error('Invalid diagnostic result');
      const safe = sanitize(test), index = state.tests.findIndex(t=>t.id === safe.id);
      if (index < 0) state.tests.push(safe); else state.tests[index] = safe;
      checkpoint();
    },
    artifact(filename, bytes) {
      if (!/^(?:gorseller|gunlukler)\/[a-zA-Z0-9_-]+\.(?:png|txt|json)$/.test(filename)) throw new Error('Unsafe artifact name');
      // Text artifacts always pass the same sanitizer as errors and notes.
      atomic(filename, filename.endsWith('.png') ? bytes : sanitize(String(bytes)));
      files.add(filename);
      if (!state.artifacts.includes(filename)) state.artifacts.push(filename);
      checkpoint();
    },
    async finish(notes='') {
      state.finishedAt = new Date().toISOString();
      atomic('kullanici-notlari.txt',sanitize(notes)); files.add('kullanici-notlari.txt');
      checkpoint();
      const destination = path.join(parent,`${name}.zip`), zip = new ZipFile();
      const written = pipeline(zip.outputStream, fs.createWriteStream(`${destination}.tmp`,{mode:0o600}));
      for (const filename of files) zip.addFile(path.join(directory,filename),filename);
      zip.end();
      await written;
      fs.renameSync(`${destination}.tmp`,destination);
      return destination;
    },
  };
}
module.exports = {createReport, overallStatus, sanitize};
