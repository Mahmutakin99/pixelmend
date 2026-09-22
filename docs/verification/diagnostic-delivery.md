# Portable acceptance runner — implementation ledger

User contract: distribute PixelMend plus a platform launcher; offer missing-model
installation, default to standard tests, optionally run the photograph benchmark,
produce an offline Desktop report for manual sharing. Never label skipped tests as
passed. Keep personal files, paths and secrets out of reports.

Execution: existing clean feature branch `feat/mac-local-ai`; work in place to
preserve the user's current build/dependency environment. Application source
remains private. The two verified RealESRGAN ONNX artifacts were published with
their BSD-3-Clause license, SHA-256 and provenance records at
https://github.com/Mahmutakin99/pixelmend-models/releases/tag/models-2026-09-21.

## Work remaining

- [x] Recoverable, sanitized JSON/HTML/ZIP reports and platform launchers.
- [x] Isolated self-test application mode, installation choice and cancellation.
- [x] Standard real engine/model checks, GUI checks and screenshots.
- [x] Saved-state and cursor regressions covered by automated checks.
- [ ] Four new licensed, pinned model integrations and runtime selection.
- [ ] Native packages, M4 validation and external Windows/Linux acceptance.

## Evidence

Starting inventory: two verified model manifests; four catalog entries have no
manifest. Existing CI smoke exercises OpenCV only. No claim of six-model readiness.

2026-09-22 evidence: release assets were downloaded again and both published
SHA-256 values matched. A fresh temporary model store installed and probed both
RealESRGAN General x4v3 and x4plus on an Apple M4 using CoreMLExecutionProvider.
The Electron standard acceptance runner passed classical operations, both new
models on automatic and CPU paths, cancellation, UI, save/project, selection and
engine shutdown. Its final status is `incomplete`, correctly, because LaMa was
not installed and the three remaining planned model integrations are unavailable.
