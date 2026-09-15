# PixelMend Product Completion Roadmap Design

**Goal:** Turn the working local engine and desktop application into a measured, signed, cross-platform v1 release without enabling unverified AI behavior or storing binary releases in Git.

**Scope:** This roadmap orders the remaining work from low-risk foundations to release gates. It is the planning authority for post-RealESRGAN work; implementation details remain in the phase documents it references.

## Product rules that do not change

- Photos and inference remain local; no cloud image-processing API is introduced.
- AI upscale is unavailable until a public immutable model artifact, licence/provenance record, real probe, and measured benchmark acceptance exist.
- Lanczos remains the no-model fallback.
- Source Git history contains source and reproducibility metadata, not DMG, ZIP, model weights, or generated benchmark payloads. Release binaries belong to GitHub Release assets.
- Unsupported/unknown device capacity is shown as unknown; it is never silently converted into a capability claim.
- A release is not called cross-platform until the actual package and inference path run on its target platform.

## Ordered delivery phases

### 1. Release foundations — easiest, no inference behavior change

Lock publisher/reverse-DNS `appId`, output metadata policy, release numbering and CHANGELOG convention, and final icon direction. Configure protected `main` and GitHub CI to run the existing engine suite and desktop test/build checks for every change.

**Exit gate:** identity and metadata decisions are recorded; CI is required for `main`; no release asset is committed to Git.

### 2. Local lifecycle hygiene

Add the periodic asset TTL driver, disk-backed session cleanup policy, model-store size/revision visibility, and explicit safe cleanup of unused old model revisions. Preserve active jobs, selected model revisions, and user-selected custom model locations.

**Exit gate:** restart, expiry, delete, and insufficient-disk cases are integration-tested; no active model/job is deleted by maintenance.

### 3. Usability and measured performance presentation

Complete the tier recommendation and Performance UI from measured capability/model data. Add accessible state changes, keyboard coverage, clear unsupported/slow/unsafe distinctions, and manual acceptance cases.

**Exit gate:** a clean profile does not silently download a model; every recommendation explains the observed fact or reports it as unmeasured.

### 4. High-resolution editing workflow

Replace the full-resolution browser-canvas dependency for paint layers with a coordinate-mapped preview/overlay design. Keep source pixels in the sidecar and render/edit masks at bounded preview resolution, then materialize a native-size mask for the engine.

**Exit gate:** an image at the 200 MP policy limit can be opened, painted, processed, and exported without allocating a browser canvas at source resolution; geometry and undo/redo have automated coverage.

### 5. Benchmark evidence

Create versioned fixture manifests: 3–4 licence-cleared inpainting fixtures and 12 CC0/public-domain upscale photographs. Capture input hashes, licence/source evidence, provider/model identity, cold/warm timings, RSS/device observations, output dimensions, seam checks, and quality comparisons against Lanczos.

**Exit gate:** benchmark reports are reproducible from manifest plus immutable model reference; no quality or performance marketing claim precedes a report.

### 6. RealESRGAN product activation

Publish `pixelmend/real-esrgan-x4plus-onnx` with a public immutable revision, exact size, SHA-256, model/export/source licences, and export provenance. Put those real coordinates into the catalog, run model download/probe on M4, then run the benchmark gate and enable AI only after it passes.

**Exit gate:** an installed model is byte/hash verified, probe-passed, benchmark-qualified, and selectable in the UI; failures leave Lanczos available.

### 7. Platform decisions and validation

Write the Windows inference backend ADR after a DirectML/Windows ML/CPU investigation on real hardware. Decide Linux CPU/CUDA packaging after real driver/package-size tests. Test each chosen path in an actual target environment rather than inferring it from macOS.

**Exit gate:** each v1 platform has an explicit supported provider, limitations, and repeatable package/inference evidence.

### 8. Package security and delivery chain

Build native PyInstaller/Electron artifacts per OS in CI, produce checksums, SBOM, build manifest, model manifest, and downloaded-artifact smoke evidence. Complete macOS Developer ID signing, hardened runtime, notarization and stapling; choose and implement the Windows signing route.

**Exit gate:** a clean target profile can install, start the authenticated sidecar, run a lightweight edit, save, cancel, and shut down without zombie processes; signatures and checksums validate.

### 9. General release

Create signed GitHub Release assets, release notes, support matrix, known-limitations section, and a user-approved version tag. Do a final manual acceptance pass on every supported platform.

**Exit gate:** every published binary has a matching checksum, signature/provenance record, release note, and successful final smoke report.

## External decisions and authorities

The following cannot be assumed by implementation work:

- Publisher identity, macOS Developer Program/Developer ID, notarization credentials, and Windows signing provider.
- Ownership and publication rights for the RealESRGAN ONNX artifact.
- Fixture licences/source records for benchmark content.
- Approval to create tags and public GitHub Releases.

## Explicitly deferred from v1 release readiness

- SD/SDXL generative filling.
- SwinIR, HAT, SUPIR, and GFPGAN product activation.
- macOS Intel support.

## Dependency flow

`release foundations → lifecycle hygiene → usability → high-resolution workflow → benchmark evidence → RealESRGAN activation → platform validation → signed packages → general release`

Phases 1–4 can be implemented independently of model publication. Phase 5 can prepare fixtures and runner work before publication, but its final AI acceptance needs the phase 6 artifact. Phases 7–9 must not claim a platform or public release before their respective evidence gates pass.
