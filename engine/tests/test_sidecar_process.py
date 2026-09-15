import json
import os
from pathlib import Path
import queue
import secrets
import subprocess
import sys
import threading
import urllib.request


def test_real_loopback_sidecar_startup_health_and_shutdown():
    token = secrets.token_hex(32)
    env = dict(os.environ, PIXELMEND_SESSION_TOKEN=token)
    process = subprocess.Popen([sys.executable, '-m', 'pixelmend_engine'], env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        # select() accepts pipe file descriptors on Unix but not Windows.
        lines = queue.Queue()
        threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True).start()
        try:
            line = lines.get(timeout=15)
        except queue.Empty:
            raise AssertionError('startup timed out') from None
        assert token not in line
        startup = json.loads(line)
        request = urllib.request.Request(f"http://127.0.0.1:{startup['port']}/health",
                                         headers={'X-PixelMend-Token': token})
        import time
        for attempt in range(50):
            try:
                with urllib.request.urlopen(request, timeout=2) as response:
                    assert json.load(response) == {'status': 'ok'}
                break
            except OSError:
                if attempt == 49:
                    raise
                time.sleep(.05)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise
    # Uvicorn restores and re-raises SIGTERM after its graceful lifespan shutdown.
    assert process.returncode in (0, -15)
