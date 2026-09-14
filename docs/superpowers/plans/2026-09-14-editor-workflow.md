# PixelMend continuous editor implementation

Approved specification: the conversation's final plan dated 2026-09-14.

## Global constraints
- Local macOS Apple Silicon; no accounts, telemetry or external inference.
- Normal paint is separate from the photo. Normal eraser erases paint ONLY.
- Object selection is separate from paint, never exported. Object removal edits current photo.
- Processing -> preview -> Apply/Discard. Cancel running jobs; Undo applied changes.
- Unified history including paint, selection and applied results; preserve history on project reopen.
- Home, settings, TR/EN, theme; three ordered groups Paint, Object eraser, Upscale.
- PNG/JPEG/WebP/TIFF export; ZIP .pixelmend v1 project with hashed PNG blobs, 4 GiB expanded limit.
- rc.2 unsigned package, real packaged E2E; do not overwrite old RC.

## Task 1: Renderer document, canvas and screens
Implement typed immutable document/history, normal paint/erase, selection paint/erase, incremental live strokes, preview/apply/discard, zoom/pan, home/settings/recent/recovery, localization, export/project actions, keyboard/accessibility and tests. Own apps/desktop/src only. Use the bridge contract below. No engine paths or tokens in renderer. Pixel blobs are disk-backed opaque references. History holds stroke commands and photo refs, not full RGBA arrays. Each stroke stores its own color/opacity/size/hardness. Upscale scales paint/selection coordinates and widths by two, preserving separation. Preview does not mutate history. Apply removal clears selection; Undo restores it. Settings/window actions are not history. Recovery is debounced 2s after stable changes. Dirty guard on open and close, applied project saved vs exported distinct.

## Shared bridge contract (window.pixelmend)
BlobRef = {id:string,uri:string,width:number,height:number}; id SHA256 PNG.
openImage(): Promise<BlobRef|null>; importFile(file:File): Promise<BlobRef> (preload uses webUtils.getPathForFile); putBlob(base64:string): Promise<BlobRef>.
startJob({photoId:string,mask?:string,operation:'remove'|'upscale'}): Promise<{job_id:string}>.
job(id): Promise<{job_id:string,status:string,error?:{code:string,message:string}|null}>.
result(id): Promise<BlobRef>; cancel(id): Promise<unknown>; releaseJob(id): Promise<void>; restartEngine(): Promise<void>.
saveImage({photoId:string,paint:string,format:'PNG'|'JPEG'|'WEBP'|'TIFF'}): Promise<boolean> (paint base64 PNG in current dimensions, transparent paint only).
saveProject(document:unknown,saveAs?:boolean): Promise<boolean>; openProject(recentId?:string): Promise<unknown|null>.
saveRecovery(document:unknown): Promise<void>; recovery(): Promise<unknown|null>; clearRecovery(): Promise<void>.
settings(): Promise<{language:'tr'|'en',theme:'system'|'light'|'dark',maskColor:string,maskOpacity:number}>; setSettings(settings): Promise<void>.
recent(): Promise<{id:string,name:string}[]>; clearRecent(): Promise<void>.
models(): Promise<{ready:boolean,state:string,progress:number,error?:string}>; modelAction('download'|'cancel'|'remove'): Promise<void>.
onAction(callback:(action:string)=>void): ()=>void; confirmClose(): Promise<void>.
Menu/close actions: open, save-project, export, undo, redo, settings, close.

Project document shape must be shared with main validator before completion; send decision early. Main discovers photo references by id+uri fields in serialized document and packs only those PNGs. URI reconstructed on reopen. No absolute paths supplied by renderer. All errors use stable codes/messages localized by renderer.

## Task 2: Native bridge, disk blobs, archive and engine adapters
Parent implements electron modules and Python export/model adapters using tests first. Hashed session PNG disk storage, atomic project/recovery/settings writes, ZIP validation, bounded protocol reads, model state, engine lifecycle, menus, IPC sender validation. Preserve old files and no arbitrary path IPC.

## Task 3: Integration and acceptance
Real Electron test: home -> import -> paint and eraser live -> object mask -> remove preview -> discard -> remove/apply -> second edit -> undo/redo -> upscale/apply -> export pixels -> project reopen/history -> settings language -> cancel/missing model. Python/Vitest/TS build; frozen engine, rc.2 DMG/ZIP/checksum; docs and broad review.

## Progress and rulings
- Baseline main 08d020d clean; user explicitly permits current branch.
- Interface scan: renderer consumes native APIs above; native consumes project serialized document and PNG only; no overlapping implementation files.
- Ruling: vector stroke history retained across upscale with transformed coordinates; avoids flattening paint and keeps paint eraser semantics.
- Ruling: initial scope fixed photo plus one paint layer, no general layer editor.
