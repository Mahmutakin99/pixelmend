import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  addStroke,
  applyResult,
  createDocument,
  redo,
  undo,
  type EditorDocument,
  type Stroke,
} from "./document";
import { drawStroke, drawStrokeSegment, drawStrokeStart } from "./brush";
import { imagePoint } from "./strokes";
import { boundedPan, wheelZoom } from "./zoom";
import { fitDimension, targetIsValid, type Dimensions } from "./upscale";
import { userError, type ErrorContext, type UserError } from "./errors";
import { keepsErasePreview } from "./cursor-preview";
import { Settings as PerformanceSettings } from "./Settings";
import { useModels } from "./useModels";
import "./bridge";
import "./style.css";
type Tool = "paint" | "paintErase" | "select" | "selectErase";
type Inspector = "draw" | "remove" | "upscale" | "view";
type Active = {
  pointerId: number;
  target: "paint" | "selection";
  stroke: Stroke;
};
type CursorPreview = { target: "paint" | "selection"; x: number; y: number; erasing: boolean };
type PanGesture = { pointerId: number; x: number; y: number; startX: number; startY: number };
const PREVIEW_MAX_EDGE = 2048;
function previewSize(width: number, height: number) {
  const scale = Math.min(1, PREVIEW_MAX_EDGE / Math.max(width, height));
  return { width: Math.max(1, Math.round(width * scale)), height: Math.max(1, Math.round(height * scale)), scale };
}
function previewStroke(stroke: Stroke, scale: number): Stroke {
  return {...stroke, size: stroke.size * scale, points: stroke.points.map(p => ({x:p.x * scale, y:p.y * scale}))};
}
function App() {
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
    [inspector, setInspector] = useState<Inspector>("draw");
  const paint = useRef<HTMLCanvasElement>(null),
    mask = useRef<HTMLCanvasElement>(null),
    cursorLayer = useRef<HTMLCanvasElement>(null),
    article = useRef<HTMLElement>(null),
    active = useRef<Active | null>(null),
    panGesture = useRef<PanGesture | null>(null),
    locked = useRef(false);
  const closeIntent = useRef(false);
  const closeRequest = useRef<() => void>(() => {});
  const p = doc?.history.present;
  const { models, capabilities, error: modelError, refresh } = useModels();
  const aiReady = models.some(
    (m) =>
      m.id === "realesrgan-x4plus" &&
      m.state === "ready" &&
      m.probe?.status === "passed",
  );
  const lamaReady = models.some(m => m.id === "lama" && m.state === "ready" && m.probe?.status === "passed");
  const outputLimit = capabilities?.policy?.max_output_pixels ?? 200_000_000;
  const [starting, setStarting] = useState(false),
    busy = starting || !!job,
    busyRef = useRef(false);
  busyRef.current = busy || !!preview;
  const reportError = (context: ErrorContext, cause: unknown) => {
    console.error(cause);
    setError(userError(context, cause));
  };
  useEffect(() => {
    if (!aiReady && upscaleMethod === "ai") setUpscaleMethod("lanczos");
  }, [aiReady, upscaleMethod]);
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
    if (!cursorPreview) return;
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
    context.strokeStyle = cursorPreview.erasing ? '#e8ecf0' : cursorPreview.target === 'selection' ? '#ff735c' : color;
    context.lineWidth = Math.max(1, 2 * display.scale);
    context.setLineDash(cursorPreview.target === 'selection' ? [5 * display.scale, 4 * display.scale] : []);
    context.beginPath();
    context.arc(cursorPreview.x, cursorPreview.y, radius, 0, Math.PI * 2);
    context.stroke();
    context.restore();
  }, [cursorPreview, doc, p, size, color]);
  useEffect(() => {
    window.pixelmend.settings().then(setSettings);
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
      setDoc(
        createDocument({
          id: a.asset_id,
          uri: a.preview,
          width: a.width,
          height: a.height,
        }),
      );
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
    if (!p || busy || preview || !canvas.width) return null;
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
    if (inspector !== "draw" && inspector !== "remove") {
      setCursorPreview(null);
      return;
    }
    if (!p || busy || preview) return;
    const q = imagePoint(
      e.clientX,
      e.clientY,
      e.currentTarget.getBoundingClientRect(),
      p.photo.width,
      p.photo.height,
    );
    if (e.type === "pointerdown") {
      if (e.button !== 0 || active.current) return;
      if (keepsErasePreview(tool.endsWith('Erase') ? 'erase' : 'draw')) setCursorPreview(cursorAt(e));
      else setCursorPreview(null);
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
        to = { x: q[0], y: q[1] };
      z.push(to);
      drawStrokeSegment(
        (a.target === "paint" ? paint : mask).current!.getContext("2d")!,
        previewStroke(a.stroke, previewSize(p.photo.width, p.photo.height).scale),
        a.target,
        {x: from.x * previewSize(p.photo.width, p.photo.height).scale, y: from.y * previewSize(p.photo.width, p.photo.height).scale},
        {x: to.x * previewSize(p.photo.width, p.photo.height).scale, y: to.y * previewSize(p.photo.width, p.photo.height).scale},
      );
      if (keepsErasePreview(a.stroke.mode)) setCursorPreview(cursorAt(e));
    } else if (e.type === 'pointermove') {
      setCursorPreview(cursorAt(e));
    } else if (
      (e.type === "pointerup" || e.type === "pointercancel") &&
      active.current?.pointerId === e.pointerId
    ) {
      const a = active.current;
      active.current = null;
      setCursorPreview(cursorAt(e));
      if (e.type === "pointerup")
        setDoc((d) => d && addStroke(d, a.target, a.stroke));
      else redraw();
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
          if (!live) return;
          setPreview({ uri: next.preview, asset: next, op: job.op });
          setJob(null);
          locked.current = false;
          setNotice(
            `Sonuç hazır: ${next.width} × ${next.height} · ${s.result_details?.[0]?.algorithm ?? ""} · ${s.result_details?.[0]?.provider ?? "CPU"}. Uygula veya Vazgeç.`,
          );
        } else if (["failed", "cancelled"].includes(s.status)) {
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
    if (!p || locked.current || preview) return;
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
    if (op === "remove" && removeMethod === "lama" && !lamaReady) {
      setNotice("LaMa hazır değil. Ayarlar → Modeller bölümünden kurun veya sınayın.");
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
    try {
      let assetId = p!.photo.id;
      if (p!.paint.length) {
        const rendered = await window.pixelmend.renderAsset({assetId, paintStrokes: p!.paint});
        assetId = rendered.asset_id;
      }
      {
        const ok = await window.pixelmend.saveImage({ assetId });
        setNotice(ok ? "PNG görsel kaydedildi; EXIF/GPS/XMP metadata temizlendi." : "Kaydetme iptal edildi.");
        return ok;
      }
    } catch (error) {
      reportError('save', error);
      return false;
    }
  };
  const leaveHome = () => {
    active.current = null;
    setPreview(null);
    setShowExit(false);
    setShowExitSave(false);
    setDoc(undefined);
    if (closeIntent.current) void window.pixelmend.confirmClose();
  };
  const saveProject = async () => {
    const ok = await window.pixelmend.saveProject(doc, false);
    setNotice(ok ? "Proje kaydedildi." : "Kaydetme iptal edildi.");
    return ok;
  };
  const requestHome = () => {
    if (doc!.history.past.length || active.current) setShowExit(true);
    else leaveHome();
  };
  closeRequest.current = () => {
    if (busy) { setNotice('Kapatmadan önce çalışan işlemi tamamlayın veya iptal edin.'); return; }
    if (preview) { setNotice('Kapatmadan önce önizlemeyi Uygula veya Vazgeç ile tamamlayın.'); return; }
    closeIntent.current = true;
    if (doc && (doc.history.past.length || active.current || preview)) setShowExit(true);
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
  if (!doc)
    return (
      <main className="home">
        <h1>PixelMend</h1>
        <p>Fotoğrafları yerelde düzenleyin.</p>
        <button onClick={open}>Görsel Aç</button>
        <button
          onClick={async () => {
            const d = await window.pixelmend.openProject();
            if (d) setDoc(d);
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
          />
        )}
      </main>
    );
  const valid =
      !!target && targetIsValid(target.width, target.height, outputLimit),
    mp = target ? (target.width * target.height) / 1e6 : 0;
  return (
    <main>
      <header>
        <button disabled={busy || !!preview} onClick={requestHome}>
          Başlangıç
        </button>
        <h1>PixelMend</h1>
        <button
          onClick={() => setDoc((d) => d && undo(d))}
          disabled={busy || !!preview || !doc.history.past.length}
        >
          Geri al
        </button>
        <button
          onClick={() => setDoc((d) => d && redo(d))}
          disabled={busy || !!preview || !doc.history.future.length}
        >
          Yinele
        </button>
        <div className="save-menu">
          <button
            disabled={busy || !!preview}
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
          <button aria-label="Çizim" aria-pressed={inspector === "draw"} onClick={() => { setInspector("draw"); setTool("paint"); }}>✎</button>
          <button aria-label="Nesne silme" aria-pressed={inspector === "remove"} onClick={() => { setInspector("remove"); setTool("select"); }}>⌁</button>
          <button aria-label="Büyütme" aria-pressed={inspector === "upscale"} onClick={() => setInspector("upscale")}>⤢</button>
          <button aria-label="Görünüm" aria-pressed={inspector === "view"} onClick={() => setInspector("view")}>◉</button>
        </nav>
        <aside className="inspector">
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
            <label><input type="radio" name="remove-method" checked={removeMethod === "lama"} onChange={() => setRemoveMethod("lama")}/> AI — LaMa{!lamaReady && " (kurulum/sınama gerekli)"}</label>
            <label><input type="radio" name="remove-method" checked={removeMethod === "opencv"} onChange={() => setRemoveMethod("opencv")}/> Hızlı — OpenCV</label>
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
              disabled={busy || !!preview}
              onClick={() => process("remove")}
            >
              Nesneyi Sil
            </button>
          </section>}
          {inspector === "upscale" && <section className="tool-group">
            <h2>Büyütme</h2>
            <p>{upscaleMethod === "ai" ? "Ayrıntıları ve netliği iyileştirir; ince dokular değişebilir." : "Görünümü koruyarak boyutlandırır; AI ile ayrıntı üretmez."}</p>
            <label className="method-option"><input type="radio" name="upscale-method" checked={upscaleMethod === "lanczos"} onChange={() => setUpscaleMethod("lanczos")}/><span><strong>Standart büyütme</strong><small>Lanczos · özgün görünüm öncelikli</small></span></label>
            <label className="method-option"><input type="radio" name="upscale-method" checked={upscaleMethod === "ai"} disabled={!aiReady} onChange={() => setUpscaleMethod("ai")}/><span><strong>AI ile iyileştir</strong><small>RealESRGAN · doğal ayrıntı öncelikli{!aiReady && " · model hazır değil"}</small></span></label>
            <div className="quick-actions">
              <button
                disabled={busy || !!preview}
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
                disabled={busy || !!preview}
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
            </label>
            <p className={valid ? "hint" : "hint error"}>{valid ? `${mp.toFixed(1)} MP hedef · güvenli sınır işlem başında RAM ve diske göre doğrulanır` : `En fazla ${outputLimit / 1e6} MP ve pozitif tam sayılar girin.`}</p>
            <button
              disabled={busy || !!preview || !valid}
              onClick={() => process("upscale", target)}
            >
              Önizleme oluştur
            </button>
          </section>}
          <p className="status" role="status">
            {notice}
          </p>
          {inspector === "view" && <section className="tool-group" aria-label="Görünüm ayarları">
            <label>
              Yakınlaştırma hassasiyeti
              <input aria-label="Yakınlaştırma hassasiyeti" type="range" min="0.5" max="4" step="0.5" value={zoomSensitivity} onChange={e => setZoomSensitivity(Number(e.target.value))} />
              <span>{zoomSensitivity.toFixed(1)}×</span>
            </label>
            <p className="hint">⌘/Ctrl + tekerlek ile yakınlaştırın; tekerleğe basılı sürükleyerek görseli kaydırın.</p>
            <button onClick={() => { setZoom(1); setPan({x: 0, y: 0}); }}>Görünümü sıfırla</button>
          </section>}
          {preview && (
            <section className="tool-group preview-actions" aria-label="İşlem önizlemesi">
              <strong>İşlem önizlemesi hazır</strong>
              <button onClick={apply}>Uygula</button>
              <button onClick={() => { setPreview(null); setNotice("Önizleme vazgeçildi. Seçim korunuyor."); }}>Vazgeç</button>
            </section>
          )}
        </aside>
        <article ref={article} onWheel={wheel}>
          <div
            className="canvas zoomable"
            style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, transformOrigin: zoomOrigin }}
          >
            <img src={preview?.uri || p!.photo.uri} alt="Düzenlenen görsel" />
            <canvas
              style={{ visibility: preview ? "hidden" : "visible", opacity: cursorPreview?.erasing && cursorPreview.target === 'paint' ? 0 : undefined }}
              className="paint"
              ref={paint}
            />
            <canvas
              style={{ visibility: preview ? "hidden" : "visible", opacity: cursorPreview?.erasing && cursorPreview.target === 'selection' ? 0 : undefined }}
              className="mask"
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
              style={{ visibility: preview ? 'hidden' : 'visible', opacity: cursorPreview?.erasing && cursorPreview.target === 'selection' ? .42 : 1 }}
              ref={cursorLayer}
            />
          </div>
          {busy && (
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
      {showExit && (
        <Exit
          close={() => {closeIntent.current = false; setShowExit(false);}}
          discard={leaveHome}
          save={() => {
            setShowExit(false);
            setShowExitSave(true);
          }}
        />
      )}
      {showExitSave && (
        <SaveExit
          close={() => {closeIntent.current = false; setShowExitSave(false);}}
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
        />
      )}
      {error && <ErrorDialog value={error} close={() => setError(null)} />}
    </main>
  );
}
function ErrorDialog({value, close}: {value: UserError; close: () => void}) {
  return <div className="modal error-dialog" role="alertdialog" aria-modal="true" aria-labelledby="error-title">
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
    <div className="modal" role="dialog">
      <h2>Değişiklikler kaydedilsin mi?</h2>
      <p>Çizimler ve yapılan işlemler kaydedilmeden ana ekrana dönülecek.</p>
      <div className="modal-actions">
        <button onClick={close}>Vazgeç</button>
        <button onClick={discard}>Kaydetmeden çık</button>
        <button onClick={save}>Kaydet</button>
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
    <div className="modal" role="dialog">
      <h2>Nasıl kaydetmek istersiniz?</h2>
      <p>
        Görsel PNG olarak dışa aktarılır; proje düzenlemeye devam etmek için
        saklanır.
      </p>
      <div className="modal-actions">
        <button onClick={close}>Vazgeç</button>
        <button
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
