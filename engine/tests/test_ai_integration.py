"""Exercise public policy and model-unavailable boundaries without model downloads."""

from fastapi.testclient import TestClient

from pixelmend_engine.main import create_app


TOKEN = 'f' * 64


def test_capabilities_expose_one_output_policy_and_ai_model_has_a_published_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv('PIXELMEND_MODELS_DIR', str(tmp_path / 'models'))
    monkeypatch.setenv('PIXELMEND_SESSIONS_DIR', str(tmp_path / 'sessions'))
    with TestClient(create_app(session_token=TOKEN), base_url='http://127.0.0.1') as client:
        headers = {'X-PixelMend-Token': TOKEN}
        capabilities = client.get('/capabilities', headers=headers)
        assert capabilities.status_code == 200
        assert capabilities.json()['policy']['max_output_pixels'] == 200_000_000
        models = client.get('/models', headers=headers)
        assert models.status_code == 200
        ai = next(item for item in models.json()['models'] if item['id'] == 'realesrgan-x4plus')
        assert ai['state'] in {'absent', 'ready'}
        assert ai['source'] == 'published' and ai['verified_manifest']
        assert ai['revision'] and ai['sha256']


def test_asset_export_is_authenticated_and_returns_full_normalized_png(tmp_path, monkeypatch):
    monkeypatch.setenv('PIXELMEND_MODELS_DIR', str(tmp_path / 'models'))
    monkeypatch.setenv('PIXELMEND_SESSIONS_DIR', str(tmp_path / 'sessions'))
    from io import BytesIO
    from PIL import Image

    image = BytesIO()
    Image.new('RGBA', (12, 7), (10, 20, 30, 128)).save(image, format='PNG')
    with TestClient(create_app(session_token=TOKEN), base_url='http://127.0.0.1') as client:
        headers = {'X-PixelMend-Token': TOKEN}
        created = client.post('/assets', headers=headers, files={'image': ('x.png', image.getvalue())})
        asset_id = created.json()['asset_id']
        assert client.get(f'/assets/{asset_id}/export?format=PNG').status_code == 401
        response = client.get(f'/assets/{asset_id}/export?format=PNG', headers=headers)
        assert response.status_code == 200
        with Image.open(BytesIO(response.content)) as decoded:
            assert decoded.size == (12, 7)
            assert decoded.mode == 'RGBA'
