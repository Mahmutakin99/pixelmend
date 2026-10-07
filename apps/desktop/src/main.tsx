import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  addStroke,
  applyResult,
  applyGenerativeResult,
  createGeneratedDocument,
  parseDocument,
  createDocument,
  redo,
  undo,
  type EditorDocument,
  type Stroke,
} from "./document";
import { drawStroke, drawStrokeSegment, drawStrokeStart, previewBrush } from "./brush";
import { imagePoint } from "./strokes";
import { boundedPan, wheelZoom } from "./zoom";
import { fitDimension, preserveDimensions, targetIsValid, type Dimensions } from "./upscale";
import { resultNotice } from "./job-result";
import { userError, type ErrorContext, type UserError } from "./errors";
import { canvasCursor } from "./cursor-visibility";
import { documentFingerprint, isDocumentDirty } from "./document-state";
import { normalizePreferences } from "./preferences";
import { Settings as PerformanceSettings } from "./Settings";
import { useModels } from "./useModels";
import { selectableModels, isModelPreparing, modelAvailability } from "./models";
import { showsAiControls } from "./ai-controls";
import {useGenerative} from "./useGenerative";
import {GenerativePanel} from "./GenerativePanel";
import type {GenerativeRequest} from "./bridge";
import "./bridge";
import "./style.css";
import "./tokens.css";
type Tool = "paint" | "paintErase" | "select" | "selectErase";
type Inspector = "draw" | "remove" | "upscale" | "view" | "text_edit";
type Active = {
  pointerId: number;
  target: "paint" | "selection";
  stroke: Stroke;
};
type CursorPreview = { target: "paint" | "selection"; x: number; y: number; erasing: boolean };
type PanGesture = { pointerId: number; x: number; y: number; startX: number; startY: number };
function ToolIcon({name}: {name: "draw" | "remove" | "upscale" | "view"}) {
  const common = {width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true};
  if (name === "draw") return <svg {...common}><path d="m14.5 4.5 5 5L8 21l-5 .8.8-5L14.5 4.5Z"/><path d="m13 6 5 5"/></svg>;
  if (name === "remove") return <svg {...common}><path d="M5 19 19 5"/><path d="m7 5 12 12"/><path d="M4 12h16"/></svg>;
  if (name === "upscale") return <svg {...common}><path d="M5 9V5h4M15 5h4v4M19 15v4h-4M9 19H5v-4"/><path d="m9 15 6-6M10 9h5v5"/></svg>;
  return <svg {...common}><circle cx="12" cy="12" r="7"/><path d="M12 8v8M8 12h8"/></svg>;
}
const PREVIEW_MAX_EDGE = 2048;
function previewSize(width: number, height: number) {
  const scale = Math.min(1, PREVIEW_MAX_EDGE / Math.max(width, height));
  return { width: Math.max(1, Math.round(width * scale)), height: Math.max(1, Math.round(height * scale)), scale };
}
function previewStroke(stroke: Stroke, scale: number): Stroke {
  return {...stroke, size: stroke.size * scale, points: stroke.points.map(p => ({x:p.x * scale, y:p.y * scale}))};
}
function App() {
  const gen=useGenerative();
  const [generateOpen,setGenerateOpen]=useState(false),[compareOriginal,setCompareOriginal]=useState(false);
  const pendingGenerated=useRef(false);
  const documentRevision=useRef(0);
  const hasPreview=!!gen.candidate&&!generateOpen;
  const [doc, setDoc] = useState<EditorDocument>();
  const [tool, setTool] = useState<Tool>("paint"),
    [size, setSize] = useState(28),
    [color, setColor] = useState("#ff3b6b"),
    [opacity, setOpacity] = useState(80),
    [notice, setNotice] = useState(""),
    [job, setJob] = useState<any>(),
    [preview, setPreview] = useState<any>(),
    [settings, setSettings] = useState<any>(),
    [showSettings, setShowSettings] = useState(false),
    [showSave, setShowSave] = useState(false),
    [showExit, setShowExit] = useState(false),
    [showExitSave, setShowExitSave] = useState(false),
    [ratioLocked, setRatioLocked] = useState(true),
    [target, setTarget] = useState<Dimensions>(),
    [zoom, setZoom] = useState(1),
    [zoomSensitivity, setZoomSensitivity] = useState(1.5),
    [zoomOrigin, setZoomOrigin] = useState("50% 50%"),
    [pan, setPan] = useState({x: 0, y: 0}),
    [cursorPreview, setCursorPreview] = useState<CursorPreview | null>(null),
    [error, setError] = useState<UserError | null>(null),
    [removeMethod, setRemoveMethod] = useState<"lama" | "opencv">("lama"),
    [upscaleMethod, setUpscaleMethod] = useState<"ai" | "lanczos">("lanczos"),
    [enhancementMode, setEnhancementMode] = useState<"resize" | "preserve">("resize"),
    [inspector, setInspector] = useState<Inspector>("draw");
  const paint = useRef<HTMLCanvasElement>(null),
    mask = useRef<HTMLCanvasElement>(null),
    cursorLayer = useRef<HTMLCanvasElement>(null),
    article = useRef<HTMLElement>(null),
    active = useRef<Active | null>(null),
    panGesture = useRef<PanGesture | null>(null),
    locked = useRef(false),
    documentRef = useRef<EditorDocument | undefined>(undefined),
    savedFingerprint = useRef<string | null>(null);
  const closeIntent = useRef(false);
  const closeRequest = useRef<() => void>(() => {});
  const p = doc?.history.present;
  useEffect(()=>{
    const assetIds=[...new Set(doc?[doc.original.id,...[...doc.history.past,doc.history.present,...doc.history.future].map(s=>s.photo.id)]:[])];
    void window.pixelmend.setDocumentAssets({revision:++documentRevision.current,assetIds}).catch(error=>console.error(error));
  },[doc]);
  useEffect(() => { documentRef.current = doc; }, [doc]);
  const { models, capabilities, error: modelError, refresh } = useModels();
  const selectedUpscaleId = normalizePreferences(settings || {}).upscaleModelTier === 'fast' ? 'realesrgan-general-x4v3' : 'realesrgan-x4plus';
  const selectedRemoveId = normalizePreferences(settings || {}).removeModelTier === 'fast' ? 'migan-512-places2' : 'lama';
  const aiReady = models.some(
    (m) =>
      m.id === selectedUpscaleId &&
      m.state === "ready" &&
      m.probe?.status === "passed",
  );
  const removeAIReady = models.some(
    m => m.id === selectedRemoveId && m.state === "ready" && m.probe?.status === "passed",
  );
  const modelsPreparing = models.some(isModelPreparing);
  const removePreparing = isModelPreparing(models.find(m=>m.id===selectedRemoveId));
  const upscalePreparing = isModelPreparing(models.find(m=>m.id===selectedUpscaleId));
  const preparationNotice = modelsPreparing ? <p role="note" aria-live="polite">AI modelleri arka planda hazırlanıyor; diğer araçları kullanabilirsiniz.</p> : null;
  const outputLimit = capabilities?.policy?.max_output_pixels ?? 200_000_000;
  const [starting, setStarting] = useState(false),
    busy = starting || !!job || gen.busy,
    busyRef = useRef(false);
  busyRef.current = busy || !!preview || hasPreview || hasPreview;
  const reportError = (context: ErrorContext, cause: unknown) => {
    console.error(cause);
    setError(userError(context, cause));
  };
  const redraw = () => {
    if (!p) return;
    const display = previewSize(p.photo.width, p.photo.height);
    for (const [k, c] of [
      ["paint", paint.current],
      ["selection", mask.current],
    ] as const) {
      if (!c) continue;
      c.width = display.width;
      c.height = display.height;
      const x = c.getContext("2d")!;
      for (const s of p[k]) drawStroke(x, previewStroke(s, display.scale), k);
    }
    if (cursorLayer.current) {
      cursorLayer.current.width = display.width;
      cursorLayer.current.height = display.height;
    }
  };
  useEffect(redraw, [doc]);
  useEffect(() => {
    if (p) {
      setTarget({ width: p.photo.width * 2, height: p.photo.height * 2 });
      setZoom(1);
      setPan({x: 0, y: 0});
    }
  }, [doc?.original.id]);
  useEffect(() => {
    const canvas = cursorLayer.current;
    if (!canvas || !p) return;
    const context = canvas.getContext('2d')!;
    context.clearRect(0, 0, canvas.width, canvas.height);
    if (!cursorPreview || busy || preview || hasPreview || !['draw','remove','text_edit'].includes(inspector)) return;
    const source = cursorPreview.target === 'paint' ? paint.current : mask.current;
    const display = previewSize(p.photo.width, p.photo.height);
    const radius = size * display.scale / 2;
    if (cursorPreview.erasing && source) {
      context.drawImage(source, 0, 0);
      context.save();
      context.globalCompositeOperation = 'destination-out';
      context.beginPath();
      context.arc(cursorPreview.x, cursorPreview.y, radius, 0, Math.PI * 2);
      context.fill();
      context.restore();
    }
    context.save();
    context.strokeStyle = '#000';
    context.lineWidth = Math.max(2, 3 * display.scale);
    context.setLineDash([5 * display.scale, 4 * display.scale]);
    context.beginPath();
    context.arc(cursorPreview.x, cursorPreview.y, radius, 0, Math.PI * 2);
    context.stroke();
    context.strokeStyle = '#fff';
    context.lineWidth = Math.max(.75, display.scale);
    context.stroke();
    context.restore();
  }, [cursorPreview, doc, p, size, busy, preview, inspector]);
  useEffect(() => {
    window.pixelmend.settings().then(value => {
      const next = normalizePreferences(value);
      setSettings(next);
      setZoomSensitivity(next.zoomSensitivity);
    });
    return window.pixelmend.onAction((a: string) => {
      if (a === "undo" && !busyRef.current) setDoc((d) => d && undo(d));
      if (a === "redo" && !busyRef.current) setDoc((d) => d && redo(d));
      if (a === "request-close") closeRequest.current();
      if (a === "settings") setShowSettings(true);
    });
  }, []);
  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const update = () => {
      document.documentElement.dataset.theme = settings?.theme === 'system' || !settings?.theme
        ? (media.matches ? 'dark' : 'light') : settings.theme;
      document.documentElement.lang = 'tr';
    };
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, [settings]);
  const open = async () => {
    const a = await window.pixelmend.openImage();
    if (a) {
      const opened = createDocument({
          id: a.asset_id,
          uri: a.preview,
          width: a.width,
          height: a.height,
        });
      savedFingerprint.current = documentFingerprint(opened);
      setDoc(opened);
      setPreview(null);
      setNotice(`${a.width} × ${a.height} görsel açıldı`);
    }
  };
  const clampPan = (next: {x: number; y: number}, scale = zoom) => {
    const surface = article.current, canvas = mask.current;
    if (!surface || !canvas) return next;
    const rect = canvas.getBoundingClientRect();
    const baseWidth = rect.width / scale, baseHeight = rect.height / scale;
    return boundedPan(next, {width: baseWidth, height: baseHeight}, {width: surface.clientWidth, height: surface.clientHeight}, scale);
  };
  const cursorAt = (e: React.PointerEvent): CursorPreview | null => {
    const canvas = e.currentTarget as HTMLCanvasElement;
    if (!p || busy || preview || hasPreview || !canvas.width) return null;
    const rect = canvas.getBoundingClientRect();
    const target = tool.startsWith('paint') ? 'paint' : 'selection';
    return {
      target,
      x: Math.max(0, Math.min(canvas.width - 1, (e.clientX - rect.left) * canvas.width / rect.width)),
      y: Math.max(0, Math.min(canvas.height - 1, (e.clientY - rect.top) * canvas.height / rect.height)),
      erasing: tool.endsWith('Erase'),
    };
  };
  const point = (e: React.PointerEvent) => {
    if (e.type === 'pointerdown' && e.button === 1) {
      e.preventDefault();
      e.currentTarget.setPointerCapture(e.pointerId);
      panGesture.current = {pointerId: e.pointerId, x: e.clientX, y: e.clientY, startX: pan.x, startY: pan.y};
      setCursorPreview(null);
      return;
    }
    if (panGesture.current?.pointerId === e.pointerId) {
      if (e.type === 'pointermove') {
        const gesture = panGesture.current;
        setPan(clampPan({x: gesture.startX + e.clientX - gesture.x, y: gesture.startY + e.clientY - gesture.y}));
      }
      if (e.type === 'pointerup' || e.type === 'pointercancel') panGesture.current = null;
      return;
    }
    if (inspector !== "draw" && inspector !== "remove" && inspector !== "text_edit") {
      setCursorPreview(null);
      return;
    }
    if (!p || busy || preview || hasPreview) return;
    const q = imagePoint(
      e.clientX,
      e.clientY,
      e.currentTarget.getBoundingClientRect(),
      p.photo.width,
      p.photo.height,
    );
    if (e.type === "pointerdown") {
      if (e.button !== 0 || active.current) return;
      setCursorPreview(cursorAt(e));
      const targetName = tool.startsWith("paint") ? "paint" : "selection",
        mode = tool.endsWith("Erase") ? "erase" : "draw",
        stroke: Stroke = {
          id: crypto.randomUUID(),
          mode,
          points: [{ x: q[0], y: q[1] }],
          color: targetName === "paint" ? color : "#ff3b6b",
          opacity:
            mode === "erase" || targetName === "selection" ? 1 : opacity / 100,
          size,
          hardness: 1,
        };
      e.currentTarget.setPointerCapture(e.pointerId);
      active.current = { pointerId: e.pointerId, target: targetName, stroke };
      drawStrokeStart(
        (targetName === "paint" ? paint : mask).current!.getContext("2d")!,
        previewStroke(stroke, previewSize(p.photo.width, p.photo.height).scale),
        targetName,
      );
    } else if (
      e.type === "pointermove" &&
      active.current?.pointerId === e.pointerId
    ) {
      const a = active.current,
        z = a.stroke.points,
        from = z[z.length - 1],
        to = { x: q[0], y: q[1] },
        scale = previewSize(p.photo.width, p.photo.height).scale;
      z.push(to);
      drawStrokeSegment(
        (a.target === "paint" ? paint : mask).current!.getContext("2d")!,
        previewBrush(a.stroke, scale),
        a.target,
        {x: from.x * scale, y: from.y * scale},
        {x: to.x * scale, y: to.y * scale},
      );
      setCursorPreview(cursorAt(e));
    } else if (e.type === 'pointermove') {
      setCursorPreview(cursorAt(e));
    } else if (
      (e.type === "pointerup" || e.type === "pointercancel") &&
      active.current?.pointerId === e.pointerId
    ) {
      const a = active.current;
      active.current = null;
      setCursorPreview(cursorAt(e));
      if(e.type === "pointerup"){
        try{const current=documentRef.current;if(current)setDoc(addStroke(current,a.target,a.stroke));}
        catch(error){redraw();reportError('render',error);}
      }else redraw();
    }
  };
  useEffect(() => {
    if (!job) return;
    let live = true,
      timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const s = await window.pixelmend.job(job.job_id);
        if (!live) return;
        if (s.status === "completed") {
          const next = await window.pixelmend.continueResult(
            job.job_id,
            s.result_ids[0],
          );
          if (!live) {await window.pixelmend.disposeAsset(next.asset_id);return;}
          setPreview({ uri: next.preview, asset: next, op: job.op });
          setJob(null);
          locked.current = false;
          setNotice(resultNotice(s.result_details?.[0], next.width, next.height));
        } else if (["failed", "cancelled"].includes(s.status)) {
          await window.pixelmend.disposeJob(job.job_id);
          setJob(null);
          locked.current = false;
          if (s.status === 'cancelled') setNotice('İşlem iptal edildi.');
          else reportError(job.op, new Error(s.error?.message || 'inference_failed'));
        } else {
          setNotice(
            s.status === "cancelling"
              ? "İptal bekleniyor…"
              : s.status === "queued"
                ? "İş sırada bekliyor…"
                : job.op === "remove"
                  ? "Nesne siliniyor…"
                  : "Görsel büyütülüyor…",
          );
          timer = setTimeout(poll, 150);
        }
      } catch (error) {
        if (live) {
          reportError(job.op, error);
          void window.pixelmend.disposeJob(job.job_id).catch(()=>{});
          setJob(null);
          locked.current = false;
        }
      }
    };
    void poll();
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [job]);
  const process = async (op: "remove" | "upscale", d?: Dimensions) => {
    if (!p || busy || locked.current || preview || hasPreview) return;
    if (op === "remove") {
      if (!p.selection.some(s => s.mode === "draw")) {
        reportError('remove', new Error('selection_required'));
        return;
      }
    }
    if (
      op === "upscale" &&
      (!d || !targetIsValid(d.width, d.height, outputLimit))
    ) {
      reportError('upscale', new Error('target_invalid'));
      return;
    }
    if (op === "upscale" && upscaleMethod === "ai" && !aiReady) {
      setNotice(
        "AI Kalite modeli hazır değil. Performans ayarlarından modeli indirin.",
      );
      return;
    }
    if (op === "remove" && removeMethod === "lama" && !removeAIReady) {
      setNotice("Seçilen AI modeli hazır değil. Ayarlar → Modeller bölümünden kurun veya sınayın.");
      setShowSettings(true);
      return;
    }
    locked.current = true;
    setStarting(true);
    setNotice(
      op === "remove"
        ? "Nesne silme başlatılıyor…"
        : upscaleMethod === "ai"
          ? "AI kalite artırma başlatılıyor…"
          : "Büyütme başlatılıyor…",
    );
    try {
      const created = await window.pixelmend.startJob({
        assetId: p.photo.id,
        operation: op,
        selectionStrokes: op === "remove" ? p.selection : undefined,
        targetWidth: d?.width,
        targetHeight: d?.height,
        upscaleMethod,
        removeMethod,
        modelId: op === 'upscale' && upscaleMethod === 'ai' ? selectedUpscaleId : op === 'remove' && removeMethod === 'lama' ? selectedRemoveId : undefined,
        intent: op === 'upscale' && enhancementMode === 'preserve' ? 'preserve_size' : 'resize',
      });
      setJob({ ...created, op });
    } catch (error) {
      locked.current = false;
      reportError(op, error);
    } finally {
      setStarting(false);
    }
  };
  const apply = () => {
    const a = preview.asset;
    setDoc(
      (d) =>
        d &&
        applyResult(
          d,
          { id: a.asset_id, uri: a.preview, width: a.width, height: a.height },
          preview.op,
        ),
    );
    setTarget({width: a.width, height: a.height});
    setPreview(null);
    setNotice(
      preview.op === "remove"
        ? "Nesne silindi; yeni alan seçebilirsiniz."
        : `Görsel ${a.width} × ${a.height} boyutuna getirildi.`,
    );
  };
  const saveImage = async () => {
    let temporaryAsset:string|undefined;
    try {
      const snapshot = documentRef.current;
      if (!snapshot) return false;
      const saved = documentFingerprint(snapshot);
      let assetId = snapshot.history.present.photo.id;
      if (snapshot.history.present.paint.length) {
        const rendered = await window.pixelmend.renderAsset({assetId, paintStrokes: snapshot.history.present.paint});
        assetId = rendered.asset_id;temporaryAsset=assetId;
      }
      {
        const ok = await window.pixelmend.saveImage({ assetId });
        if (ok && documentRef.current?.original.id === snapshot.original.id) savedFingerprint.current = saved;
        setNotice(ok ? "PNG görsel kaydedildi; EXIF/GPS/XMP metadata temizlendi." : "Kaydetme iptal edildi.");
        return ok && documentFingerprint(documentRef.current) === saved;
      }
    } catch (error) {
      reportError('save', error);
      return false;
    }finally{if(temporaryAsset)await window.pixelmend.disposeAsset(temporaryAsset).catch(()=>{});}
  };
  const leaveHome = () => {
    if(pendingGenerated.current){pendingGenerated.current=false;openGenerated();setShowExit(false);setShowExitSave(false);return;}
    active.current = null;
    setPreview(null);
    setShowExit(false);
    setShowExitSave(false);
    setDoc(undefined);
    if (closeIntent.current) void window.pixelmend.confirmClose();
  };
  const saveProject = async () => {
    try {
    const snapshot = documentRef.current;
    if (!snapshot) return false;
    const saved = documentFingerprint(snapshot);
    const ok = await window.pixelmend.saveProject(snapshot, false);
    if (ok && documentRef.current?.original.id === snapshot.original.id) savedFingerprint.current = saved;
    setNotice(ok ? "Proje kaydedildi." : "Kaydetme iptal edildi.");
    return ok && documentFingerprint(documentRef.current) === saved;
    } catch(error){reportError('save',error);return false;}
  };
  const requestHome = () => {
    if (isDocumentDirty(doc, savedFingerprint.current) || active.current) setShowExit(true);
    else leaveHome();
  };
  closeRequest.current = () => {
    if (busy) { setNotice('Kapatmadan önce çalışan işlemi tamamlayın veya iptal edin.'); return; }
    if (preview || hasPreview) { setNotice('Kapatmadan önce önizlemeyi Uygula veya Vazgeç ile tamamlayın.'); return; }
    closeIntent.current = true;
    if (doc && (isDocumentDirty(doc, savedFingerprint.current) || active.current || preview)) setShowExit(true);
    else void window.pixelmend.confirmClose();
  };
  const updateTarget = (field: "width" | "height", raw: string) => {
    if (!p) return;
    const n = Number(raw);
    if (!Number.isInteger(n) || n < 1) return;
    setTarget(
      ratioLocked
        ? fitDimension(p.photo, field, n)
        : { ...target!, [field]: n },
    );
  };
  const wheel = (e: React.WheelEvent) => {
    if (!(e.ctrlKey || e.metaKey)) return;
    e.preventDefault();
    const r = e.currentTarget.getBoundingClientRect();
    setZoomOrigin(
      `${((e.clientX - r.left) * 100) / r.width}% ${((e.clientY - r.top) * 100) / r.height}%`,
    );
    setZoom((v) => {
      const next = wheelZoom(v, e.deltaY, zoomSensitivity);
      setPan((current) => clampPan(current, next));
      return next;
    });
  };
  const startGenerative=(request:GenerativeRequest)=>{if(job||starting||preview||active.current)return;void gen.session.start(request);};
  const discardGenerative=()=>{void gen.session.discard().catch(e=>setNotice(String(e)));setCompareOriginal(false);};
  const acceptEdit=()=>{const candidate=gen.session.take();if(!candidate)return;const a=candidate.asset;setDoc(d=>d&&applyGenerativeResult(d,{id:a.asset_id,uri:a.preview,width:a.width,height:a.height},candidate.info));setCompareOriginal(false);setNotice('Yazıyla düzenleme uygulandı.');};
  const openGenerated=()=>{const candidate=gen.session.take();if(!candidate)return;const a=candidate.asset;setDoc(createGeneratedDocument({id:a.asset_id,uri:a.preview,width:a.width,height:a.height},candidate.info));savedFingerprint.current=null;setGenerateOpen(false);setNotice('Üretilen görsel yeni belgede açıldı.');};
  const requestGenerated=()=>{if(isDocumentDirty(doc,savedFingerprint.current)){pendingGenerated.current=true;setShowExit(true);}else openGenerated();};
  const generateDialog=generateOpen&&<div className="modal generation-dialog" role="dialog" aria-modal="true" aria-label="Yazıyla Oluştur">
    <button disabled={gen.busy} aria-label="Üretim ekranını kapat" onClick={()=>{discardGenerative();setGenerateOpen(false);}}>Kapat</button>
    <div className="generation-layout"><GenerativePanel kind="text_to_image" state={gen} capabilities={capabilities} models={models} start={startGenerative} cancel={()=>{void gen.session.cancel().catch(e=>setNotice(String(e)));}} discard={discardGenerative} accept={requestGenerated} settings={()=>setShowSettings(true)}/>
    <div className="generation-preview">{gen.candidate?<img src={gen.candidate.asset.preview} alt="Üretilen görsel önizlemesi"/>:<p>Sonucunuz burada görünecek.</p>}</div></div>
  </div>;
  const candidateUri=hasPreview&&!compareOriginal?gen.candidate?.asset.preview:undefined;
  const displayingResult=!!preview||hasPreview&&!compareOriginal;
  if (!doc)
    return (
      <main className="home">
        <h1>PixelMend</h1>
        <p>Fotoğrafları yerelde düzenleyin.</p>
        {preparationNotice}
        <button disabled={busy} onClick={open}>Görsel Aç</button>
        <button disabled={busy} onClick={()=>setGenerateOpen(true)}>Yazıyla Oluştur</button>
        {generateDialog}
        <button
          onClick={async () => {
            const d = await window.pixelmend.openProject();
            if (d) { const opened=parseDocument(d);savedFingerprint.current = documentFingerprint(opened); setDoc(opened); }
          }}
        >
          Proje Aç
        </button>
        <button onClick={() => setShowSettings(true)}>Ayarlar</button>
        {showSettings && (
          <PerformanceSettings
            value={settings}
            close={() => setShowSettings(false)}
            set={setSettings}
            models={models}
            capabilities={capabilities}
            refresh={refresh}
            error={modelError}
            onZoomSensitivity={setZoomSensitivity}
          />
        )}
      </main>
    );
  const valid =
      !!target && targetIsValid(target.width, target.height, outputLimit),
    mp = target ? (target.width * target.height) / 1e6 : 0;
  return (
    <main>
      {preparationNotice}
      <header>
        <button disabled={busy || !!preview || hasPreview} onClick={requestHome}>
          Başlangıç
        </button>
        <h1>PixelMend</h1>
        <button disabled={busy || !!preview || hasPreview} onClick={()=>setGenerateOpen(true)}>Yazıyla Oluştur</button>
        <button
          onClick={() => setDoc((d) => d && undo(d))}
          disabled={busy || !!preview || hasPreview || !doc.history.past.length}
        >
          Geri al
        </button>
        <button
          onClick={() => setDoc((d) => d && redo(d))}
          disabled={busy || !!preview || hasPreview || !doc.history.future.length}
        >
          Yinele
        </button>
        <button aria-label="Ayarlar" title="Ayarlar" disabled={busy} onClick={() => setShowSettings(true)}>
          Ayarlar
        </button>
        <div className="save-menu">
          <button
            disabled={busy || !!preview || hasPreview}
            aria-expanded={showSave}
            onClick={() => setShowSave((v) => !v)}
          >
            Kaydet
          </button>
          {showSave && (
            <div className="save-options">
              <button
                onClick={async () => {
                  setShowSave(false);
                  await saveImage();
                }}
              >
                Görsel olarak kaydet (PNG)
              </button>
              <button
                onClick={async () => {
                  setShowSave(false);
                  await saveProject();
                }}
              >
                Projeyi kaydet (.pixelmend)
              </button>
            </div>
          )}
        </div>
      </header>
      <section className="workspace">
        <nav className="tool-rail" aria-label="Düzenleme araçları">
          <button aria-label="Çizim" title="Çizim" aria-pressed={inspector === "draw"} onClick={() => { setInspector("draw"); setTool("paint"); }}><ToolIcon name="draw" /></button>
          <button aria-label="Nesne silme" title="Nesne silme" aria-pressed={inspector === "remove"} onClick={() => { setInspector("remove"); setTool("select"); }}><ToolIcon name="remove" /></button>
          <button aria-label="Büyütme" title="Büyütme" aria-pressed={inspector === "upscale"} onClick={() => setInspector("upscale")}><ToolIcon name="upscale" /></button>
          <button aria-label="Yazıyla Düzenle" title="Yazıyla Düzenle" aria-pressed={inspector === "text_edit"} onClick={()=>{setInspector("text_edit");setTool("select");}}>✦</button>
          <button aria-label="Görünüm" title="Görünüm" aria-pressed={inspector === "view"} onClick={() => setInspector("view")}><ToolIcon name="view" /></button>
        </nav>
        <aside className="inspector">
          {(inspector==='text_edit'||hasPreview||gen.busy&&!generateOpen)&&<><div className="quick-actions"><button disabled={busy||hasPreview} aria-pressed={tool==='select'} onClick={()=>setTool('select')}>Alan seç</button><button disabled={busy||hasPreview} aria-pressed={tool==='selectErase'} onClick={()=>setTool('selectErase')}>Seçim silgisi</button></div><label>Seçim boyutu<input type="range" min="2" max="500" value={size} disabled={busy||hasPreview} onChange={e=>setSize(+e.target.value)}/></label>
          <GenerativePanel kind="text_edit" state={gen} capabilities={capabilities} models={models} source={{assetId:p!.photo.id,selectionStrokes:p!.selection,paintStrokes:p!.paint}} locked={!!job||starting||!!preview} start={startGenerative} cancel={()=>{void gen.session.cancel().catch(e=>setNotice(String(e)));}} discard={discardGenerative} accept={acceptEdit} settings={()=>setShowSettings(true)} compare={compareOriginal} setCompare={setCompareOriginal}/></>}

          {inspector === "draw" && <section className="tool-group">
            <h2>Çizim</h2>
            <p>Görselin üzerine renk ekleyin.</p>
            <button
              aria-pressed={tool === "paint"}
              onClick={() => setTool("paint")}
            >
              Fırça
            </button>
            <button
              aria-pressed={tool === "paintErase"}
              onClick={() => setTool("paintErase")}
            >
              Silgi
            </button>
            <label>
              Renk{" "}
              <input
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
              />
            </label>
            <label>
              Opaklık{" "}
              <span className="value-input">
                <input
                  type="range"
                  min="1"
                  max="100"
                  value={opacity}
                  onChange={(e) => setOpacity(+e.target.value)}
                />
                <input
                  aria-label="Opaklık yüzdesi"
                  type="number"
                  min="1"
                  max="100"
                  value={opacity}
                  onChange={(e) =>
                    setOpacity(Math.max(1, Math.min(100, +e.target.value || 1)))
                  }
                />
                <span>%</span>
              </span>
            </label>
            <label>
              Fırça boyutu{" "}
              <span className="value-input">
                <input
                  type="range"
                  min="2"
                  max="160"
                  value={size}
                  onChange={(e) => setSize(+e.target.value)}
                />
                <input
                  aria-label="Fırça boyutu piksel"
                  type="number"
                  min="2"
                  max="160"
                  value={size}
                  onChange={(e) =>
                    setSize(Math.max(2, Math.min(160, +e.target.value || 2)))
                  }
                />
                <span>px</span>
              </span>
            </label>
          </section>}
          {inspector === "remove" && <section className="tool-group">
            <h2>Nesne Silgisi</h2>
            <p>Silinecek alanı işaretleyin.</p>
            <label><input type="radio" name="remove-method" checked={removeMethod === "lama"} onChange={() => setRemoveMethod("lama")}/> AI ile nesne sil{!removeAIReady && ` (${modelAvailability(models.find(m=>m.id===selectedRemoveId))})`}</label>
            <label><input type="radio" name="remove-method" checked={removeMethod === "opencv"} onChange={() => setRemoveMethod("opencv")}/> Hızlı — OpenCV</label>
            {showsAiControls('remove', removeMethod) ? <><label>AI modeli<select aria-label="Nesne silme modeli" value={selectedRemoveId} disabled={busy || !!preview || hasPreview} onChange={async event=>{
              const tier=event.target.value==='migan-512-places2'?'fast':'balanced';
              const next={...normalizePreferences(settings || {}),removeModelTier:tier as 'fast'|'balanced'|'advanced'};
              try {await window.pixelmend.setSettings(next);setSettings(next);setRemoveMethod('lama');}catch(error){reportError('remove',error);}
            }}>{selectableModels(models.filter(m=>m.operation==='remove')).map(m=><option key={m.id} value={m.id} disabled={!m.verified_manifest}>{m.tier==='fast'?'Hızlı — daha düşük kalite':'Dengeli'} · {m.name}{!m.verified_manifest?' · henüz desteklenmiyor':m.state==='ready'?'':` · ${modelAvailability(m)}`}</option>)}</select></label><p className="hint">Güçlü silme modeli yakında.</p>
            {!removeAIReady ? <button onClick={()=>setShowSettings(true)}>{removePreparing ? 'Model hazırlığını göster' : 'Modeli kur veya sına'}</button> : null}</> : null}
            <button
              aria-pressed={tool === "select"}
              onClick={() => setTool("select")}
            >
              Nesne Seçici
            </button>
            <button
              aria-pressed={tool === "selectErase"}
              onClick={() => setTool("selectErase")}
            >
              Seçimi Sil
            </button>
            <label>
              Seçim fırçası boyutu
              <span className="value-input"><input type="range" min="2" max="160" value={size} onChange={(e) => setSize(+e.target.value)} /><input aria-label="Seçim fırçası boyutu piksel" type="number" min="2" max="160" value={size} onChange={(e) => setSize(Math.max(2, Math.min(160, +e.target.value || 2)))} /><span>px</span></span>
            </label>
            <button
              disabled={busy || !!preview || hasPreview || (removeMethod === 'lama' && !removeAIReady)}
              onClick={() => process("remove")}
            >
              Nesneyi Sil
            </button>
          </section>}
          {inspector === "upscale" && <section className="tool-group">
            <h2>Büyütme</h2>
            <p>{upscaleMethod === "ai" ? "Ayrıntıları ve netliği iyileştirir; ince dokular değişebilir." : "Görünümü koruyarak boyutlandırır; AI ile ayrıntı üretmez."}</p>
            <label className="method-option"><input type="radio" name="upscale-method" checked={upscaleMethod === "lanczos"} onChange={() => { setUpscaleMethod("lanczos"); setEnhancementMode("resize"); }}/><span><strong>Standart büyütme</strong><small>Lanczos · özgün görünüm öncelikli</small></span></label>
            <label className="method-option"><input type="radio" name="upscale-method" checked={upscaleMethod === "ai"} disabled={!aiReady} onChange={() => setUpscaleMethod("ai")}/><span><strong>AI ile iyileştir</strong><small>RealESRGAN · doğal ayrıntı öncelikli{!aiReady && ` · ${modelAvailability(models.find(m=>m.id===selectedUpscaleId))}`}</small></span></label>
            {showsAiControls('upscale', upscaleMethod) ? <><label>AI modeli<select aria-label="İyileştirme modeli" value={selectedUpscaleId} disabled={busy || !!preview || hasPreview} onChange={async event=>{
              const tier=event.target.value==='realesrgan-general-x4v3'?'fast':'balanced';
              const next={...normalizePreferences(settings || {}),upscaleModelTier:tier as 'fast'|'balanced'|'advanced'};
              try {await window.pixelmend.setSettings(next);setSettings(next);setUpscaleMethod('ai');}catch(error){reportError('upscale',error);}
            }}>{selectableModels(models.filter(m=>m.operation==='upscale')).map(m=><option key={m.id} value={m.id} disabled={!m.verified_manifest}>{m.tier==='fast'?'Hızlı — daha düşük kalite':'Dengeli'} · {m.name}{!m.verified_manifest?' · henüz desteklenmiyor':m.state==='ready'?'':` · ${modelAvailability(m)}`}</option>)}</select></label><p className="hint">Güçlü kalite artırma modeli yakında.</p>
            {!aiReady ? <button onClick={()=>setShowSettings(true)}>{upscalePreparing ? 'Model hazırlığını göster' : 'Modeli kur veya sına'}</button> : null}
            <div className="segmented-control" role="group" aria-label="İyileştirme hedefi">
              <button aria-pressed={enhancementMode === 'resize'} onClick={() => setEnhancementMode('resize')}>Büyüt</button>
              <button aria-pressed={enhancementMode === 'preserve'} onClick={() => { setEnhancementMode('preserve'); setUpscaleMethod('ai'); setTarget(preserveDimensions(p!.photo)); }}>Boyutu koru</button>
            </div></> : null}
            {enhancementMode === 'preserve' ? <p className="hint">AI, görüntüyü doğal 4× ayrıntı yolundan geçirir ve sonucu aynı ölçülere getirir. İnce dokular değişebilir.</p> : <><div className="quick-actions">
              <button
                disabled={busy || !!preview || hasPreview || (upscaleMethod === 'ai' && !aiReady)}
                onClick={() => {
                  const d = {
                    width: p!.photo.width * 2,
                    height: p!.photo.height * 2,
                  };
                  setTarget(d);
                  void process("upscale", d);
                }}
              >
                2×
              </button>
              <button
                disabled={busy || !!preview || hasPreview || (upscaleMethod === 'ai' && !aiReady)}
                onClick={() => {
                  const d = {
                    width: p!.photo.width * 4,
                    height: p!.photo.height * 4,
                  };
                  setTarget(d);
                  void process("upscale", d);
                }}
              >
                4×
              </button>
            </div>
            <label>
              Genişlik{" "}
              <input
                aria-label="Hedef genişlik"
                type="number"
                min="1"
                value={target?.width ?? ""}
                onChange={(e) => updateTarget("width", e.target.value)}
              />
            </label>
            <label>
              Yükseklik{" "}
              <input
                aria-label="Hedef yükseklik"
                type="number"
                min="1"
                value={target?.height ?? ""}
                onChange={(e) => updateTarget("height", e.target.value)}
              />
            </label>
            <label className="lock">
              <input
                type="checkbox"
                checked={ratioLocked}
                onChange={(e) => setRatioLocked(e.target.checked)}
              />{" "}
              Oranı koru
            </label></>}
            <p className={valid ? "hint" : "hint error"}>{valid ? `${mp.toFixed(1)} MP hedef · güvenli sınır işlem başında RAM ve diske göre doğrulanır` : `En fazla ${outputLimit / 1e6} MP ve pozitif tam sayılar girin.`}</p>
            <button
              disabled={busy || !!preview || hasPreview || !valid || (upscaleMethod === 'ai' && !aiReady)}
              onClick={() => process("upscale", enhancementMode === 'preserve' ? preserveDimensions(p!.photo) : target)}
            >
              Önizleme oluştur
            </button>
          </section>}
          <p className="status" role="status">
            {notice}
          </p>
          {inspector === "view" && <section className="tool-group" aria-label="Görünüm ayarları">
            <h2>Görünüm</h2>
            <p className="hint">{Math.round(zoom * 100)}% · ⌘/Ctrl + tekerlek ile yakınlaştırın; tekerleğe basılı sürükleyerek görseli kaydırın.</p>
            <div className="quick-actions">
              <button onClick={() => { const rect=mask.current?.getBoundingClientRect(); if(rect?.width && p) { setZoom(p.photo.width / (rect.width / zoom)); setPan({x:0,y:0}); } }}>100%</button>
              <button onClick={() => { setZoom(1); setPan({x: 0, y: 0}); }}>Sığdır</button>
            </div>
            <p className="hint">Tekerlek hassasiyetini Ayarlar › Tuval ve araçlar bölümünden değiştirebilirsiniz.</p>
          </section>}
          {preview && (
            <section className="tool-group preview-actions" aria-label="İşlem önizlemesi">
              <strong>İşlem önizlemesi hazır</strong>
              <button onClick={apply}>Uygula</button>
              <button onClick={() => { void window.pixelmend.disposeAsset(preview.asset.asset_id).catch(()=>{});setPreview(null); setNotice("Önizleme vazgeçildi. Seçim korunuyor."); }}>Vazgeç</button>
            </section>
          )}
        </aside>
        <article ref={article} onWheel={wheel}>
          <div
            className="canvas zoomable"
            style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, transformOrigin: zoomOrigin }}
          >
            <img src={preview?.uri || candidateUri || p!.photo.uri} alt="Düzenlenen görsel" />
            <canvas
              style={{ visibility: displayingResult ? "hidden" : "visible", opacity: cursorPreview?.erasing && cursorPreview.target === 'paint' ? 0 : undefined }}
              className="paint"
              ref={paint}
            />
            <canvas
              className="mask"
              style={{ visibility: displayingResult ? "hidden" : "visible", opacity: cursorPreview?.erasing && cursorPreview.target === 'selection' ? 0 : undefined, cursor: canvasCursor({editing: inspector === 'draw' || inspector === 'remove' || inspector === 'text_edit', hasPreview: !!preview || hasPreview, busy, hasRing: !!cursorPreview}) }}
              ref={mask}
              onPointerDown={point}
              onPointerMove={point}
              onPointerUp={point}
              onPointerCancel={point}
              onPointerLeave={() => { if (!active.current && !panGesture.current) setCursorPreview(null); }}
            />
            <canvas
              aria-hidden="true"
              className="cursor-layer"
              style={{ visibility: displayingResult ? 'hidden' : 'visible', opacity: cursorPreview?.erasing && cursorPreview.target === 'selection' ? .42 : 1 }}
              ref={cursorLayer}
            />
          </div>
          {(starting || !!job) && (
            <div className="processing" role="region" aria-label="İşlem durumu">
              <progress aria-label="İşlem sürüyor" />
              <strong>{notice}</strong>
              {job && (
                <button
                  onClick={async () => {
                    try {
                      setNotice("İptal isteniyor…");
                      await window.pixelmend.cancel(job.job_id);
                    } catch (error) {
                      reportError('cancel', error);
                    }
                  }}
                >
                  İptal
                </button>
              )}
            </div>
          )}
        </article>
      </section>
      {generateDialog}
      {showExit && (
        <Exit
          close={() => {pendingGenerated.current=false;closeIntent.current = false; setShowExit(false);}}
          discard={leaveHome}
          save={() => {
            setShowExit(false);
            setShowExitSave(true);
          }}
        />
      )}
      {showExitSave && (
        <SaveExit
          close={() => {pendingGenerated.current=false;closeIntent.current = false; setShowExitSave(false);}}
          image={saveImage}
          project={saveProject}
          leave={leaveHome}
        />
      )}{" "}
      {showSettings && (
        <PerformanceSettings
          value={settings}
          close={() => setShowSettings(false)}
          set={setSettings}
          models={models}
          capabilities={capabilities}
          refresh={refresh}
          error={modelError}
          onZoomSensitivity={setZoomSensitivity}
        />
      )}
      {error && <ErrorDialog value={error} close={() => setError(null)} />}
    </main>
  );
}
function ErrorDialog({value, close}: {value: UserError; close: () => void}) {
  return <div className="modal confirm-dialog error-dialog" role="alertdialog" aria-modal="true" aria-labelledby="error-title">
    <h2 id="error-title">{value.title}</h2>
    <p>{value.message}</p>
    <div className="modal-actions"><button autoFocus onClick={close}>Tamam</button></div>
  </div>;
}
function Exit({
  close,
  discard,
  save,
}: {
  close: () => void;
  discard: () => void;
  save: () => void;
}) {
  return (
    <div className="modal confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="exit-title">
      <h2 id="exit-title">Değişiklikler kaydedilsin mi?</h2>
      <p>Devam etmeden önce mevcut belgedeki çizimleri ve işlemleri kaydedebilirsiniz.</p>
      <div className="modal-actions">
        <button autoFocus onClick={close}>Vazgeç</button>
        <button onClick={discard}>Kaydetmeden çık</button>
        <button className="primary" onClick={save}>Kaydet</button>
      </div>
    </div>
  );
}
function SaveExit({
  close,
  image,
  project,
  leave,
}: {
  close: () => void;
  image: () => Promise<boolean>;
  project: () => Promise<boolean>;
  leave: () => void;
}) {
  return (
    <div className="modal confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="save-title">
      <h2 id="save-title">Kaydet ve çık</h2>
      <p>
        Görsel PNG olarak dışa aktarılır; proje düzenlemeye devam etmek için
        saklanır.
      </p>
      <div className="modal-actions">
        <button autoFocus onClick={close}>Vazgeç</button>
        <button className="primary"
          onClick={async () => {
            if (await image()) leave();
          }}
        >
          PNG olarak kaydet
        </button>
        <button
          onClick={async () => {
            if (await project()) leave();
          }}
        >
          Projeyi kaydet
        </button>
      </div>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
