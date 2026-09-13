from io import BytesIO

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image


TOKEN = "a" * 64


def _image_payload() -> bytes:
    encoded = BytesIO()
    Image.fromarray(np.array([[[10, 20, 30]]], dtype=np.uint8)).save(
        encoded, format="PNG"
    )
    return encoded.getvalue()


def test_assets_api_requires_a_session_token_and_keeps_paths_private() -> None:
    """Removing auth or leaking a source filename through the API is a security bug."""
    from pixelmend_engine.main import create_app

    client = TestClient(create_app(session_token=TOKEN))

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
