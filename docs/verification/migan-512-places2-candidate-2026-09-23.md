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

The model is a verified, installable **Hızlı** removal choice. Its full visual
acceptance across the five removal scenes and the 1600 × 900 / 2400 × 1350
resource measurements remain Phase A acceptance work.
