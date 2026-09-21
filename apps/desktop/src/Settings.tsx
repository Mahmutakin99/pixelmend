import {useEffect, useState} from 'react';
import {allowedActions, formatBytes, type Capabilities, type ModelAction, type ModelView} from './models';
import {normalizePreferences, type PixelMendPreferences} from './preferences';
import type {Preferences} from './bridge';

const stateLabels: Record<string, string> = {absent: 'Kurulum gerekli', unavailable: 'Doğrulama bekliyor', missing: 'Kurulum gerekli', downloading: 'İndiriliyor', verifying: 'Doğrulanıyor', installed: 'Sınanmadı', ready: 'Hazır', failed: 'Başarısız', error: 'Başarısız', probing: 'Sınanıyor', deleting: 'Siliniyor'};
const tierCopy = {
  fast: {title: 'Hızlı', copy: 'Daha düşük sistem gereksinimleri ve kısa bekleme süresi için önerilir.'},
  balanced: {title: 'Dengeli', copy: 'Günlük kullanım için önerilir. İşlem süresi ve ayrıntı kalitesini dengeler.'},
  advanced: {title: 'Gelişmiş', copy: 'Güçlü sistemler ve zor görseller için önerilir. Daha fazla bellek kullanabilir.'},
} as const;
type Section = 'general' | 'canvas' | 'models' | 'performance' | 'about';

function ModelCard({model, refresh}: {model: ModelView; refresh: () => void}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const allowed = allowedActions(model);
  const act = async (action: ModelAction) => {
    setPending(true); setError('');
    try { await window.pixelmend.modelAction(model.id, action); refresh(); }
    catch (cause) { setError(String(cause)); }
    finally { setPending(false); }
  };
  const primary = allowed.includes('install-local') ? ['install-local', 'Yerel ONNX seç'] as const
    : allowed.includes('install') ? ['install', 'Modeli indir'] as const
    : allowed.includes('probe') ? ['probe', 'Yeniden ölç'] as const : null;
  return <article className="model-card" aria-label={`${model.name} modeli`}>
    <div><h3>{model.name}</h3><p>{stateLabels[model.state] || model.state}{model.in_use ? ' · Kullanımda' : ''}</p></div>
    <p className="model-summary">{model.description || (model.state === 'ready' ? 'Bu Mac’te doğrulandı ve kullanıma hazır.' : 'Kurulum ve kısa bir çalışma sınaması tamamlanınca kullanılabilir.')}</p>
    <div className="model-meta"><span>{model.size_bytes ? formatBytes(model.size_bytes) : 'Boyut henüz doğrulanmadı'}</span><span>{model.source === 'local' ? 'Yerel doğrulanmış dosya' : model.verified_manifest ? 'Yayımlanmış model' : 'Kurulum henüz sunulmuyor'}</span></div>
    {['downloading', 'verifying'].includes(model.state) && <progress aria-label={`${model.name} kurulumu`} value={model.downloaded_bytes} max={model.size_bytes || 1}/>} 
    <div className="model-actions">
      {primary && <button className="primary" disabled={pending} onClick={() => act(primary[0])}>{primary[1]}</button>}
      {allowed.includes('delete') && <button disabled={pending} onClick={() => act('delete')}>Kaldır</button>}
      {allowed.includes('cancel') && <button disabled={pending} onClick={() => act('cancel')}>İptal</button>}
    </div>
    {(error || model.error) && <p className="inline-error" role="alert">{error || model.error?.message}</p>}
    <details><summary>Teknik ayrıntılar</summary><dl className="technical-facts"><dt>Sağlayıcı</dt><dd>{model.probe?.selected_provider || 'Henüz ölçülmedi'}</dd><dt>En az bellek</dt><dd>{model.minimum_memory_bytes ? formatBytes(model.minimum_memory_bytes) : 'Ölçüm tamamlanmadı'}</dd><dt>Önerilen bellek</dt><dd>{model.recommended_memory_bytes ? formatBytes(model.recommended_memory_bytes) : 'Ölçüm tamamlanmadı'}</dd><dt>Lisans</dt><dd>{model.license_id || 'Doğrulama bekliyor'}</dd><dt>Revision</dt><dd>{model.revision || 'Doğrulama bekliyor'}</dd><dt>SHA-256</dt><dd>{model.sha256 || 'Doğrulama bekliyor'}</dd></dl></details>
  </article>;
}

