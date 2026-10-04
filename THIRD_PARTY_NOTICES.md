# Third-party notices

PixelMend repository code: Apache-2.0. Runtime dependencies are locked in `engine/uv.lock` and `apps/desktop/pnpm-lock.yaml`.

- Electron: MIT
- React: MIT
- FastAPI: MIT
- Pillow: HPND
- OpenCV: Apache-2.0
- ONNX Runtime: MIT
- LaMa ONNX model: Apache-2.0; immutable revision and SHA-256 are recorded in `engine/src/pixelmend_engine/model_store.py`.
- MI-GAN Places2 weights: MIT; source and pinned artifact metadata are recorded in `engine/src/pixelmend_engine/model_catalog.py`.
- Real-ESRGAN weights: BSD-3-Clause; [license copy](tools/model-export/LICENSE.Real-ESRGAN.txt), [x4plus provenance](tools/model-export/x4plus-provenance.json), and [general-x4v3 provenance](tools/model-export/general-provenance.json).
- BasicSR-derived export architectures: Apache-2.0; [exporter notices](tools/model-export/NOTICE.md).

Model weights are downloaded separately and are not bundled with the application.
The runtime catalog records license URLs, immutable revisions, sizes and hashes.
SDXL and Swin2SR are unavailable in this RC. Licenses for downloaded models
remain separate from PixelMend's source-code license.

Benchmark photograph sources and license evidence are recorded in
`engine/bench/photograph-manifest.json` and the runtime diagnostic fixture manifest.

The isolated generative runtime is locked separately in
`engine/generative-runtime/uv.lock`:

- MFLUX: MIT; [source](https://github.com/mflux-community/mflux).
- MLX and MLX-LM: MIT; [MLX](https://github.com/ml-explore/mlx),
  [MLX-LM](https://github.com/ml-explore/mlx-lm).
- PyTorch: BSD-3-Clause; [license](https://github.com/pytorch/pytorch/blob/main/LICENSE).
- Transformers: Apache-2.0; [license](https://github.com/huggingface/transformers/blob/main/LICENSE).
- FLUX.2 Klein distilled 4B: Apache-2.0; immutable source revision
  `e7b7dc27f91deacad38e78976d1f2b499d76a294`,
  [official model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B).
  Supported linear weights are converted to MLX 4-bit/group64; VAE weights are unchanged.
- OPUS-MT Turkish–English, `Helsinki-NLP/opus-mt-tc-big-tr-en`:
  Helsinki-NLP Research Group, OPUS-MT project; original weights unchanged;
  immutable revision `2261c8fc7b1af59caee87f8ff0ecf3fbccfe8391`;
  [model card](https://huggingface.co/Helsinki-NLP/opus-mt-tc-big-tr-en),
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  Attribution and license link are also retained in the installed package NOTICE.

Mac generative packages include original dependency notices under the runtime
resources' `pixelmend-licenses` directory. PyTorch is present; MLX operation does
not imply that Torch is absent. The rejected Qwen translation candidate is not
an installed or silently selectable model.
