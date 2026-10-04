# Changelog

PixelMend uses Semantic Versioning. Release candidates use `1.0.0-rc.N`; model artifacts and release signing are published separately.

## 1.0.0-rc.4

- Open the editor before model verification completes; keep basic editing available while AI prepares in the background.
- Wait for model readiness in diagnostics and preserve partial reports on startup errors or cancellation.
- Show the packaged application version in About.

## 1.0.0-rc.2

- Native vector-stroke masks and paint exports avoid full-resolution renderer canvases.
- Export removes EXIF, GPS, XMP and embedded thumbnails while retaining normalized sRGB ICC and alpha semantics.
- Sidecar sessions are marked, ephemeral and TTL-cleaned; no user image recovery occurs after restart.

## 1.0.0-rc.1

- Local Apple Silicon Electron candidate with authenticated Python sidecar.
- OpenCV Telea/Navier-Stokes, LaMa object removal and Lanczos 2×/4× paths.
- Normalized image import, metadata-sanitized export, mask strokes, undo/redo and result preview.
- Test build only: no Developer ID signature, notarization, Real-ESRGAN or Stable Diffusion runtime.
