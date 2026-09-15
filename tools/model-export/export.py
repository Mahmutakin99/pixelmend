"""Reproduce and parity-gate the local, unpublished RealESRGAN x4 candidate."""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import urllib.request

import numpy as np
import onnx
import onnxruntime as ort
import torch

from rrdbnet import RRDBNet

WEIGHTS_URL = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
WEIGHTS_SHA256 = "4fa0d38905f75ac06eb49a7951b426670021be3018265fd191d2125df9d682f1"
LICENSE_COMMIT = "a4abfb2979a7bbff3f69f58f58ae324608821e27"
BASICSR_COMMIT = "651835a1b9d38dbbdaf45750f56906be2364f01a"
LICENSE_URL = f"https://raw.githubusercontent.com/xinntao/Real-ESRGAN/{LICENSE_COMMIT}/LICENSE"
DEFAULT_OUT = Path(__file__).resolve().parents[2] / "engine/models_cache/export"


def sha256(path):
    # Stream artifacts to avoid a second full model-sized allocation.
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def fetch(url, target, expected_sha256=None):
    # No checkpoint is loaded before its pinned digest is verified.
    if not target.exists():
        temporary = target.with_suffix(target.suffix + ".part")
        try:
            with urllib.request.urlopen(url, timeout=60) as response, temporary.open("wb") as handle:
                while chunk := response.read(1024 * 1024):
                    handle.write(chunk)
            if expected_sha256 and sha256(temporary) != expected_sha256:
                raise ValueError("Downloaded source hash mismatch")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    if expected_sha256 and sha256(target) != expected_sha256:
        raise ValueError("Cached source hash mismatch")


def parity(model, path):
    # Multiple asymmetric dimensions catch exports accidentally frozen to trace size.
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    session = ort.InferenceSession(str(path), sess_options=options, providers=["CPUExecutionProvider"])
    rng = np.random.default_rng(20260915)
    rows = []
    with torch.inference_mode():
        for height, width in [(8, 8), (11, 17), (24, 19), (32, 40)]:
            array = rng.random((1, 3, height, width), dtype=np.float32)
            expected = model(torch.from_numpy(array)).numpy()
            actual = session.run(["output"], {"input": array})[0]
            if actual.shape != (1, 3, height * 4, width * 4) or not np.isfinite(actual).all():
                raise ValueError("Invalid ONNX output")
            difference = np.abs(expected - actual)
            # Compare raw FP32 results before uint8 clipping can conceal divergence.
            np.testing.assert_allclose(actual, expected, rtol=2e-3, atol=2e-4)
            rows.append({"input_shape": list(array.shape), "max_abs_error": float(difference.max()),
                         "mean_abs_error": float(difference.mean()), "passed": True})
            print(json.dumps(rows[-1]), flush=True)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    weights = args.output_dir / "RealESRGAN_x4plus.pth"
    fetch(WEIGHTS_URL, weights, WEIGHTS_SHA256)
    license_path = args.output_dir / "LICENSE.Real-ESRGAN.txt"
    fetch(LICENSE_URL, license_path)
    torch.set_num_threads(4)
    torch.manual_seed(20260915)
    model = RRDBNet().eval()
    checkpoint = torch.load(weights, map_location="cpu", weights_only=True)
    model.load_state_dict(checkpoint["params_ema"], strict=True)
    artifact = args.output_dir / "realesrgan-x4plus-fp32.onnx"
    # A failed rerun must never leave stale candidate metadata claiming parity passed.
    candidate = args.output_dir / "candidate-manifest.json"
    candidate.unlink(missing_ok=True)
    staging = args.output_dir / "realesrgan-x4plus-fp32.staging.onnx"
    with torch.inference_mode():
        torch.onnx.export(model, torch.zeros(1, 3, 16, 16), str(staging),
                          input_names=["input"], output_names=["output"],
                          dynamic_axes={"input": {2: "height", 3: "width"},
                                        "output": {2: "height_x4", 3: "width_x4"}},
                          opset_version=17, dynamo=False, export_params=True)
    onnx.checker.check_model(str(staging), full_check=True)
    checks = parity(model, staging)
    staging.replace(artifact)
    provenance = {
        "created_at": datetime.now(timezone.utc).isoformat(), "weights_url": WEIGHTS_URL,
        "weights_sha256": sha256(weights), "weights_size_bytes": weights.stat().st_size,
        "source_release": "v0.1.0", "license_commit": LICENSE_COMMIT, "basicsr_commit": BASICSR_COMMIT,
        "architecture_sha256": sha256(Path(__file__).with_name("rrdbnet.py")),
        "export_script_sha256": sha256(Path(__file__)),
        "uv_lock_sha256": sha256(Path(__file__).with_name("uv.lock")),
        "license_sha256": sha256(license_path), "license_url": LICENSE_URL,
        "platform": platform.platform(), "python": platform.python_version(),
        "packages": {name: importlib.metadata.version(name) for name in ("torch", "onnx", "onnxruntime", "numpy")},
        "graph": {"opset": 17, "dtype": "float32", "layout": "NCHW", "batch": 1,
                  "channels": "RGB", "input_range": [0, 1], "output": "raw; clip 0..1 before uint8", "scale": 4},
        "parity": {"provider": "CPUExecutionProvider", "rtol": 2e-3, "atol": 2e-4, "cases": checks},
        "artifact": {"filename": artifact.name, "size_bytes": artifact.stat().st_size, "sha256": sha256(artifact)},
    }
    (args.output_dir / "export-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    candidate.write_text(json.dumps({"model_id": "realesrgan-x4plus", "published": False,
                                    "intended_repo_id": "pixelmend/real-esrgan-x4plus-onnx",
                                    "revision": None, "license_id": "BSD-3-Clause", "license_url": LICENSE_URL,
                                    **provenance["artifact"]}, indent=2) + "\n")
    print(f"PARITY PASSED: {artifact}", flush=True)


if __name__ == "__main__":
    main()
