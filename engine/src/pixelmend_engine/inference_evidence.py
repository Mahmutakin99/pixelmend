"""One bounded ORT trace per session; export provider counts, never trace paths."""
from collections import Counter
import json
from pathlib import Path
from tempfile import TemporaryDirectory


def summarize_profile(path):
    try:
        file = Path(path)
        if file.stat().st_size > 32 * 1024**2:
            raise ValueError('profile too large')
        events = json.loads(file.read_text())
        counts = Counter(event.get('args', {}).get('provider') for event in events
                         if event.get('cat') == 'Node' and event.get('ph') == 'X'
                         and isinstance(event.get('args', {}).get('provider'), str))
        return {'status': 'observed' if counts else 'unavailable', 'providers': dict(counts),
                'scope': 'First native call in this session; Core ML can use CPU/GPU/Neural Engine'}
    except (OSError, ValueError, TypeError, AttributeError):
        return {'status': 'unavailable', 'providers': {}}


class InferenceEvidence:
    def __init__(self, options, providers, *, enabled=True):
        self.directory = TemporaryDirectory(prefix='pixelmend-ort-') if enabled else None
        self.value = {'status':'unavailable', 'providers':{}}
        if self.directory:
            options.enable_profiling = True
            options.profile_file_prefix = str(Path(self.directory.name) / 'trace')
        names = [p[0] if isinstance(p, tuple) else p for p in providers or []]
        if 'DmlExecutionProvider' in names:
            import onnxruntime as ort
            options.enable_mem_pattern = False
            options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

    def finish(self, session):
        if self.directory:
            try:
                self.value = summarize_profile(session.end_profiling())
            finally:
                self.directory.cleanup()
                self.directory = None
        return self.value
