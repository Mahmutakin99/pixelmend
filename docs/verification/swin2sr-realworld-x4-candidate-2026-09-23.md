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

It remains a documented, local candidate. A different advanced model or a
verified conversion that passes actual Core ML execution and visual acceptance
is required before the Gelişmiş card can become available.
