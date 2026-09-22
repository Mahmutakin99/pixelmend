from io import BytesIO

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image


TOKEN = "a" * 64


def test_all_routes_reject_untrusted_origin_and_host():
    from pixelmend_engine.main import create_app

    with TestClient(create_app(session_token=TOKEN), base_url='http://127.0.0.1') as client:
        assert client.get('/openapi.json').status_code == 404
        headers = {'X-PixelMend-Token': TOKEN, 'Origin': 'https://example.com'}
        assert client.get('/health', headers=headers).status_code == 403
        headers = {'X-PixelMend-Token': TOKEN, 'Host': 'example.com'}
        assert client.get('/health', headers=headers).status_code == 403


def test_malformed_token_is_unauthorized():
    from pixelmend_engine.main import create_app

    with TestClient(create_app(session_token=TOKEN), base_url='http://127.0.0.1') as client:
        response = client.get('/health', headers={'X-PixelMend-Token': b'\xff'})
        assert response.status_code == 401


def _image_payload() -> bytes:
    encoded = BytesIO()
    Image.fromarray(np.array([[[10, 20, 30]]], dtype=np.uint8)).save(
        encoded, format="PNG"
    )
    return encoded.getvalue()


def test_assets_api_requires_a_session_token_and_keeps_paths_private() -> None:
    """Removing auth or leaking a source filename through the API is a security bug."""
    from pixelmend_engine.main import create_app

    client = TestClient(create_app(session_token=TOKEN), base_url='http://127.0.0.1')

    denied = client.post(
        "/assets", files={"image": ("private-photo.png", _image_payload(), "image/png")}
    )
    assert denied.status_code == 401

    imported = client.post(
        "/assets",
        headers={"X-PixelMend-Token": TOKEN},
        files={"image": ("private-photo.png", _image_payload(), "image/png")},
    )
    assert imported.status_code == 201
    body = imported.json()
    assert set(body) == {"asset_id", "width", "height", "warnings"}
    assert body["width"] == 1
    assert body["height"] == 1
    assert "private-photo.png" not in imported.text

    preview = client.get(
        f"/assets/{body['asset_id']}/preview", headers={"X-PixelMend-Token": TOKEN}
    )
    assert preview.status_code == 200
    assert preview.headers["content-type"] == "image/png"

    deleted = client.delete(
        f"/assets/{body['asset_id']}", headers={"X-PixelMend-Token": TOKEN}
    )
    assert deleted.status_code == 204


def test_health_and_capabilities_are_token_protected() -> None:
    """A browser that can probe health without a token can target the sidecar."""
    from pixelmend_engine.main import create_app

    client = TestClient(create_app(session_token=TOKEN), base_url='http://127.0.0.1')

    assert client.get("/health").status_code == 401
    health = client.get("/health", headers={"X-PixelMend-Token": TOKEN})
    capabilities = client.get(
        "/capabilities", headers={"X-PixelMend-Token": TOKEN}
    )

    assert health.json() == {"status": "ok"}
    assert capabilities.status_code == 200
    assert "host_ram_total_bytes" in capabilities.json()


def test_shutdown_requires_auth_and_calls_the_server_hook():
    from pixelmend_engine.main import create_app
    app = create_app(session_token=TOKEN)
    stopped = []
    app.state.request_shutdown = lambda: stopped.append(True)
    client = TestClient(app, base_url='http://127.0.0.1')
    assert client.post('/shutdown').status_code == 401
    assert not stopped
    assert client.post('/shutdown', headers={'X-PixelMend-Token': TOKEN}).status_code == 200
    assert stopped == [True]
