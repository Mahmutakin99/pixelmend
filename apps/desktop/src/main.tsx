import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { StrokeHistory, imagePoint } from './strokes';
import './style.css';
declare global { interface Window { pixelmend: any } }

function App() {
  const history = useRef(new StrokeHistory()).current;
  const [asset,setAsset] = useState<any>();
  const [mode,setMode] = useState<'paint'|'erase'>('paint');
  const [brush,setBrush] = useState(28);
  const [color,setColor] = useState('#ff3b6b');
  const [job,setJob] = useState<any>();
  const [result,setResult] = useState<any>();
  const [showResult,setShowResult] = useState(false);
  const [notice,setNotice] = useState('Hazır');
  const [busy,setBusy] = useState(false);
  const locked = useRef(false);
  const [,refresh] = useState(0);
  const canvas = useRef<HTMLCanvasElement>(null);
  const drawing = useRef<[number,number][]>([]);
  const redraw = () => {
    if (!asset || !canvas.current) return;
    const c=canvas.current, ctx=c.getContext('2d')!;
    c.width=asset.width; c.height=asset.height;
    const active=drawing.current.length ? {mode,radius:brush,points:drawing.current} : undefined;
    for (const s of history.visible(active)) {
      ctx.globalCompositeOperation=s.mode==='erase'?'destination-out':'source-over';
      ctx.strokeStyle=color; ctx.fillStyle=color; ctx.lineWidth=s.radius; ctx.lineCap='round'; ctx.lineJoin='round';
      ctx.beginPath(); ctx.arc(...s.points[0],s.radius/2,0,Math.PI*2); ctx.fill();
      ctx.beginPath(); s.points.forEach((p,i)=>i?ctx.lineTo(...p):ctx.moveTo(...p)); ctx.stroke();
    }
    ctx.globalCompositeOperation='source-over';
  };
  useEffect(redraw,[asset,mode,brush,color,showResult]);
  useEffect(() => {
    if (!job?.job_id) return;
    let active=true; let timer: ReturnType<typeof setTimeout>;
    const poll=async()=>{
      try {
        const s=await window.pixelmend.job(job.job_id);
        if (!active) return;
        setJob(s);
        if (s.status==='completed') {
          const id=s.result_ids[0], uri=await window.pixelmend.result(job.job_id,id);
          if (!active) return;
          const size=s.result_details?.find((r:any)=>r.result_id===id);
          setResult({jobId:job.job_id,id,uri,...size}); setShowResult(true);
          setNotice(`İşlem tamamlandı — ${size?.width} × ${size?.height}. Sonucu kaydedebilirsiniz.`);
        } else if (s.status==='failed') setNotice(`Hata: ${s.error?.message || 'İşlem başarısız oldu.'}`);
        else if (s.status==='cancelled') setNotice('İşlem iptal edildi. Kaynak ve önceki sonuç korundu.');
        else { setNotice(s.status==='cancelling'?'İptal bekleniyor…':'İşleniyor…'); timer=setTimeout(poll,120); return; }
        locked.current=false; setBusy(false);
      } catch(error) {
        if (!active) return;
        setNotice(`Hata: İşlem durumu alınamadı: ${String(error)}`); locked.current=false; setBusy(false);
      }
    };
    void poll(); return()=>{active=false;clearTimeout(timer);};
  },[job?.job_id]);
  const report=async(fn:()=>Promise<any>)=>{
    try { return await fn(); }
    catch(error) { setNotice(`Hata: ${error instanceof Error?error.message:String(error)}`); }
  };
  const open=async()=>{
    if(locked.current)return;
    const a=await report(()=>window.pixelmend.openImage());
    if(a){history.clear();drawing.current=[];setAsset(a);setResult(undefined);setShowResult(false);setJob(undefined);setNotice(`${a.width} × ${a.height} görsel açıldı`);}
  };
  const pointer=(event:React.PointerEvent<HTMLCanvasElement>)=>{
    if(!asset||busy||showResult||!event.isPrimary)return;
    const p=imagePoint(event.clientX,event.clientY,event.currentTarget.getBoundingClientRect(),asset.width,asset.height);
    if(event.type==='pointerdown'&&event.button===0){event.currentTarget.setPointerCapture(event.pointerId);drawing.current=[p];}
    else if(event.type==='pointermove'&&drawing.current.length)drawing.current.push(p);
    else if(event.type==='pointerup'||event.type==='pointercancel'){
      if(drawing.current.length&&event.type==='pointerup'){
        drawing.current.push(p);history.add({mode,radius:brush,points:drawing.current});
        setNotice(mode==='paint'?'Maske boyandı. Sil veya LaMa ile işleyin.':'Maske silindi.');
      }
      drawing.current=[];refresh(n=>n+1);
    }
    redraw();
  };
  const process=async(algorithm='opencv_telea')=>{
    if(!asset||locked.current)return;
    locked.current=true;setBusy(true);setNotice('İş kuyruğa alınıyor…');redraw();
    const payload=algorithm==='lanczos'?{assetId:asset.asset_id,algorithms:[algorithm],scale:2}
      :{assetId:asset.asset_id,algorithms:[algorithm],mask:canvas.current!.toDataURL('image/png').split(',')[1]};
    const created=await report(()=>window.pixelmend.startJob(payload));
    if(created)setJob({...created,status:'queued'});else{locked.current=false;setBusy(false);}
  };
  const cancel=async()=>{
    if(!job||!busy)return;
    const value=await report(()=>window.pixelmend.cancel(job.job_id));
    if(value)setNotice('İptal istendi; motorun durması bekleniyor…');
  };
  const save=async()=>{
    if(!result)return;
    const path=await report(()=>window.pixelmend.save(result.jobId,result.id,'PNG'));
    if(path)setNotice(`Kaydedildi: ${path}`);else if(path===null)setNotice('Kaydetme iptal edildi. Sonuç korunuyor.');
  };
  const editHistory=(action:'undo'|'redo'|'clear')=>{
    history[action]();redraw();refresh(n=>n+1);
    setNotice(action==='undo'?'Son çizim geri alındı.':action==='redo'?'Geri alınan çizim yinelendi.':'Maske temizlendi.');
  };
  return <main><header><h1>PixelMend</h1>
    <button disabled={busy} onClick={open}>Görsel Aç</button>
    <button disabled={!asset||busy||showResult} onClick={()=>process()}>Sil</button>
    <button disabled={!busy||!job} onClick={cancel}>İptal</button>
    <button disabled={!result||busy} onClick={save}>Kaydet</button>
  </header><section className="workspace"><aside>
    <label>Fırça {brush}px<input disabled={busy} type="range" min="2" max="160" value={brush} onChange={e=>setBrush(+e.target.value)}/></label>
    <label>Maske rengi<input disabled={busy} aria-label="Maske rengi" type="color" value={color} onChange={e=>setColor(e.target.value)}/></label>
    <button disabled={busy||showResult} onClick={()=>setMode('paint')} aria-pressed={mode==='paint'}>Boya</button>
    <button disabled={busy||showResult} onClick={()=>setMode('erase')} aria-pressed={mode==='erase'}>Silgi</button>
    <button disabled={busy||showResult||!history.canUndo} onClick={()=>editHistory('undo')}>Geri al</button>
    <button disabled={busy||showResult||!history.canRedo} title="Geri alınan çizimi yeniden uygular" onClick={()=>editHistory('redo')}>Yinele</button>
    <button disabled={busy||showResult||!history.canUndo} onClick={()=>editHistory('clear')}>Maskeyi temizle</button><hr/>
    <button disabled={!asset||busy||showResult} onClick={()=>process('lama')}>LaMa</button>
    <button disabled={!asset||busy} onClick={()=>process('lanczos')}>Lanczos 2×</button>
    {result&&<><hr/><button disabled={busy} aria-pressed={!showResult} onClick={()=>setShowResult(false)}>Kaynak ve maske</button>
      <button disabled={busy} aria-pressed={showResult} onClick={()=>setShowResult(true)}>Sonuç</button>
      <span>Sonuç: {result.width} × {result.height}</span></>}
  </aside><article>{asset?<div className="canvas">
    <img alt={showResult?'İşlenmiş sonuç':'Kaynak görsel'} src={showResult?result?.uri:asset.preview}/>
    <canvas style={{visibility:showResult?'hidden':'visible'}} ref={canvas} onPointerDown={pointer} onPointerMove={pointer} onPointerUp={pointer} onPointerCancel={pointer}/>
  </div>:<div className="empty">Başlamak için Görsel Aç düğmesine basın.</div>}
    <p role="status" aria-live="polite">{notice}</p>
  </article></section></main>;
}
createRoot(document.getElementById('root')!).render(<App/>);
