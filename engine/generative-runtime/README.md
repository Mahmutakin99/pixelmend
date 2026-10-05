# PixelMend local generative runtime

This separate project supplies one-shot Apple Silicon workers for PixelMend.
The engine owns their processes, cancellation, package leases and selected-area
composition. Hardware profiles remain disabled until resource and human quality
acceptance; a successful inference alone does not enable a profile. The existing
ONNX engine never imports this project or its native dependencies at startup.

Python 3.12, MFLUX 0.21.0, MLX 0.32.2 and MLX-LM 0.32.0 are pinned in
`pyproject.toml`; `uv.lock` records the complete dependency graph and hashes.
PyInstaller is a development dependency. Torch is a transitive MFLUX dependency.
`sources.json` records immutable official model revisions and their licenses.
Klein is Apache-2.0; the OPUS-MT translator is CC-BY-4.0 with source attribution.
It is a provenance record, not an installable model manifest: package hashes,
download sizes and accepted profiles must come from validated conversion outputs.

## Development verification

From the repository root:

```sh
uv sync --project engine/generative-runtime --frozen
engine/generative-runtime/.venv/bin/python tools/generative/prepare-macos15.py
engine/generative-runtime/.venv/bin/python -m unittest discover -s engine/generative-runtime/tests
```

From this directory, with the same environment:

```sh
.venv/bin/python -m PyInstaller runtime.spec
```

PyInstaller produces a directory containing its own Python and native components.
Keep the entire directory together. Building successfully is not proof of native
imports, model inference, signing, notarization or macOS 15 compatibility. The installer selects the official macOS 15 MLX wheels from the existing lock
and verifies their actual sizes and SHA256 values; the host would otherwise
prefer the macOS 26 variant. After building, run
`python tools/generative/native-audit.py PATH_TO_RUNTIME`. Packaging rejects
native components requiring a newer OS than 15.0. This binary audit does not
replace running the finished app on a real macOS 15 device.

`convert_klein.py SOURCE DESTINATION` converts a developer-downloaded immutable
distilled 4B snapshot using the pinned MFLUX mappings and native module shapes.
It streams tensors, quantizes supported modules to 4 bits with group size 64,
and preserves the original VAE. All trainable parameters must come from the
source; only the native text encoder's deterministic rotary buffer is derived
from configuration. Shards stay below 1 GiB. The destination is activated by
rename after conversion and real per-file SHA256 calculation. `conversion.json`
records payload sizes, provenance and settings; it is not a release install
manifest and its payload total excludes that record itself. End users do not
run conversion or install development tools.

Native conversion parity tests are opt-in with `PIXELMEND_TEST_MLX=1` and require
actual Metal access. Unit checks do not replace real model inference.

## One-shot protocol

Send one UTF-8 JSON line ending with a newline to stdin, at most 64 KiB.
The process emits JSON lines and exits. Requests support:

- `probe`: checks pinned versions, native imports and a Metal computation.
  An optional `model_dir` tests Marian loading without a prompt, or Klein when
  `model_kind` is `image`. Neither probe establishes profile quality acceptance.
- `translate`: `model_dir` is an absolute local OPUS-MT package directory; `prompt`
  is the synthetic Turkish test instruction.
- `generate`: `model_dir` is an absolute converted Klein directory, `prompt`
  is an English instruction, `seed` is a uint32, and `width`/`height` are one of
  the plan's six size pairs.
- `edit`: the same fields as `generate`, with a crop in `input.png`.

Image operations require a caller-created absolute `session_dir` owned by the
current user, with permission 0700. They exclusively create `output.png`, as a
bare RGB PNG with permission 0600. Editing here tests the model on a crop;
the engine composes only selected pixels, preserves alpha and verifies source
pixels outside the binary selection.
This internal protocol must not be exposed directly to Electron's renderer.

The harness disables Hugging Face online access and telemetry before imports,
never downloads during execution, limits the MLX cache to 1 GiB, and only loads
one model per process. Translation uses Marian's Turkish-to-English encoder-decoder
on CPU, with four beams, no sampling, and at most 511 new tokens. It has no chat
or reasoning mode and receives text directly without instruction prompts. The
source float16 safetensors are loaded into float32; they are not quantized.
SIGALRM provides a cooperative 30-second translation limit and 300-second image
limit. A second bounded stdin line `{"event":"cancel"}` requests interruption.
The engine's `RuntimeOwner` enforces deadlines independently, escalates from
cooperative cancellation to termination after two seconds, kills an unresponsive
owned process group, and waits for exit before publishing a result. The engine
also validates the owner-selected PNG path, private permissions, dimensions,
channels and absence of metadata. Completed denoise steps are emitted only after
MLX evaluates the native step.

The pipe publishes a validated `english` string, rejecting unterminated generation,
empty output, reasoning markup, and an unchanged source echo. Input token limits
are checked without truncation. These checks cannot prove semantic correctness.
The real Turkish quality gate is mandatory before accepting a production profile. These test modes deliberately run as separate processes. The 1000-character
limit applies to the user's source; the prepared image prompt is governed by the
image tokenizer's 512-token limit instead.

For explicit packaged translator checks, set `PIXELMEND_TEST_GENERATIVE_EXECUTABLE`
to the standalone executable and `PIXELMEND_TEST_TRANSLATION_MODEL` to an absolute
local model directory before running the contract tests. Ordinary tests skip this
real-model check. `freeze_support()` dispatches frozen multiprocessing helpers
before they can consume the protocol input or emit spurious job errors.

Third-party progress and stdout/stderr are suppressed to avoid leaking prompts.
Structured errors contain only controlled identifiers. For content-free frozen
import diagnosis, `PIXELMEND_GENERATIVE_DIAGNOSTICS=1` enables a traceback only
for `probe`. Synthetic evaluation evidence, weights, and generated binaries
remain in the Git-ignored `.local-notes` directory.

Image workers load the pinned Klein components in phases: encode and materialize
the prompt, release the text encoder, encode and materialize reference images,
then load the diffusion transformer. Native MFLUX prediction and one-seed
MemorySaver callbacks release the transformer after denoising. The parent engine
then waits for that worker to exit before starting a VAE-only decode worker.
The bounded BF16 latent file is private, validated and removed after the job;
physical memory peaks are reported per phase and combined with max, never sum.
This process boundary also releases native tensors retained beyond Python object
finalization. Both image phases share the original 300-second deadline.
`sequential_klein.py` changes component lifetimes, not weights, dimensions or
the native numerical operations. Pixel equality and physical-footprint budgets
must be measured again when this loading strategy changes. Klein opts out of implicit VAE
tiling because of tile colour offsets. The original VAE and 1 GiB cache limit are
preserved; no system GPU or wired-memory settings are changed. See
`../../tools/generative/README.md` for isolated Mac app packaging and signing.
