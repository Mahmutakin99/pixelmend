# MI-GAN 512 Places2 candidate — 2026-09-23

## Provenance and licence

- Model: `andraniksargsyan/migan` at commit
  `406830d0fa60666da0071c342ad2fbc8f30c5c64`.
- Artifact: `migan_pipeline_v2.onnx`, 28,079,181 bytes,
  SHA-256 `6f1f3530a1a2324b19752018ce756088b07973cda8d7d890034ace5c8a48c40b`.
- The official MI-GAN repository links this ONNX pipeline for application
  integration. Its `LICENSE-WEIGHTS` grants MIT rights, including distribution.
- Contract: dynamic uint8 NCHW RGB image plus uint8 NCHW mask; 255 in the
  model mask means known pixels. PixelMend inverts its selected-area mask only
  at this boundary, then composites the result only within the selection.

## M4 measurement

The real M4 run used a 160 × 192 RGB image and a 55 × 50 selected region.

| Backend | First run | Warm run | Result |
| --- | ---: | ---: | --- |
| CPUExecutionProvider | 0.187 s | 0.180 s | Passed; 508 profiled CPU nodes |
| CoreMLExecutionProvider + CPU | — | — | Rejected at Core ML compilation: `gaussian_blur/Conv` is missing required `pad` |

The application therefore records CPU as the selected provider for this pinned
artifact on this M4. It does not present Core ML registration as GPU execution.
The adapter's explicit composite made all pixels outside the selected mask
byte-for-byte equal to the source in the real run. Alpha remains owned by the
job layer and is preserved unchanged.

## Status

The comparison runner evaluated MI-GAN, balanced LaMa and OpenCV on flat,
texture, structure, edge and wide-selection scenes, including 1600 × 900 and
2400 × 1350 rocket images. Every model result preserved the unselected RGB
pixels exactly.

MI-GAN completed the four smaller scenes in 0.168–0.191 s, while LaMa took
1.251–1.391 s in the same process. At 1600 × 900 and 2400 × 1350 MI-GAN took
0.182 s and 0.202 s; LaMa took 1.297 s and 1.289 s. These are warm in-process
measurements, not cold-start claims. Peak process RSS includes both loaded
models and reached about 1.90 GiB at 2400 × 1350.

Visual review of the generated sheets found MI-GAN close to LaMa on the small
flat and wood-texture removals. Its brick continuation is simpler than LaMa's,
and its wide rocket selection leaves implausible structure. It is therefore a
verified, installable **Hızlı** removal choice only: its card must retain the
warning that fine detail and difficult selections can be more limited. The
Dengeli and Gelişmiş choices are never silently substituted.
