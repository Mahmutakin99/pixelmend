# PixelMend Platform and Final Delivery Implementation Plan

> **For agentic workers:** Implement task by task with `superpowers:executing-plans`. Checkboxes track evidence, not intent.

**Goal:** Ship reviewed, testable PixelMend packages and companion offline test kits for macOS arm64, Windows x64 and Linux x64, with final M4 installation.

**Architecture:** Keep the existing native packaging matrix and in-app diagnostic runner. Build and test packages independently per OS; on Windows/Linux distinguish CI CPU/package evidence from tester hardware evidence. Complete M4 installation after phase A's model gates.

**Tech Stack:** Electron Builder, PyInstaller, GitHub Actions, React, Python, platform shell/PowerShell, offline HTML/JSON/ZIP reports.

**Spec:** `docs/verification/final-delivery-next-steps.md`; this is phase B of two and depends on `2026-09-23-pixelmend-models-and-quality.md` for six-model final acceptance.

## Global constraints

- Target package platforms: macOS Apple Silicon arm64, Windows x64, Linux x64. Unsigned native test builds do not imply signed public distribution.
- Test launchers need no developer tooling on tester machines. Output remains local until a user manually shares the ZIP.
- Reports must exclude personal photos, desktop screenshots, usernames, full paths, credentials and serial numbers. Incomplete/cancelled tests never count as pass.
- A user's open document is never forcibly closed to replace `/Applications/PixelMend.app`.
- Actual GPU support is asserted per provider only after a representative native-device inference with executed-node evidence.

## Review focus

1. Old installed app ignores `--self-test` → launcher keeps a visible failure notice rather than reporting success.
2. Desktop is redirected or unwritable → prompt for a writable location and retain partial report.
3. Sidecar hangs or crashes → terminate only the diagnostic process tree, preserve checkpoints and produce failure evidence.
4. PowerShell/Unix quoting for paths with spaces/non-ASCII → launcher uses exact selected executable and output directory.
5. User saves while a document changes → saved marker represents only the captured revision; subsequent edits still prompt.

## Task 1 — Native test kit and report reliability

**Files:** `tools/diagnostics/PixelMend-Test.sh`, `PixelMend-Test.ps1`, `tools/ci/make-test-kit.mjs`; `apps/desktop/electron/diagnostic-{host,runner,report,ui}.cjs`; `.check.cjs` tests.

- [ ] Test macOS, Windows and Linux launcher path selection with spaces and Unicode, old app detection, unwritable Desktop, cancel and process timeout. Preserve a startup-failure text file when the app cannot produce a ZIP.
- [ ] Make report status depend on completed checks, actual provider execution and model readiness; keep missing/unsupported/resource-limit separate. Keep bounded logs and atomic JSON/HTML/ZIP checkpoints.
- [ ] Add or repair packaged GUI tests for all four brush modes, pointer capture loss, zoom/Retina ring geometry, save/undo/reopen, settings persistence, 1× enhancement, preview apply/cancel, model install/cancel/retry and keyboard access.
- [ ] Run report sanitization and launcher tests; inspect the generated offline HTML and ZIP after intentional crash/cancel. Confirm no local paths/tokens/personal media leak.

**Gate:** A nontechnical tester can run the package plus launcher and return one readable ZIP; failures still leave an actionable local report.

## Task 2 — Platform runtime and package matrix

**Files:** `engine/pyproject.toml`, `engine/uv.lock`, `engine/pixelmend-engine.spec`, `engine/src/pixelmend_engine/execution_profile.py`, `.github/workflows/package-verify.yml`, `apps/desktop/package.json`, `tools/ci/package-evidence.mjs`.

- [ ] Build macOS arm64 DMG/ZIP, Windows x64 NSIS and Linux x64 AppImage/deb with pinned dependency graphs, hashes, SBOM and matching companion test kit. Keep the current CPU package smoke gate.
- [ ] For Windows/Linux, select only providers present in the packaged runtime and passing a model-specific native probe. Align CUDA/cuDNN with the selected ONNX Runtime build; DirectML remains conditional on its packaged binary and device test. CPU works when an accelerator is absent.
- [ ] Run a packaged application job on each native CI runner; confirm startup/authenticated sidecar, model installation from the pinned manifest, one AI operation, cancellation and graceful shutdown. Record architecture/driver/provider facts without personal identifiers.
- [ ] Ask physical Windows/Linux testers to run the app and offline kit, review UI, and manually return ZIPs. Mark CUDA/DirectML as verified only for the exact machine/runtime/model that executed it; VM emulation or provider registration alone is insufficient.

**Gate:** Three native packages install/open; CPU inference and diagnostic reports work. GPU claims require returned physical-device evidence.

## Task 3 — Final UI and accessibility pass

**Files:** `apps/desktop/src/main.tsx`, `Settings.tsx`, `style.css`, `tokens.css`, `electron/diagnostic-ui.cjs`; UI regression tests and screenshots in `docs/verification/`.

- [ ] Inspect start, editor and every tool, all settings sections, model states, processing, comparison, save, unsaved exit and error screens in light/dark themes at 800×600, normal and wide sizes. Fix clipping, spacing, disabled-state explanation and focus before recapturing.
- [ ] Check Tab order, Escape/Enter, save/undo shortcuts, readable names, contrast and reduced motion. Preserve document, mask, preview and zoom when entering/leaving settings.
- [ ] Prove save → Home does not prompt again, while a later edit, failed save or save-time edit does. Verify PNG/project reopen and that drawing/selection circles remain visible during drag.
- [ ] Use real packaged renderer screenshots and human visual review; record what was observed separately from automated DOM assertions.

**Gate:** All enumerated screens and interactions have reviewed screenshots; known defects are fixed or explicitly documented as release blockers.

## Task 4 — M4 installation, final acceptance and handoff

**Files:** `README.md`, `DURUM.md`, `docs/verification/` final report, package manifests and test artifacts.

- [ ] Finish phase A's six-model quality gate, then run full engine, desktop, production build and package tests. Run the packaged app and diagnostic kit on M4 with a clean profile and with the existing model depot.
- [ ] Confirm install/cancel/retry, six actual AI jobs, save/reopen, application restart and identical verified model paths after install. Record model hash, revision, executed providers, timings, memory and screenshot review.
- [ ] Check whether PixelMend is open with unsaved work before replacing `/Applications/PixelMend.app`; defer replacement if so. Preserve a recoverable prior app and verify the installed copy after replacement.
- [ ] Remove only proven obsolete project outputs and this task's temporary files, with recoverable handling for user-owned old files. Do not rewrite Git history. Update `DURUM.md`, README folder purposes, release manifest and final pass/fail matrix.
- [ ] Commit verified slices, push the feature branch under the existing user authorization, and hand over packages, test-kit links, report ZIPs and explicit Windows/Linux GPU limitations.

**Gate:** Working tree clean, installed M4 app independently rechecked, platform artifacts available, all six model gates passed or any shortfall clearly identified as preventing “nihai” status.

## Provider references to recheck at implementation time

- Windows DirectML requirements and sequential-session restrictions: https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html
- NVIDIA CUDA/cuDNN package compatibility: https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html
- Apple Core ML provider behavior: https://onnxruntime.ai/docs/execution-providers/CoreML-ExecutionProvider.html
