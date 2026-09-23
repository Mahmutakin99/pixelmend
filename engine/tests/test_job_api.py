from io import BytesIO
import json
import time
import pytest
import numpy as np

from fastapi.testclient import TestClient
from PIL import Image
from pixelmend_engine.main import create_app


def test_job_api_accepts_selection_strokes_without_a_renderer_png():
    data = BytesIO()
    Image.new('RGB', (32, 32), 'white').save(data, format='PNG')
    strokes = [{'mode': 'draw', 'points': [{'x': 16, 'y': 16}], 'color': '#ff3b6b',
                'opacity': 1, 'size': 8, 'hardness': 1}]
    with TestClient(create_app(session_token='a' * 64), base_url='http://127.0.0.1',
                    headers={'X-PixelMend-Token': 'a' * 64}) as client:
        asset = client.post('/assets', files={'image': ('source.png', data.getvalue())}).json()
        response = client.post('/jobs', data={'asset_id': asset['asset_id'],
            'algorithms': '["opencv_telea"]', 'selection_strokes': json.dumps(strokes)})
        assert response.status_code == 201, response.text


def test_rendered_asset_composites_paint_strokes_server_side():
    data = BytesIO()
    Image.new('RGB', (16, 16), 'black').save(data, format='PNG')
    strokes = [{'mode': 'draw', 'points': [{'x': 8, 'y': 8}], 'color': '#ff8040',
                'opacity': 1, 'size': 4, 'hardness': 1}]
    with TestClient(create_app(session_token='a' * 64), base_url='http://127.0.0.1',
                    headers={'X-PixelMend-Token': 'a' * 64}) as client:
        asset = client.post('/assets', files={'image': ('source.png', data.getvalue())}).json()
        response = client.post(f"/assets/{asset['asset_id']}/rendered", json={'paint_strokes': strokes})
        assert response.status_code == 201, response.text
        rendered = client.get(f"/assets/{response.json()['asset_id']}/export")
        assert Image.open(BytesIO(rendered.content)).convert('RGB').getpixel((8, 8)) == (255, 128, 64)


@pytest.mark.parametrize('color', [(0, 0, 0), (255, 59, 107)])
def test_canvas_rgba_selection_uses_alpha_and_preserves_surround(color):
    """The actual canvas exports RGBA, including black strokes and erased pixels."""
    source = Image.new('RGB', (32, 32), (180, 180, 180))
    source.paste((0, 0, 0), (14, 14, 18, 18))
    original = np.asarray(source).copy()
    data = BytesIO()
    source.save(data, format='PNG')
    overlay = Image.new('RGBA', source.size, (*color, 0))
    overlay.paste((*color, 255), (12, 12, 20, 20))
    mask = BytesIO()
    overlay.save(mask, format='PNG')
    with TestClient(create_app(session_token='a' * 64), base_url='http://127.0.0.1',
                    headers={'X-PixelMend-Token': 'a' * 64}) as client:
        asset = client.post('/assets', files={'image': ('source.png', data.getvalue())}).json()
        response = client.post('/jobs', data={'asset_id': asset['asset_id'],
            'algorithms': '["opencv_telea"]'}, files={'mask': ('canvas.png', mask.getvalue())})
        assert response.status_code == 201, response.text
        job_id = response.json()['job_id']
        for _ in range(100):
            state = client.get(f'/jobs/{job_id}').json()
            if state['status'] in ('completed', 'failed'):
                break
            time.sleep(.01)
        assert state['status'] == 'completed', state
        output = client.get(f"/jobs/{job_id}/results/{state['result_ids'][0]}")
        pixels = np.asarray(Image.open(BytesIO(output.content)))
        selected = np.asarray(overlay)[:, :, 3] >= 128
        np.testing.assert_array_equal(pixels[~selected], original[~selected])
        assert pixels[15, 15].mean() > 100


def test_job_api_processes_mask_streams_results_and_exports():
    data = BytesIO()
    Image.new('RGB', (8, 8), 'white').save(data, format='PNG')
    mask = BytesIO()
    Image.new('L', (8, 8), 255).save(mask, format='PNG')
    with TestClient(create_app(session_token='a' * 64), base_url='http://127.0.0.1',
                    headers={'X-PixelMend-Token': 'a' * 64}) as client:
        asset = client.post('/assets', files={'image': ('a.png', data.getvalue())}).json()
        response = client.post('/jobs', data={'asset_id': asset['asset_id'],
            'algorithms': json.dumps(['opencv_telea'])}, files={'mask': ('m.png', mask.getvalue())})
        assert response.status_code == 201, response.text
        job_id = response.json()['job_id']
        for _ in range(100):
            status = client.get(f'/jobs/{job_id}').json()
            if status['status'] == 'completed':
                break
            time.sleep(.01)
        assert status['status'] == 'completed'
        stream = client.get(f'/jobs/{job_id}/events')
        assert 'event: completed' in stream.text
        result_id = status['result_ids'][0]
        result = client.get(f'/jobs/{job_id}/results/{result_id}?format=TIFF')
        assert result.status_code == 200
        assert Image.open(BytesIO(result.content)).format == 'TIFF'
        continued = client.post(f'/jobs/{job_id}/results/{result_id}/asset')
        assert continued.status_code == 201
        assert continued.json()['asset_id'] != asset['asset_id']
        assert client.delete(f'/jobs/{job_id}').status_code == 204
        assert client.get(f'/jobs/{job_id}').status_code == 404
        upscale = client.post('/jobs', data={'asset_id': asset['asset_id'],
            'algorithms': '["lanczos"]', 'scale': '2'})
        assert upscale.status_code == 201, upscale.text


def test_unready_lama_preserves_model_error_code(tmp_path, monkeypatch):
    monkeypatch.setenv('PIXELMEND_MODELS_DIR', str(tmp_path))
    data = BytesIO(); Image.new('RGB', (16,16)).save(data,format='PNG')
    with TestClient(create_app(session_token='a'*64), base_url='http://127.0.0.1',headers={'X-PixelMend-Token':'a'*64}) as client:
        asset=client.post('/assets',files={'image':('x.png',data.getvalue())}).json()
        response=client.post('/jobs',data={'asset_id':asset['asset_id'],'algorithms':'["lama"]','selection_strokes':json.dumps([{'mode':'draw','points':[{'x':8,'y':8}],'color':'#ff0000','opacity':1,'size':4,'hardness':1}])})
        assert response.status_code == 409
        assert response.json()['detail']['code'] == 'not_ready'


def test_job_api_carries_the_validated_low_resource_mode_to_the_queue():
    data = BytesIO(); Image.new('RGB', (16, 16), 'white').save(data, format='PNG')
    strokes = json.dumps([{'mode': 'draw', 'points': [{'x': 8, 'y': 8}], 'color': '#ff0000',
                          'opacity': 1, 'size': 4, 'hardness': 1}])
    with TestClient(create_app(session_token='a' * 64), base_url='http://127.0.0.1',
                    headers={'X-PixelMend-Token': 'a' * 64}) as client:
        asset = client.post('/assets', files={'image': ('source.png', data.getvalue())}).json()
        response = client.post('/jobs', data={'asset_id': asset['asset_id'],
            'algorithms': '["opencv_telea"]', 'selection_strokes': strokes,
            'resource_mode': 'low-resource'})
        assert response.status_code == 201, response.text
        assert client.get(f"/jobs/{response.json()['job_id']}").json()['resource_mode'] == 'low-resource'
