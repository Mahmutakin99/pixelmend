import time

from fastapi.testclient import TestClient

from pixelmend_engine.main import create_app

TOKEN = 'a' * 64
HEADERS = {'X-PixelMend-Token': TOKEN}


def test_diagnostics_are_absent_in_normal_application(monkeypatch, tmp_path):
    monkeypatch.setenv('PIXELMEND_MODELS_DIR', str(tmp_path / 'models'))
    with TestClient(create_app(session_token=TOKEN), base_url='http://127.0.0.1') as client:
        assert client.post('/diagnostics/fixture', headers=HEADERS).status_code == 404


def test_real_fixture_job_checks_alpha_mask_and_explicit_cpu(monkeypatch, tmp_path):
    monkeypatch.setenv('PIXELMEND_MODELS_DIR', str(tmp_path / 'models'))
    with TestClient(create_app(session_token=TOKEN, diagnostics=True), base_url='http://127.0.0.1') as client:
        assert client.post('/diagnostics/fixture').status_code == 401
        fixture = client.post('/diagnostics/fixture', headers=HEADERS).json()
        for algorithm in ['opencv_telea', 'lanczos']:
            response = client.post('/diagnostics/jobs', headers=HEADERS, json={
                'asset_id': fixture['asset_id'], 'algorithm': algorithm, 'scale': 2,
                'provider': 'automatic',
            })
            assert response.status_code == 200, response.text
            job_id = response.json()['job_id']
            for _ in range(100):
                job = client.get(f'/jobs/{job_id}', headers=HEADERS).json()
                if job['status'] in {'failed', 'completed'}:
                    break
                time.sleep(.02)
            assert job['status'] == 'completed'
            checked = client.get(f'/diagnostics/jobs/{job_id}/check', headers=HEADERS)
            assert checked.status_code == 200, checked.text
            assert checked.json()['alpha_preserved'] is True
            assert checked.json()['dimensions_correct'] is True
            if algorithm == 'opencv_telea':
                assert checked.json()['unmasked_pixels_preserved'] is True
        runtime = client.get('/diagnostics/runtime', headers=HEADERS).json()
        assert runtime['process_tree_rss_bytes'] > 0
        assert 'hostname' not in runtime
        invalid = client.post('/diagnostics/jobs', headers=HEADERS, json={
            'asset_id': fixture['asset_id'], 'algorithm': 'lanczos', 'scale': 9000,
        })
        assert invalid.status_code == 422
        large = client.post('/diagnostics/fixture?fixture_id=rocket&width=1600', headers=HEADERS)
        assert large.status_code == 200, large.text
        assert (large.json()['width'], large.json()['height']) == (1600, 900)
        assert client.post('/diagnostics/fixture?fixture_id=rocket&width=9999', headers=HEADERS).status_code == 422
