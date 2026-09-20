import {useEffect,useState} from 'react';
import {allowedActions,formatBytes,type ModelView,type ModelAction,type Capabilities} from './models';
import type {Preferences} from './bridge';

const stateLabels:Record<string,string>={unavailable:'Henüz yayınlanmadı',missing:'İndirilmedi',absent:'İndirilmedi',not_installed:'İndirilmedi',waiting:'Bekliyor',downloading:'İndiriliyor',verifying:'Doğrulanıyor',installed:'Sınanmadı',ready:'Hazır',failed:'Başarısız',error:'Başarısız',cancelled:'İptal edildi',probing:'Sınanıyor',deleting:'Siliniyor'};
const probeLabels:Record<string,string>={unmeasured:'Ölçülmedi',running:'Sınanıyor',passed:'Başarılı',failed:'Başarısız'};

// Model download requires explicit local consent after size and license are displayed.
function ModelCard({model,refresh}:{model:ModelView;refresh:()=>void}) {
  const [pending,setPending]=useState(false),[consent,setConsent]=useState<ModelAction|null>(null),[error,setError]=useState('');
  const allowed=allowedActions(model);
  const act=async(action:ModelAction)=>{setPending(true);setError('');try{await window.pixelmend.modelAction(model.id,action);setConsent(null);refresh();}catch(error){setError(String(error));}finally{setPending(false);}};
  return <section className="model-card" aria-label={model.name}>
    <h3>{model.name}</h3><p>{stateLabels[model.state]||model.state}{model.in_use?' · Kullanımda':''}</p>
    <dl className="model-facts"><dt>Kaynak</dt><dd>{model.source === "local" ? "Doğrulanmış yerel ONNX" : "Yayımlanmış model"}</dd><dt>Model boyutu</dt><dd>{formatBytes(model.size_bytes)}</dd><dt>Lisans</dt><dd>{model.license_id||'Bilinmiyor'} {model.license_url&&<span className="license-url">{model.license_url}</span>}</dd>
      <dt>Depolanan boyut</dt><dd>{formatBytes(model.stored_bytes)}</dd></dl>
    {['downloading','verifying'].includes(model.state)&&<div><progress aria-label={`${model.name} indirme`} value={model.downloaded_bytes} max={model.size_bytes||1}/><p>{formatBytes(model.downloaded_bytes)} / {formatBytes(model.size_bytes)}</p></div>}
    <div className="modal-actions">
      <button disabled={pending||!allowed.includes('install-local')} onClick={()=>act('install-local')}>Yerel ONNX kur</button>
      <button disabled={pending||!allowed.includes('install')} onClick={()=>setConsent('install')}>İndir</button>
      <button disabled={pending||!allowed.includes('cancel')} onClick={()=>act('cancel')}>İndirmeyi iptal et</button>
      <button disabled={pending||!allowed.includes('retry')} onClick={()=>setConsent('retry')}>Yeniden dene</button>
      <button disabled={pending||!allowed.includes('probe')} onClick={()=>act('probe')}>Sağlayıcıyı sına</button>
      <button disabled={pending||!allowed.includes('delete')} onClick={()=>setConsent('delete')}>Modeli sil</button>
    </div>
    {consent&&<div className="consent" role="group" aria-label="Model işlem onayı"><p>{consent==='delete'?'Yerel model dosyası silinecek.':`${formatBytes(model.size_bytes)} indirilecek. Lisans: ${model.license_id||'Bilinmiyor'}. İndirmeyi onaylıyor musunuz?`}</p>{consent!=='delete'&&<p className="license-url">{model.license_url||'Lisans bağlantısı bilinmiyor'}</p>}<button disabled={pending} onClick={()=>act(consent)}>{consent==='delete'?'Silmeyi onayla':'İndirmeyi onayla'}</button><button disabled={pending} onClick={()=>setConsent(null)}>Vazgeç</button></div>}
    {(error||model.error)&&<p role="alert">{error||`${model.error?.code}: ${model.error?.message}`}</p>}
    <details><summary>Teknik ayrıntılar — revision, bütünlük ve sağlayıcı ölçümü</summary><dl className="model-facts"><dt>Revision</dt><dd>{model.revision||'Yayınlanmadı'}</dd><dt>Etkin revision</dt><dd>{model.active_revision||'Yayınlanmadı'}</dd><dt>SHA-256</dt><dd>{model.sha256||'Yayınlanmadı'}</dd><dt>Son kullanım</dt><dd>{model.last_used_at||'Ölçülmedi'}</dd><dt>Eski revision</dt><dd>{model.stale_revisions?.length ? 'Temizleme için kullanıcı eylemi gerekir.' : 'Yok'}</dd><dt>Sağlayıcı sınaması</dt><dd>{probeLabels[model.probe?.status||'unmeasured']}</dd><dt>Seçilen sağlayıcı</dt><dd>{model.probe?.selected_provider||'Ölçülmedi'}</dd><dt>Oturum sağlayıcıları</dt><dd>{model.probe?.providers.join(', ')||'Ölçülmedi'}</dd><dt>Ölçüm zamanı</dt><dd>{model.probe?.measured_at||'Ölçülmedi'}</dd></dl></details>
  </section>;
}
export function Settings({value,close,set,models,capabilities,refresh,error}:{value:Preferences|undefined;close:()=>void;set:(v:Preferences)=>void;models:ModelView[];capabilities:Capabilities|undefined;refresh:()=>void;error:string}) {
  const v=value||{language:'tr',theme:'system'};
  const [settingsError,setSettingsError]=useState('');
  const update=async(next:Preferences)=>{try{await window.pixelmend.setSettings(next);set(next);}catch(error){setSettingsError(String(error));}};
  useEffect(()=>{const onKeyDown=(event:KeyboardEvent)=>{if(event.key==='Escape')close();};window.addEventListener('keydown',onKeyDown);return()=>window.removeEventListener('keydown',onKeyDown);},[close]);
  return <div className="modal settings-modal" role="dialog" aria-modal="true" aria-label="Ayarlar"><div className="settings-title"><h2>Ayarlar</h2><button onClick={close}>Kapat</button></div><div className="settings-body">
    <section className="settings-section" aria-labelledby="general-settings"><h2 id="general-settings">Genel</h2><div className="preferences"><p>Dil: Türkçe</p><label>Tema <select value={v.theme} onChange={e=>update({...v,theme:e.target.value})}><option value="system">Sistem</option><option value="dark">Koyu</option><option value="light">Açık</option></select></label></div></section>
    <h2>Performans</h2><p>Donanım bilgileri gözlemdir. Modelin kullanılabilmesi için sağlayıcı sınaması başarılı olmalıdır.</p>
    <dl className="performance-facts"><dt>Toplam / kullanılabilir RAM</dt><dd>{formatBytes(capabilities?.host_ram_total_bytes)} / {formatBytes(capabilities?.host_ram_available_bytes)}</dd><dt>CPU sayısı</dt><dd>{capabilities?.cpu_count??'Ölçülmedi'}</dd><dt>Kurulu sağlayıcılar</dt><dd>{capabilities?.execution_providers.join(', ')||'Ölçülmedi'}</dd><dt>Hızlandırıcı</dt><dd>{capabilities?.accelerator.identity||'Ölçülmedi'}</dd><dt>Bellek türü</dt><dd>{!capabilities?.accelerator.memory_kind||capabilities.accelerator.memory_kind==='unknown'?'Ölçülmedi':capabilities.accelerator.memory_kind}</dd><dt>Cihaz bütçesi / boşluğu</dt><dd>{formatBytes(capabilities?.accelerator.device_budget_bytes)} / {formatBytes(capabilities?.accelerator.device_headroom_bytes)}</dd><dt>Çıktı sınırı</dt><dd>{capabilities?.policy?.max_output_pixels?`${capabilities.policy.max_output_pixels/1e6} MP`:'Ölçülmedi'}</dd></dl>
    <button onClick={refresh}>Bilgileri yenile</button>{(error||settingsError)&&<p role="alert">{error||settingsError}</p>}<h2>Modeller</h2>
    {models.map(model=><ModelCard key={model.id} model={model} refresh={refresh}/>)}{!models.length&&<p>Model bilgileri bekleniyor.</p>}</div>
  </div>;
}
