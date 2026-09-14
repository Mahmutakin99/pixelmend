# Third-party notices

PixelMend repository code: Apache-2.0. Runtime dependencies are locked in `engine/uv.lock` and `apps/desktop/pnpm-lock.yaml`.

- Electron: MIT
- React: MIT
- FastAPI: MIT
- Pillow: HPND
- OpenCV: Apache-2.0
- ONNX Runtime: MIT
- LaMa ONNX model: Apache-2.0; immutable revision and SHA-256 are recorded in `engine/src/pixelmend_engine/model_store.py`.

Model weights are downloaded after explicit use and are not included in this RC. Stable Diffusion, SDXL and Real-ESRGAN are not included in this candidate.