export function Settings({value, close, set, models, capabilities, refresh, error, onZoomSensitivity = () => {}}: {value: Preferences | undefined; close: () => void; set: (v: Preferences) => void; models: ModelView[]; capabilities: Capabilities | undefined; refresh: () => void; error: string; onZoomSensitivity?: (value: number) => void}) {
  const [section, setSection] = useState<Section>('general');
  const [settingsError, setSettingsError] = useState('');
  const v = normalizePreferences(value || {});
  const update = async (next: PixelMendPreferences) => {
    try { await window.pixelmend.setSettings(next); set(next); }
    catch (cause) { setSettingsError(String(cause)); }
  };
  useEffect(() => { const key = (event: KeyboardEvent) => { if (event.key === 'Escape') close(); }; window.addEventListener('keydown', key); return () => window.removeEventListener('keydown', key); }, [close]);
  const nav: Array<[Section, string]> = [['general', 'Genel'], ['canvas', 'Tuval ve araçlar'], ['models', 'AI modelleri'], ['performance', 'Performans'], ['about', 'Hakkında']];
  return <section className="settings-page" aria-label="Ayarlar">
    <header className="settings-header"><div><p className="eyebrow">PixelMend</p><h1>Ayarlar</h1></div><button onClick={close}>Bitti</button></header>
    <div className="settings-layout"><nav className="settings-nav" aria-label="Ayar bölümleri">{nav.map(([id, label]) => <button key={id} className={section === id ? 'selected' : ''} aria-current={section === id ? 'page' : undefined} onClick={() => setSection(id)}>{label}</button>)}</nav>
      <main className="settings-content">
        {section === 'general' && <section className="settings-section"><h2>Genel</h2><p>Görünüm sistem tercihini takip eder. Değişiklikler anında uygulanır.</p><label className="setting-row"><span><strong>Tema</strong><small>Uygulamanın görünümü</small></span><select value={v.theme} onChange={event => update({...v, theme: event.target.value})}><option value="system">Sistem</option><option value="dark">Koyu</option><option value="light">Açık</option></select></label><div className="setting-row"><span><strong>Dil</strong><small>Bu sürüm Türkçe olarak sunulur.</small></span><span>Türkçe</span></div></section>}
        {section === 'canvas' && <section className="settings-section"><h2>Tuval ve araçlar</h2><p>Yakınlaştırma davranışını çalışma biçiminize göre ayarlayın.</p><label className="range-setting"><span><strong>Yakınlaştırma hassasiyeti</strong><small>⌘/Ctrl + tekerlek ile yakınlaştırma hızı</small></span><input aria-label="Yakınlaştırma hassasiyeti" type="range" min="0.5" max="4" step="0.5" value={v.zoomSensitivity} onChange={event => { const zoomSensitivity = Number(event.target.value); onZoomSensitivity(zoomSensitivity); void update({...v, zoomSensitivity}); }}/><output>{v.zoomSensitivity.toFixed(1)}×</output></label><p className="tip">Tuvalde orta tuşla veya tekerleğe basılı sürükleyerek görseli taşıyabilirsiniz.</p></section>}
        {section === 'models' && <section className="settings-section"><h2>AI modelleri</h2><p>Her araç için son seçiminiz hatırlanır. Dengeli model ilk kullanımda seçilir.</p><div className="tier-grid">{(Object.keys(tierCopy) as Array<keyof typeof tierCopy>).map(tier => <article className={`tier-card ${tier === 'balanced' ? 'recommended' : ''}`} key={tier}><h3>{tierCopy[tier].title}{tier === 'balanced' && <span>Önerilen</span>}</h3><p>{tierCopy[tier].copy}</p></article>)}</div><h3 className="section-label">Kurulu modeller</h3>{models.map(model => <ModelCard key={model.id} model={model} refresh={refresh}/>)}{!models.length && <p>Model bilgileri yükleniyor.</p>}</section>}
        {section === 'performance' && <section className="settings-section"><h2>Performans</h2><p>PixelMend, her model için gerçek kısa sınamayı geçen en hızlı yolu seçer. Hızlandırıcı kullanılamazsa, aynı model kaynaklar uygunsa CPU’da bir kez yeniden denenir.</p><label className="setting-row"><span><strong>Çalışma modu</strong><small>Model seçimini değiştirmez.</small></span><select value={v.performanceMode} onChange={event => update({...v, performanceMode: event.target.value as PixelMendPreferences['performanceMode']})}><option value="automatic">Otomatik hız</option><option value="low-resource">Düşük kaynak kullanımı</option></select></label><dl className="hardware-facts"><dt>Cihaz</dt><dd>{capabilities?.accelerator.identity || 'Bu sistem cihaz adını sağlamıyor'}</dd><dt>Toplam bellek</dt><dd>{formatBytes(capabilities?.host_ram_total_bytes)}</dd><dt>Şu an kullanılabilir</dt><dd>{formatBytes(capabilities?.host_ram_available_bytes)}</dd><dt>AI çalışma yolu</dt><dd>{capabilities?.execution_providers.includes('CoreMLExecutionProvider') ? 'Apple Core ML + CPU' : 'CPU çalışma yolu'}</dd><dt>Bellek türü</dt><dd>{capabilities?.accelerator.memory_kind === 'unified' ? 'Birleşik bellek — GPU’ya özel boş VRAM ölçülmez' : 'Bu sistem bu bilgiyi sağlamıyor'}</dd><dt>Çıktı güvenlik sınırı</dt><dd>{capabilities?.policy?.max_output_pixels ? `${capabilities.policy.max_output_pixels / 1e6} MP` : 'Bilgi bekleniyor'}</dd></dl><button onClick={refresh}>Bilgileri yenile</button></section>}
        {section === 'about' && <section className="settings-section"><h2>Hakkında</h2><p>PixelMend fotoğraflarınızı bu bilgisayarda işler. Görsel verisi dış servislere gönderilmez.</p><dl className="hardware-facts"><dt>Sürüm</dt><dd>1.0.0-rc.2</dd><dt>Çalışma sağlayıcıları</dt><dd>{capabilities?.execution_providers.join(', ') || 'Bilgi bekleniyor'}</dd></dl></section>}
        {(error || settingsError) && <p className="inline-error" role="alert">{error || settingsError}</p>}
      </main>
    </div>
  </section>;
}
