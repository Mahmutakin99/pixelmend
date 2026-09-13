"""Launch the sidecar on an OS-selected IPv4 loopback port."""

import json
import os
import socket

import uvicorn

from pixelmend_engine.main import create_app


def main():
    """Keep the session secret in environment and report only the chosen port."""
    token = os.environ.pop('PIXELMEND_SESSION_TOKEN', '')
    app = create_app(session_token=token)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen(128)
        listener.setblocking(False)
        print(json.dumps({'port': listener.getsockname()[1]}), flush=True)
        server = uvicorn.Server(uvicorn.Config(app, log_level='warning', access_log=False))
        server.run(sockets=[listener])


if __name__ == '__main__':
    main()
