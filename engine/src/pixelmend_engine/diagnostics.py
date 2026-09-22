"""Opt-in acceptance endpoints, absent from the normal application.

All work goes through the production queue and its model leases/resource checks.
Fixtures are generated here; no personal path is accepted or returned.
"""
from dataclasses import asdict
from io import BytesIO
import hashlib
import json
from pathlib import Path
from importlib.metadata import version
import platform
from typing import Literal

import numpy as np
import psutil
from PIL import Image
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .model_manager import ModelManagerError
from .policy import ResourceLimitError


class DiagnosticJob(BaseModel):
    asset_id: str
    algorithm: Literal['opencv_telea', 'lanczos', 'lama', 'realesrgan_x4plus', 'realesrgan_general_x4v3']
    scale: Literal[1, 2, 4] = 1
    provider: Literal['automatic', 'CPUExecutionProvider'] = 'automatic'
    cancel_immediately: bool = False


def diagnostic_router(queue, assets, auth):
    router = APIRouter(prefix='/diagnostics', dependencies=[Depends(auth)])
    fixtures = set()
    owned_jobs = set()
    data_dir = Path(__file__).parent / 'diagnostic_fixtures'
    photographs = json.loads((data_dir / 'manifest.json').read_text())

    @router.get('/photographs')
    def list_photographs():
        return photographs

    @router.get('/runtime')
    def runtime():
        process = psutil.Process()
        rss = process.memory_info().rss
        complete = True
        try:
            children = process.children(recursive=True)
        except (psutil.Error, OSError):
            children, complete = [], False
        for child in children:
            try:
                rss += child.memory_info().rss
            except (psutil.Error, OSError):
                complete = False
        return {'os': platform.system(), 'os_version': platform.release(),
                'process_architecture': platform.machine(),
                'python_version': platform.python_version(),
                'onnxruntime_version': version('onnxruntime'),
                'process_tree_rss_bytes': rss,
                'process_tree_complete': complete,
                'architecture_note': 'Process architecture; physical architecture/emulation not verified'}

    @router.post('/fixture')
    def fixture(fixture_id: str = Query('synthetic'), width: int = 0):
        if width not in {0, 1600, 2400}:
            raise HTTPException(422, 'Unknown fixture dimensions')
        if len(fixtures) >= 32:
            raise HTTPException(409, 'Diagnostic fixture limit reached')
        if fixture_id != 'synthetic':
            row = next((item for item in photographs if item['id'] == fixture_id), None)
            if row is None or (width and fixture_id != 'rocket'):
                raise HTTPException(422, 'Unknown photograph or size')
            filename = 'original-rocket.jpg' if width else fixture_id + '.png'
            raw = (data_dir / filename).read_bytes()
            digest = row['original_sha256'] if width else row['sha256']
            if hashlib.sha256(raw).hexdigest() != digest:
                raise HTTPException(422, 'Photograph checksum mismatch')
            if width:
                from PIL import ImageOps
                image = ImageOps.fit(Image.open(BytesIO(raw)).convert('RGB'), (width, width * 9 // 16), method=Image.Resampling.LANCZOS)
                encoded = BytesIO()
                image.save(encoded, format='PNG')
                raw = encoded.getvalue()
            imported = assets.import_image(BytesIO(raw))
            fixtures.add(imported.asset_id)
            return {**asdict(imported), 'fixture_version': 1, 'source': row,
                    'input_sha256': hashlib.sha256(raw).hexdigest(),
                    'description': 'Licensed photograph; center 16:9 crop from original' if width else row['preparation']}
        y, x = np.indices((64, 96))
        rgb = np.stack(((x * 3) % 256, (y * 4) % 256, ((x + y) * 2) % 256), axis=-1).astype(np.uint8)
        rgb[24:40, 40:56] = (20, 25, 30)
        alpha = np.where(x < 12, 128, 255).astype(np.uint8)
        image = Image.fromarray(rgb)
        image.putalpha(Image.fromarray(alpha))
        encoded = BytesIO()
        image.save(encoded, format='PNG')
        encoded.seek(0)
        imported = assets.import_image(encoded)
        fixtures.add(imported.asset_id)
        return {**asdict(imported), 'fixture_version': 1,
                'description': 'Synthetic gradient, texture, selected rectangle and alpha; not a photograph quality benchmark'}

    @router.post('/jobs')
    async def submit(payload: DiagnosticJob):
        if payload.asset_id not in fixtures:
            raise HTTPException(422, 'Only diagnostic fixtures are accepted')
        source = assets.get_image(payload.asset_id)
        remove = payload.algorithm in {'opencv_telea', 'lama'}
        mask = None
        if remove:
            mask = np.zeros(source.rgb.shape[:2], dtype=np.uint8)
            mask[22:42, 38:58] = 255
        try:
            job = queue.submit(payload.asset_id, [payload.algorithm], mask,
                               1 if remove else 2,
                               None if remove else source.width * payload.scale,
                               None if remove else source.height * payload.scale)
            # Queue submission and override run on the event loop, before its consumer
            # can start. Never change the persisted user profile for a CPU test.
            if payload.provider == 'CPUExecutionProvider' and job.model_revision:
                job.provider = payload.provider
            owned_jobs.add(job.job_id)
            if payload.cancel_immediately:
                queue.cancel(job.job_id)
            return {'job_id': job.job_id}
        except ModelManagerError as error:
            raise HTTPException(error.status_code, {'code': error.code, 'message': str(error)}) from error
        except (ValueError, ResourceLimitError) as error:
            raise HTTPException(422, str(error)) from error

    @router.get('/jobs/{job_id}/check')
    def check(job_id: str):
        if job_id not in owned_jobs:
            raise HTTPException(404, 'Unknown diagnostic job')
        job = queue.get(job_id)
        if job.status != 'completed' or len(job.results) != 1:
            raise HTTPException(409, 'Job did not complete')
        source = assets.get_image(job.asset_id)
        result = next(iter(job.results.values()))
        expected_size = job.target_size or (source.width, source.height)
        expected_alpha = None if source.alpha is None else np.asarray(Image.fromarray(source.alpha).resize(expected_size, Image.Resampling.LANCZOS))
        dimensions = (result.width, result.height) == expected_size
        alpha = bool(np.array_equal(result.alpha, expected_alpha))
        outside = None
        if job.algorithms[0] in {'opencv_telea', 'lama'}:
            # The queue releases its mask after native completion; reconstruct the
            # fixed fixture selection rather than depending on retained job memory.
            mask = np.zeros(source.rgb.shape[:2], dtype=bool)
            mask[22:42, 38:58] = True
            outside = bool(np.array_equal(result.rgb[~mask], source.rgb[~mask]))
        values = {'dimensions_correct': dimensions, 'alpha_preserved': alpha,
                  'unmasked_pixels_preserved': outside, 'width': result.width, 'height': result.height,
                  'result_details': job.snapshot()['result_details'],
                  'provider_evidence': 'execution_evidence contains ORT executed-node provider counts, when available; Core ML does not imply GPU-only execution'}
        if not dimensions or not alpha or outside is False:
            raise HTTPException(422, values)
        return values

    return router
