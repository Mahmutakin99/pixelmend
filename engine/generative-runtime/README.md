# PixelMend generative runtime feasibility harness

This separate development project tests the proposed Apple Silicon runtime.
It is not integrated into PixelMend, and no hardware profile has been accepted.
The existing ONNX engine has no dependency on this project.

Python 3.12, MFLUX 0.21.0, MLX 0.32.2 and MLX-LM 0.32.0 are pinned in
`pyproject.toml`; `uv.lock` records the complete dependency graph and hashes.
PyInstaller is a development dependency. Torch is a transitive MFLUX dependency.
`sources.json` records immutable official model revisions and Apache-2.0 licenses.
It is a provenance record, not an installable model manifest: package hashes,
download sizes and accepted profiles must come from validated conversion outputs.

## Development verification

From the repository root:

```sh
uv sync --project engine/generative-runtime --frozen
engine/generative-runtime/.venv/bin/python -m unittest discover -s engine/generative-runtime/tests
```

From this directory, with the same environment:

```sh
.venv/bin/python -m PyInstaller runtime.spec
```

PyInstaller produces a directory containing its own Python and native components.
Keep the entire directory together. Building successfully is not proof of native
imports, model inference, signing, notarization or macOS 15 compatibility. Native
wheel deployment targets must be checked before distribution on older systems.

## One-shot protocol

Send one UTF-8 JSON line ending with a newline to stdin, at most 64 KiB.
The process emits JSON lines and exits. Requests support:

- `probe`: checks pinned versions, native imports and a Metal computation.
  An optional `model_dir` also tests Qwen loading without a prompt.
- `translate`: `model_dir` is an absolute local Qwen package directory; `prompt`
  is the synthetic Turkish test instruction.
- `generate`: `model_dir` is an absolute converted Klein directory, `prompt`
  is an English instruction, `seed` is a uint32, and `width`/`height` are one of
  the plan's six size pairs.
- `edit`: the same fields as `generate`, with a crop in `input.png`.

Image operations require a caller-created absolute `session_dir` owned by the
current user, with permission 0700. They exclusively create `output.png`, as a
bare RGB PNG with permission 0600. Editing here tests the model on a crop;
selection composition and alpha preservation belong to the later engine task.
This internal protocol must not be exposed directly to Electron's renderer.

The harness disables Hugging Face online access and telemetry before imports,
never downloads during execution, limits the MLX cache to 1 GiB, and only loads
one model per process. Translation uses thinking disabled, greedy sampling and
at most 512 new tokens. SIGALRM provides a cooperative 30-second translation
limit and 300-second image limit. A supervising process must enforce hard
termination of native calls; that supervisor is a later implementation task.

Translation output must be a single JSON object with only an `english` string.
Schema validation cannot prove that it is English or preserves meaning. The
real Turkish quality gate is mandatory before connecting translation to image
generation. These test modes deliberately run as separate processes.

Third-party progress and stdout/stderr are suppressed to avoid leaking prompts.
Structured errors contain only controlled identifiers. For content-free frozen
import diagnosis, `PIXELMEND_GENERATIVE_DIAGNOSTICS=1` enables a traceback only
for `probe`. Synthetic evaluation evidence, weights, and generated binaries
remain in the Git-ignored `.local-notes` directory.
