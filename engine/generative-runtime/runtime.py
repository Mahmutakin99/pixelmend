"""One-shot, offline headless runtime. This is the feasibility harness, not IPC.

Read one bounded JSON line from stdin. Load one model and exit after one request.
No prompt is passed on the command line or included in diagnostic errors.
"""

import contextlib
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import sys
import time

VERSIONS = {'mflux': '0.21.0', 'mlx': '0.32.2', 'mlx-lm': '0.32.0'}
MAX_LINE = 65536
PROTOCOL_STDOUT = sys.stdout
DIMENSIONS = {(512, 512), (640, 480), (480, 640),
              (768, 768), (1024, 768), (768, 1024)}


def validate_prompt(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 1000:
        raise ValueError('invalid_prompt')
    return value.strip()


def validate_prepared_prompt(value):
    # Input is already bounded by the pipe. Model token limits are checked separately.
    if not isinstance(value, str) or not value.strip():
        raise ValueError('invalid_prompt')
    return value.strip()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_json_key')
        result[key] = value
    return result


def parse_translation(value):
    try:
        result = json.loads(value, object_pairs_hook=_unique_object)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError('invalid_translation') from error
    if not isinstance(result, dict) or set(result) != {'english'}:
        raise ValueError('invalid_translation')
    english = validate_prepared_prompt(result['english'])
    if '<' in english or '>' in english or '\n' in english:
        raise ValueError('invalid_translation')
    return english


def validate_translation_token_count(count, limit):
    if count > limit:
        raise ValueError('prompt_token_limit')


def validate_translation_completion(token_ids, eos_token_id, decoded, source):
    if not token_ids or token_ids[-1] != eos_token_id:
        raise ValueError('invalid_translation')
    english = parse_translation(json.dumps({'english': decoded}))
    if english.casefold() == source.strip().casefold():
        raise ValueError('invalid_translation')
    return english


def load_translator(model_dir):
    import torch
    from transformers import MarianMTModel, MarianTokenizer

    # This small encoder-decoder uses CPU deliberately; image generation stays on MLX.
    torch.set_num_threads(4)
    path = local_model(model_dir)
    tokenizer = MarianTokenizer.from_pretrained(path, local_files_only=True)
    model = MarianMTModel.from_pretrained(path, local_files_only=True,
                                         use_safetensors=True, dtype=torch.float32).eval()
    return model, tokenizer


def read_request(stream):
    line = stream.readline(MAX_LINE + 1)
    if len(line) > MAX_LINE or not line.endswith(b'\n'):
        raise ValueError('invalid_request')
    try:
        value = json.loads(line, object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('invalid_request') from error
    if not isinstance(value, dict):
        raise ValueError('invalid_request')
    return value


def validate_image_options(request):
    seed, width, height = (request.get(key) for key in ('seed', 'width', 'height'))
    if (type(seed) is not int or not 0 <= seed < 2**32
            or type(width) is not int or type(height) is not int
            or (width, height) not in DIMENSIONS):
        raise ValueError('invalid_image_options')
    return seed, width, height


def validate_image_prompt(language_tokenizer, prompt):
    # Mirror MFLUX LanguageTokenizer formatting and special tokens, without truncation.
    tokenizer = language_tokenizer.tokenizer
    formatted = tokenizer.apply_chat_template(
        [{'role': 'user', 'content': prompt}], tokenize=False,
        add_generation_prompt=True, **language_tokenizer.chat_template_kwargs)
    tokens = tokenizer(formatted, truncation=False,
                       add_special_tokens=language_tokenizer.add_special_tokens)
    if len(tokens['input_ids']) > language_tokenizer.max_length:
        raise ValueError('prompt_token_limit')


def emit(value):
    PROTOCOL_STDOUT.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n')
    PROTOCOL_STDOUT.flush()


def local_model(value):
    if not isinstance(value, str):
        raise ValueError('model_not_installed')
    path = Path(value)
    if not path.is_absolute() or not path.is_dir() or path.is_symlink():
        raise ValueError('model_not_installed')
    if not any(path.rglob('*.safetensors')):
        raise ValueError('model_not_installed')
    return str(path.resolve())


def check_runtime():
    import platform
    if (sys.platform != 'darwin' or platform.machine() != 'arm64'
            or int(platform.mac_ver()[0].split('.')[0]) < 15):
        raise ValueError('unsupported_platform')
    for name, expected in VERSIONS.items():
        if importlib.metadata.version(name) != expected:
            raise ValueError('unsupported_runtime')
    import mlx.core as mx
    if not mx.metal.is_available():
        raise ValueError('unsupported_platform')
    mx.set_cache_limit(1024**3)
    return mx


@contextlib.contextmanager
def deadline(seconds):
    def expired(_signum, _frame):
        raise TimeoutError('timeout')
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def translate(request):
    prompt = validate_prompt(request.get('prompt'))
    emit({'event': 'stage', 'stage': 'translating'})
    with deadline(30):
        import torch
        model, tokenizer = load_translator(request.get('model_dir'))
        tokens = tokenizer(prompt, return_tensors='pt', truncation=False)
        validate_translation_token_count(tokens['input_ids'].shape[-1],
                                         model.config.max_position_embeddings)
        with torch.inference_mode():
            result = model.generate(**tokens, num_beams=4, do_sample=False,
                                    max_new_tokens=min(512, model.config.max_position_embeddings - 1),
                                    # Do not force an EOS at the length cap: that hides truncation.
                                    forced_eos_token_id=None)
        english = validate_translation_completion(result[0].tolist(), model.config.eos_token_id,
                                                   tokenizer.decode(result[0], skip_special_tokens=True),
                                                   prompt)
        return {'english': english, 'translation_runtime': 'torch-cpu'}


def generate(request):
    from mflux.models.flux2 import Flux2Klein
    from mflux.models.flux2.variants.edit.flux2_klein_edit import Flux2KleinEdit
    from mflux.models.common.config.model_config import ModelConfig

    prompt = validate_prepared_prompt(request.get('prompt'))
    seed, width, height = validate_image_options(request)
    session = Path(request.get('session_dir', ''))
    if (not session.is_absolute() or session.is_symlink() or not session.is_dir()
            or session.stat().st_uid != os.getuid() or session.stat().st_mode & 0o077):
        raise ValueError('invalid_session')
    output = session / 'output.png'
    if output.exists() or output.is_symlink():
        raise ValueError('invalid_output')
    model_path = local_model(request.get('model_dir'))
    edit = request['operation'] == 'edit'
    kwargs = {}
    if edit:
        source = session / 'input.png'
        if not source.is_file() or source.is_symlink():
            raise ValueError('invalid_input')
        kwargs['image_paths'] = [str(source)]
    emit({'event': 'stage', 'stage': 'loading_image_model'})
    cls = Flux2KleinEdit if edit else Flux2Klein
    model = cls(model_path=model_path, model_config=ModelConfig.flux2_klein_4b())
    # MFLUX truncates by default; reject rather than silently losing conditions.
    validate_image_prompt(model.tokenizers['qwen3'], prompt)
    emit({'event': 'stage', 'stage': 'generating'})
    image = model.generate_image(seed=seed, prompt=prompt, width=width, height=height,
                                 num_inference_steps=4, guidance=1.0, **kwargs).image
    if image.size != (width, height):
        raise ValueError('invalid_output')
    # Save bare opaque pixels: MFLUX's save method also writes prompt metadata.
    with output.open('xb') as stream:
        os.chmod(output, 0o600)
        image.convert('RGB').save(stream, format='PNG')
    return {'seed': seed, 'width': width, 'height': height}


def main():
    os.umask(0o077)
    # Set these before importing any model or Hugging Face code.
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                      HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1',
                      TOKENIZERS_PARALLELISM='false')
    started = time.monotonic()
    operation = None
    try:
        request = read_request(sys.stdin.buffer)
        operation = request.get('operation')
        if operation not in {'probe', 'translate', 'generate', 'edit'}:
            raise ValueError('invalid_operation')
        mx = check_runtime()
        # Third-party libraries may print prompts or progress; keep them off pipes/logs.
        with open(os.devnull, 'w') as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            if operation == 'probe':
                from mflux.models.flux2 import Flux2Klein
                values = mx.array([1, 2, 3]) * 2
                mx.eval(values)
                result = {'versions': VERSIONS, 'metal': True, 'gpu_result': values.tolist()}
                if 'model_dir' in request:
                    # Optional content-free translator load check for packaging diagnostics.
                    model, tokenizer = load_translator(request['model_dir'])
                    result['translation_model_loaded'] = True
            else:
                with deadline(300):
                    result = translate(request) if operation == 'translate' else generate(request)
        result.update(event='result', elapsed_seconds=time.monotonic() - started,
                      mlx_peak_bytes=mx.get_peak_memory())
        emit(result)
        return 0
    except (Exception, KeyboardInterrupt) as error:
        # Probe has no user content. Opt-in developer traces diagnose frozen imports.
        if operation == 'probe' and os.environ.get('PIXELMEND_GENERATIVE_DIAGNOSTICS') == '1':
            import traceback
            traceback.print_exc(file=sys.stderr)
        code = str(error) if isinstance(error, (ValueError, TimeoutError)) else 'runtime_failed'
        # Only identifiers we define are eligible to leave the runtime.
        allowed = {'invalid_prompt', 'invalid_translation', 'invalid_request', 'duplicate_json_key',
                   'invalid_image_options', 'model_not_installed', 'unsupported_platform',
                   'unsupported_runtime', 'invalid_session', 'invalid_output', 'invalid_input',
                   'prompt_token_limit', 'invalid_operation', 'timeout'}
        emit({'event': 'error', 'code': code if code in allowed else 'runtime_failed'})
        return 1


if __name__ == '__main__':
    # PyInstaller helper processes must dispatch to multiprocessing, not read our pipe.
    from multiprocessing import freeze_support
    freeze_support()
    raise SystemExit(main())
