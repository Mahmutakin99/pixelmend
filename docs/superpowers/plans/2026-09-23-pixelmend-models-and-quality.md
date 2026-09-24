# PixelMend Model Completion and Quality Implementation Plan

> **For agentic workers:** Implement task by task with `superpowers:executing-plans`. Checkboxes track evidence, not intent.

**Goal:** Deliver six distinct, verified AI models with honest availability, measured M4 behavior, and reproducible visual acceptance. A blocked model is replaced only after a separately recorded source, licence and hardware gate.

**Architecture:** Keep the current authenticated Electron → FastAPI → single job queue boundary. ONNX models use the existing verified manager and adapter lease; HAT/SDXL may use an isolated worker if ONNX is unsuitable. A model becomes `ready` only after file verification, actual inference and its acceptance gate.

**Tech Stack:** React/TypeScript, Electron, Python 3.12, FastAPI, ONNX Runtime, optional pinned PyTorch/Diffusers worker, PyInstaller.

**Spec:** `docs/verification/final-delivery-next-steps.md`; this plan is phase A of two. Phase B is `2026-09-23-pixelmend-release-and-platforms.md`.

## Global constraints

- Six distinct models after the documented source/licence substitutions: upscale General x4v3 / x4plus / Swin2SR Real-World x4; remove MI-GAN 512 Places2 / LaMa / SDXL Inpainting. Classic Lanczos/OpenCV remain separate.
- Default tier is balanced; selected tier never silently changes. `preserve_size` returns exact source dimensions.
- AI outputs preserve source alpha; inpainting preserves every unselected RGB pixel exactly.
- M4/16 GB acceptance is measured, not inferred from provider availability. Windows/Linux GPU measurements belong to phase B.
- A failed license, integrity, parity, memory or quality gate leaves that model `unavailable`; the six-model deliverable remains incomplete.
- New public model publication requires its own reviewed artifact set; the previous approval covered only the two already published RealESRGAN files.

## Review focus

1. Same weights under two tier names → compare pinned SHA-256 and source identity before catalog activation.
2. Partial/malformed multi-file download → atomic directory activation and restart tests.
3. GPU provider loaded but no nodes executed → require executed-node evidence and CPU comparison.
4. Cancellation during native inference → no result, no leaked lease, no automatic retry.
5. Wide photo/4× output consumes excess RAM or disk → preflight refusal with an actionable error.

## Task 1 — Advanced upscale: Swin2SR Real-World x4

> 2026-09-23 decision: Real HAT GAN x4 remains technically verified but its
> checkpoint distribution terms are not explicit enough for PixelMend. The user
> authorized a comparable, clearly licensed replacement. Evaluate
> `caidas/swin2SR-realworld-sr-x4-64-bsrgan-psnr` (Apache-2.0) as the advanced
> model; do not retain the HAT product label.

**Files:** `tools/model-export/export_swin2sr.py`; `engine/src/pixelmend_engine/models/swin2sr_onnx.py`; candidate report and adapter tests.

- [x] Pin the Apache-2.0 Swin2SR source and weight hash. Export a local ONNX candidate, recording the contract and output equivalence in `swin2sr-realworld-x4-candidate-2026-09-23.md`.
- [x] Compare PyTorch reference against exported ONNX on 64 × 64, 72 × 64 and 64 × 72. All passed below the recorded rtol/atol threshold.
- [x] Run M4 CPU, Core ML and native MPS tile trials. Dynamic Core ML fails; fixed 64px runs but has mixed CPU placement and marginal gain; fixed 128px slows severely. MPS is faster on small tiles. None of these trials activates the card.
- [ ] Add lifecycle tests for missing, corrupt, cancelled, retry, restart and use-while-delete. Run `engine/.venv/bin/python -m pytest engine/tests/test_model_manager.py engine/tests/test_real_models.py -q`.
- [ ] On the M4, record real node execution, CPU and Core ML cold/warm durations, peak memory, disk and 1×/2×/4× visual outputs. A speed or quality advantage must be observed on the chosen hard cases before the UI calls this tier “Gelişmiş”.

**Gate:** Separate verified artifact, parity report, actual inference and M4 quality review; otherwise leave its catalog entry unavailable.

## Task 2 — Fast removal: MI-GAN 512 Places2

> 2026-09-23 decision: the official LaMa Regular checkpoint is not presently
> available with a verifiable redistribution grant. The user authorized a
> comparable replacement. Evaluate
> `mlx-community/MI-GAN-512-places2-fp16` (MIT) as the M4 fast on-device model;
> retain an explicit platform availability boundary until a Windows/Linux path
> is measured.

**Files:** `model_catalog.py`, `models/migan_onnx.py`, `jobs.py`, `main.py`; desktop IPC/UI tests and provenance report.

- [x] Pin the official MI-GAN 512 Places2 ONNX pipeline, its MIT weight grant, size and SHA-256. It is separate from the balanced LaMa artifact.
- [x] Adapt the model's known-pixel mask convention, force an exact selection-only composite, and add unit coverage for both. MI-GAN is selected explicitly by model ID; it never falls back to balanced LaMa.
- [x] Verify actual M4 CPU inference and outside-mask equality. Core ML compilation fails, so the selected provider is honestly CPU.
- [x] Run installation/probe coverage and review flat, texture, structure, edge and wide-mask photos against balanced LaMa and OpenCV, including 1600 × 900 and 2400 × 1350. The measured speed benefit supports the Hızlı label; visual review restricts it to that tier.

