import {useEffect,useState} from 'react';
import type {GenerativeRequest} from './bridge';
import type {GenerativeState} from './generative-session';
import type {Capabilities,ModelView} from './models';
import type {Stroke} from './document';
type Props={kind:'text_edit'|'text_to_image';state:GenerativeState;capabilities:Capabilities|null|undefined;models:ModelView[];
 source?:{assetId:string;selectionStrokes:Stroke[];paintStrokes:Stroke[]};locked?:boolean;
 start:(request:GenerativeRequest)=>void;cancel:()=>void;discard:()=>void;accept:()=>void;settings:()=>void;
 compare?:boolean;setCompare?:(value:boolean)=>void};
export function GenerativePanel(props:Props){
 const {kind,state,capabilities,models}=props;
 const [prompt,setPrompt]=useState(''),[language,setLanguage]=useState<'tr'|'en'>('tr'),[override,setOverride]=useState(''),
 [profile,setProfile]=useState<'low-resource'|'balanced'>('low-resource'),[aspect,setAspect]=useState<'square'|'landscape'|'portrait'>('square');
 useEffect(()=>{if(state.candidate?.info.original_prompt===prompt)setOverride(state.candidate.info.translated_prompt);},[state.candidate?.asset.asset_id]);
 const accepted=capabilities?.generative?.accepted_profiles??[];
 useEffect(()=>{if(!accepted.includes(profile)&&accepted.length)setProfile(accepted.includes('balanced')?'balanced':'low-resource');},[accepted.join(','),profile]);
 const installed=['flux2-klein-4b-mlx-q4',...(language==='tr'&&!override.trim()?['opus-mt-tc-big-tr-en-f16']:[])].every(id=>models.some(m=>m.id===id&&['installed','ready'].includes(m.state)));
 const busy=state.busy||!!props.locked;
 const reason=!capabilities?.generative?.platform_supported?'macOS 15+, Apple Silicon ve en az 16 GB RAM gerekir.':
 !capabilities.generative.runtime_installed?'Yerel çalışma paketi kurulu değil.':!installed?'Gerekli model paketlerini Ayarlar’dan kurun.':
 !accepted.includes(profile)?'Bu cihaz için üretim kalite ve kaynak kabulü henüz tamamlanmadı.':'';
 const run=()=>{
  const common={prompt,promptLanguage:language,profile,...(override.trim()?{englishOverride:override.trim()}: {})};
  if(kind==='text_edit'&&props.source)props.start({...common,operation:kind,...props.source});
  else if(kind==='text_to_image')props.start({...common,operation:kind,aspect});
 };
 return <section className="tool-group generative-panel" aria-label={kind==='text_edit'?'Yazıyla Düzenle':'Yazıyla Oluştur'}>
  <h2>{kind==='text_edit'?'Yazıyla Düzenle':'Yazıyla Oluştur'}</h2>
  <p className="hint">{kind==='text_edit'?'Bir alan seçin; üretim yalnız Uygula dediğinizde fotoğrafa geçer.':'Komutunuzdan yeni, opak bir görsel oluşturun.'} İşlemler bu Mac’te çalışır.</p>
  <label>Komut<textarea rows={4} value={prompt} disabled={busy} placeholder={kind==='text_edit'?'Seçili yere oturan turuncu bir kedi ekle.':'Yağmurlu bir sokakta yürüyen beyaz bir kedi.'} onChange={e=>{setPrompt(e.target.value);setOverride('');}}/></label>
  <p className="hint">{[...prompt].length}/1000 karakter</p>
  <label>Çalışma profili<select value={profile} disabled={busy} onChange={e=>setProfile(e.target.value as typeof profile)}>
   <option value="low-resource">Düşük kaynak{!accepted.includes('low-resource')?' · kabul bekliyor':''}</option>
   <option value="balanced" disabled={!accepted.includes('balanced')}>Dengeli{!accepted.includes('balanced')?' · kabul bekliyor':''}</option>
  </select></label>
  {kind==='text_to_image'&&<label>Oran<select value={aspect} disabled={busy} onChange={e=>setAspect(e.target.value as typeof aspect)}><option value="square">Kare · {profile==='balanced'?'768×768':'512×512'}</option><option value="landscape">Yatay 4:3 · {profile==='balanced'?'1024×768':'640×480'}</option><option value="portrait">Dikey 3:4 · {profile==='balanced'?'768×1024':'480×640'}</option></select></label>}
  {kind==='text_edit'&&<p className="hint">Ayrıntı {profile==='balanced'?768:512} piksel çalışma çözünürlüğüyle sınırlıdır. Şeffaf boşluğa nesne eklenmez.</p>}
  <details><summary>Kullanılan komut ve gelişmiş ayarlar</summary>
   <label>Komut dili<select value={language} disabled={busy} onChange={e=>{setLanguage(e.target.value as typeof language);setOverride('');}}><option value="tr">Türkçe · yerel çeviri</option><option value="en">English</option></select></label>
   <label>İngilizce karşılığını düzelt<textarea rows={3} disabled={busy} value={override} placeholder={state.candidate?.info.translated_prompt??'Boş bırakılırsa yerel çeviri kullanılır.'} onChange={e=>setOverride(e.target.value)}/></label>
   {state.candidate&&<><p>Seed: <code>{state.candidate.info.seed}</code></p><p className="used-prompt">{state.candidate.info.used_prompt}</p></>}
  </details>
  {reason&&<p role="note">{reason}</p>}
  {!installed&&<button disabled={busy} onClick={props.settings}>Model kurulumunu aç</button>}
  {state.error&&<p role="alert" className="error">{state.error} Komutu yeniden yazabilir veya İngilizce karşılığını girebilirsiniz.</p>}
  <p role="status" aria-live="polite">{state.phase}</p>
  {state.busy?<><progress aria-label="Yerel üretim sürüyor"/><button onClick={props.cancel}>İptal</button></>:
   <button disabled={busy||!!reason||!prompt.trim()||[...prompt].length>1000} onClick={run}>{state.candidate?'Başka sonuç üret':'Üret'}</button>}
  {state.candidate&&<>
   {kind==='text_edit'&&<label className="lock"><input type="checkbox" checked={props.compare??false} onChange={e=>props.setCompare?.(e.target.checked)}/> Orijinali göster</label>}
   <button disabled={busy} onClick={props.accept}>{kind==='text_edit'?'Uygula':'Düzenleyicide Aç'}</button><button disabled={busy} onClick={props.discard}>Vazgeç</button>
  </>}
 </section>;
}
