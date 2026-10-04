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
