const $ = id => document.getElementById(id);
const statuses = {passed:'Başarılı',failed:'Başarısız',pending:'Bekliyor',running:'Çalışıyor',not_installed:'Kurulu değil',unsupported:'Desteklenmiyor',insufficient_resources:'Kaynak yetersiz',cancelled:'İptal edildi',timeout:'Zaman aşımı',incomplete:'Tamamlanmadı'};
function render(state) {
  $('status').textContent = state.message;
  $('device').textContent = state.device || 'Motor hazırlanıyor…';
  $('start').disabled = state.phase !== 'ready';
  $('start').hidden = !['preparing','ready'].includes(state.phase);
  $('setup').hidden = !['preparing','ready'].includes(state.phase);
  $('cancel').hidden = state.phase !== 'running';
  $('progress').hidden = !['preparing','running'].includes(state.phase);
  $('notes-section').hidden = state.phase !== 'done';
  $('finish').hidden = state.phase !== 'done';
  $('reveal').hidden = !state.hasReport;
  $('models').replaceChildren(...(state.models || []).map(model=>{
    const item=document.createElement('li');item.textContent=`${model.name} — ${model.state==='ready' ? 'Hazır' : model.state==='unavailable' ? 'Bu sürümde kurulum sunulmuyor' : 'Kurulum veya sınama gerekli'}`;return item;
  }));
  $('install-choice').hidden = !state.downloadBytes;
  $('download-size').textContent = `Eksik modelleri indir (${(state.downloadBytes / 1024**3).toFixed(2)} GB)`;
  $('results').replaceChildren(...(state.tests || []).map(test=>{
    const item=document.createElement('li');item.textContent=`${test.name || test.id} — ${statuses[test.status] || test.status}`;return item;
  }));
}
async function invoke(action) { try { await action(); } catch { $('status').textContent='İşlem tamamlanamadı. Kısmi rapor klasörünü kontrol edin.'; } }
$('start').onclick=()=>invoke(()=>window.diagnostics.start({mode:document.querySelector('input[name="mode"]:checked').value,installMissing:$('install').checked}));
$('cancel').onclick=()=>invoke(()=>window.diagnostics.cancel());
$('finish').onclick=()=>invoke(()=>window.diagnostics.finish($('notes').value));
$('reveal').onclick=()=>invoke(()=>window.diagnostics.reveal());
window.diagnostics.onState(render);
window.diagnostics.state().then(render);