**Gate:** Distinct weights and measured advantage, plus mask and lifecycle tests.

## Task 3 — SDXL Inpainting 0.1

**Files:** New isolated `engine/src/pixelmend_engine/models/sdxl_worker.py` and process protocol; `model_manager.py`/`model_store.py` multi-file package support; `jobs.py`, `job_api.py`, `model_catalog.py`; worker/manager/queue tests; license record.

- [ ] Pin the exact Hugging Face model revision and all required file hashes (weights, tokenizers, configs, schedulers). Review the CreativeML Open RAIL++-M model license and every dependency's distribution terms against planned commercial use; save the review before distribution.
- [ ] Install the file set in a staging directory, verify every required file, then atomically rename a complete package. Test missing/corrupt files, cancellation, retry and restart. A partial package is never `ready`.
- [ ] Run one heavy job in an isolated worker; M4 uses measured MPS if supported, otherwise measured CPU. Release ONNX sessions before loading it. Set deterministic seed, default background-completion prompt and bounded mask/context crop; retain debugging parameters in result details.
- [ ] Composite only masked pixels into source RGB and preserve original alpha byte-for-byte. Test empty/large/border masks, worker crash, cancel, out-of-memory and resource preflight. Do not claim CPU support without a complete representative run.
- [ ] Review real flat/texture/structure/edge/large-selection outputs against LaMa and OpenCV. Record artifacts, durations, memory and disk on 1600×900 and 2400×1350 when admitted; if M4/16 GB cannot support a representative job, mark it unavailable on this device with a clear resource reason.

**Gate:** Complete licensed file set, real M4 run, exact preservation and human visual review. The model card documents difficult faces/text and quality limits.

## Task 4 — Shared runtime and model UX

**Files:** `execution_profile.py`, `adapter_cache.py`, `fallback.py`, `policy.py`, `jobs.py`, `model_catalog.py`; `apps/desktop/src/Settings.tsx`, `main.tsx`, `models.ts`, `preferences.ts`; corresponding tests.

- [x] Evict an unused adapter before allocating the next heavy session; verify switch order and lease safety. Keep at most one heavy native job active.
- [ ] Implement low-resource mode through a validated IPC/job field: smaller ONNX tiles and limited CPU threads. Prove output dimensions and permitted quality tolerance match automatic mode; do not promise GPU temperature or utilization limits.
- [ ] Cache provider probe results by model hash, runtime, OS/device and driver identity. A short health check must precede reuse; invalidated profiles remeasure. Store only provider and timing summary, never raw trace paths.
- [ ] Expose selected model/revision, actual executed providers and CPU retry reason in job and UI. A GPU failure retries the **same** model once on CPU only if capacity permits; cancellation never retries.
- [ ] Show model-specific download size, tested memory range, suitability and one primary action. Unmeasured minimum memory remains explicitly unmeasured.

**Gate:** Run full engine/desktop tests and representative real jobs after switching all installed models.

## Task 5 — Six-model acceptance and records

**Files:** `apps/desktop/electron/diagnostic-photographs.cjs`, `diagnostic-runner.cjs`, `engine/src/pixelmend_engine/diagnostics.py`, `engine/bench/`, `docs/verification/`; diagnostic tests.

- [ ] Extend the tester's allowlist to all six distinct algorithms and provider paths. Missing/unsupported/CPU fallback status stays explicit; a provider name alone never passes the acceleration check.
- [ ] Run 12 licensed photos per upscale model at 1×, 2× and 4×; include 1600×900 and 2400×1350 where safe. Compare to Lanczos for detail, seams, halo, color, alpha, faces and text. Preserve original and output images for visual review.
- [ ] Run each remove model on flat, texture, structure, edge and wide-mask cases. Compare to OpenCV and verify outside-mask RGB and alpha exactly.
- [ ] Measure cold and warm time, peak process-tree RSS, temporary disk and cancellation separately; avoid labeling a warmed probe as cold. Declare system requirements only from measured sizes with margin.
- [ ] Update `DURUM.md`, `docs/verification/diagnostic-delivery.md`, model/license records and release notes with pass/fail evidence. Run `engine/.venv/bin/python -m pytest engine/tests -q`, `corepack pnpm --dir apps/desktop test`, `corepack pnpm --dir apps/desktop build`; run real-model acceptance with no silent skips.

**Gate:** Phase A is complete only when all six models pass. Any failing model stays visibly unavailable and is carried as an open release blocker into phase B.

## Primary sources to verify during execution

- HAT normal GAN weights and repository license: https://github.com/XPixelGroup/HAT
- LaMa Regular/Places checkpoint references and license: https://github.com/advimman/lama
- SDXL Inpainting model card, immutable files and Open RAIL++ terms: https://huggingface.co/diffusers/stable-diffusion-xl-1.0-inpainting-0.1
- ONNX Runtime provider behavior and actual graph placement: https://onnxruntime.ai/docs/execution-providers/
