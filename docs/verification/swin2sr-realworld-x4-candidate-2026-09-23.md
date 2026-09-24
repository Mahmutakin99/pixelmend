# Swin2SR Real-World x4 candidate — 2026-09-23

## Provenance

- Source: `caidas/swin2SR-realworld-sr-x4-64-bsrgan-psnr` at
  `bb13f02e45e88d00b6c202b3fbe6a181af144606`, Apache-2.0.
- Pinned PyTorch source: `pytorch_model.bin`, 48,460,141 bytes,
  SHA-256 `4a5f52a20932085557ed115f87c0ee8385e12f2719108c0dfd38c64aedea4710`.
- Local derived candidate: `swin2sr-realworld-x4-fp32.onnx`, 54,006,618 bytes,
  SHA-256 `cd0125007fe9848174333a602603e15f0b500900aa5c40956865d9a520049241`.
- Contract: FP32 NCHW RGB in 0..1, attention-window-aligned dimensions,
  natural 4× RGB output. PixelMend pads only edge tiles to eight-pixel windows
  and crops before feathered compositing.

## Equivalence

PyTorch and ONNX Runtime CPU outputs passed at 64 × 64, 72 × 64 and 64 × 72.
The maximum absolute errors were 2.74e-6, 3.58e-6 and 3.64e-6 respectively;
the threshold was rtol 3e-3 / atol 3e-4.

## M4 result and gate

At a 64 × 64 tile, CPU warm inference measured 0.304 seconds. ONNX Runtime
found Core ML subgraphs, but Core ML could not build a working execution plan
for this dynamic graph (error code `-14`). The candidate is therefore **not**
an accelerated advanced model on this M4 and is not activated or published.

The photographed acceptance runner confirmed visibly sharper 4× detail than
Lanczos for the `camera` fixture, but its CPU cost does not fit this product
tier: the camera 2× cold run measured 7.19 seconds and the eagle 2× cold run
10.66 seconds at the reviewed 192-pixel maximum-edge input. The eagle 4× case
did not complete before the acceptance runner's one-minute command boundary.
This is a failed performance gate, not a claim that the model is unreliable.

It remains a documented, local candidate. A working, packaged acceleration
path and full-photo visual acceptance are required before the Gelişmiş card
can become available.

## 2026-09-24 M4 follow-up: fixed ONNX shapes and native MPS

The pinned source was downloaded again and hash-verified. A fresh dynamic ONNX
export passed PyTorch parity on 64×64, 72×64 and 64×72 inputs (largest absolute
error 3.34e-6). This export is local and unpublished; its SHA-256 is
`6a8fee24c948b656b2c313d7a1c15b284cf51774241dfd3c9d1d2dd528b86a55`.

Fixed-shape 64×64 and 128×128 ONNX experiments were run with the application's
ONNX Runtime 1.30.0 on this M4. The 64×64 Core ML profile recorded 580 Core ML
and 1,440 CPU node events over four calls. Warm times were 0.342, 0.323 and
0.336 seconds, versus CPU's 0.378, 0.373 and 0.366 seconds. The 128×128 Core ML
profile recorded 435 Core ML and 1,080 CPU node events over three calls, but
inference times worsened from 4.274 to 43.551 and 89.813 seconds; CPU stayed
at 1.521 and 1.487 seconds. Output maximum absolute difference from CPU was
under 3.2e-6 in both fixed-shape trials. These observations rule out the 128px
Core ML route as a product default.

PyTorch 2.7.1 with native MPS did run. After its first compilation, 64×64 took
0.157–0.158 seconds and 128×128 took 0.605–0.624 seconds; the same PyTorch CPU
runs took 0.345–0.349 and 1.442–1.46 seconds respectively. This is a viable
candidate backend for further packaging and full-photo review, not acceptance
of the advanced model. No 1600×900/2400×1350 end-to-end run, peak-memory
measurement, app integration, or 12-photo visual gate was performed here.
