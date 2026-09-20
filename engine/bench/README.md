# AI upscale benchmark

`run_upscale.py` accepts a local JSON fixture manifest and records cold/warm timing inputs, host RSS, provider, model and fixture hashes. Fixture files are intentionally excluded from git.

Only 12 approved CC0-1.0 or public-domain photographs may be used. Every entry must provide its immutable local `path`, direct `source_url`, `license`, download date, SHA-256, decoded input dimensions, and intended use. The runner rejects missing provenance, a changed file, or mismatched decoded dimensions. It does not publish a quality verdict: review the generated result set and tile-boundary crops before selecting a default backend.

Example:

```json
[{"id":"photo-01","path":"/absolute/approved/photo-01.png","source_url":"https://…","license":"CC0-1.0","downloaded_at":"2026-09-15","sha256":"…","input_width":2048,"input_height":1365,"expected_use":"upscale"}]
```

Run from `engine/` after the candidate passes export parity:

```sh
PYTHONPATH=src .venv/bin/python bench/run_upscale.py --model ../engine/models_cache/export/realesrgan-x4plus-fp32.onnx --fixtures /absolute/fixtures.json --out /private/tmp/pixelmend-upscale-benchmark.json
```

For this Mac delivery, `fetch_photographs.py` restores the 12 reviewed files from
`docs/verification/photograph-manifest.json`, verifies original and prepared hashes,
and writes `fixtures/manifest.json`. The reviewed inputs are max-edge-192 RGB
thumbnails; original photographs are retained separately. This keeps the benchmark
scope explicit. `run_upscale.py` now requires exactly 12 distinct IDs, samples RSS
during inference, records session-load time separately, and saves AI/Lanczos PNGs.
`run_lama.py` (run from repository root) creates the four removal comparison sheets.
The measurements and visual verdict are in `docs/verification/mac-acceptance.md`.
