"""Single-worker inference queue; state transitions belong to its asyncio loop."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from time import monotonic
from uuid import uuid4

import numpy as np
from PIL import Image
from functools import lru_cache

from .assets import AssetStore
from .imageio import ImageAsset
from .models.opencv_inpaint import OpenCVInpaint
from .model_store import ModelFileMissingError, ModelStoreError

TERMINAL = frozenset({'completed', 'failed', 'cancelled'})


@lru_cache(maxsize=1)
def lama_adapter():
    from .models.lama_onnx import LamaInpaint
    from .paths import get_models_dir
    return LamaInpaint(get_models_dir())


def process(image, mask, algorithm, scale, target_size=None):
    """Execute native inference in the queue's dedicated worker."""
    if algorithm == 'lanczos':
        size = target_size or (image.width * scale, image.height * scale)
        rgb = np.asarray(Image.fromarray(image.rgb).resize(size, Image.Resampling.LANCZOS)).copy()
        alpha = None if image.alpha is None else np.asarray(
            Image.fromarray(image.alpha).resize(size, Image.Resampling.LANCZOS)).copy()
        return replace(image, rgb=rgb, alpha=alpha)
    adapter = lama_adapter() if algorithm == 'lama' else OpenCVInpaint(
        {'opencv_telea': 'telea', 'opencv_ns': 'ns'}[algorithm])
    return replace(image, rgb=adapter.run(image.rgb, mask))


@dataclass
class Job:
    job_id: str
    asset_id: str
    algorithms: list[str]
    mask: np.ndarray | None
    scale: int
    target_size: tuple[int, int] | None = None
    status: str = 'queued'
    results: dict[str, ImageAsset] = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    result_bytes: int = 0
    error: dict | None = None

    def emit(self, event, **data):
        """Assign monotonic event ids for deterministic SSE replay."""
        self.events.append({'id': len(self.events) + 1, 'event': event, 'data': data})

    def snapshot(self):
        return {'job_id': self.job_id, 'status': self.status,
                'result_ids': list(self.results), 'algorithms': self.algorithms,
                'error': self.error,
                'result_details': [{'result_id': key, 'width': image.width, 'height': image.height}
                                   for key, image in self.results.items()]}


class JobQueue:
    """Serialize native work and keep cancellation independent of thread preemption."""

    def __init__(self, assets: AssetStore, *, processor=process, max_jobs=32,
                 result_budget=512 * 1024 * 1024):
        self.assets = assets
        self.processor = processor
        self.max_jobs = max_jobs
        self.result_budget = result_budget
        self.jobs = {}
        self.pending = asyncio.Queue()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='inference')
        self.accepting = False

    async def __aenter__(self):
        self.accepting = True
        self.worker = asyncio.create_task(self._consume())
        return self

    async def __aexit__(self, *args):
        self.accepting = False
        for job in self.jobs.values():
            self.cancel(job.job_id)
        await self.pending.put(None)
        await self.worker
        self.executor.shutdown(wait=True)
        self.jobs.clear()

    def submit(self, asset_id, algorithms, mask=None, scale=1, target_width=None, target_height=None):
        """Validate and pin the source before exposing a queued job."""
        if not self.accepting or len(self.jobs) >= self.max_jobs:
            raise ValueError('job capacity unavailable')
        if not algorithms or len(algorithms) > 8 or len(set(algorithms)) != len(algorithms):
            raise ValueError('select unique algorithms')
        if any(a not in {'opencv_telea', 'opencv_ns', 'lama', 'lanczos'} for a in algorithms):
            raise ValueError('algorithm unavailable')
        image = self.assets.get_image(asset_id)
        target_size = None
        if 'lanczos' in algorithms:
            if algorithms != ['lanczos']:
                raise ValueError('upscale requires a separate job')
            has_target = target_width is not None or target_height is not None
            if has_target:
                if not (isinstance(target_width, int) and isinstance(target_height, int) and target_width > 0 and target_height > 0):
                    raise ValueError('target width and height must be positive integers')
                target_size = (target_width, target_height)
            elif scale not in (2, 4):
                raise ValueError('upscale requires scale 2 or 4, or a target size')
            output_pixels = target_width * target_height if target_size else image.width * image.height * scale * scale
            if output_pixels > 50_000_000:
                raise ValueError('output pixel limit exceeded')
        else:
            if scale != 1:
                raise ValueError('inpaint scale must be 1')
            if mask is None or mask.shape != image.rgb.shape[:2] or mask.dtype != np.uint8:
                raise ValueError('mask dimensions must match the source')
            if not np.all((mask == 0) | (mask == 255)) or not np.any(mask):
                raise ValueError('mask must contain a binary selection')
        self.assets.acquire_for_job(asset_id)
        job = Job(uuid4().hex, asset_id, list(algorithms), None if mask is None else mask.copy(), scale, target_size)
        self.jobs[job.job_id] = job
        job.emit('queued', **job.snapshot())
        self.pending.put_nowait(job)
        return job

    def get(self, job_id):
        return self.jobs[job_id]

    def cancel(self, job_id):
        """Request cancellation; retain native-work references until it returns."""
        job = self.get(job_id)
        if job.status not in TERMINAL:
            job.status = 'cancelling'
        return job

    def delete(self, job_id):
        job = self.get(job_id)
        if job.status not in TERMINAL:
            raise ValueError('job is still active')
        del self.jobs[job_id]

    def events_after(self, job_id, cursor):
        return [event for event in self.get(job_id).events if event['id'] > cursor]

    async def join(self):
        await self.pending.join()

    async def _consume(self):
        """Await the whole native call before publishing results or releasing assets."""
        while True:
            job = await self.pending.get()
            if job is None:
                self.pending.task_done()
                return
            try:
                if job.status != 'cancelling':
                    job.status = 'running'
                    job.emit('running', job_id=job.job_id)
                    image = self.assets.get_image(job.asset_id)
                    for algorithm in job.algorithms:
                        started = monotonic()
                        args = (image, job.mask, algorithm, job.scale, job.target_size) if self.processor is process else (image, job.mask, algorithm, job.scale)
                        result = await asyncio.get_running_loop().run_in_executor(self.executor, self.processor, *args)
                        if job.status == 'cancelling':
                            break
                        size = result.rgb.nbytes + (result.alpha.nbytes if result.alpha is not None else 0)
                        if sum(j.result_bytes for j in self.jobs.values()) + size > self.result_budget:
                            raise MemoryError('result budget exceeded')
                        result_id = uuid4().hex
                        job.results[result_id] = result
                        job.result_bytes += size
                        job.emit('result', result_id=result_id, algorithm=algorithm,
                                 seconds=monotonic() - started, width=result.width, height=result.height)
                job.status = 'cancelled' if job.status == 'cancelling' else 'completed'
            except Exception as error:
                job.status = 'cancelled' if job.status == 'cancelling' else 'failed'
                if job.status == 'failed':
                    if isinstance(error, ModelFileMissingError):
                        job.error = {'code': 'model_missing', 'message': 'LaMa modeli kurulu değil. Model kurulana kadar Sil veya Lanczos kullanabilirsiniz.'}
                    elif isinstance(error, ModelStoreError):
                        job.error = {'code': 'model_invalid', 'message': 'LaMa modelinin bütünlük doğrulaması başarısız. Model yeniden kurulmalı.'}
                    elif isinstance(error, MemoryError):
                        job.error = {'code': 'memory_limit', 'message': 'İşlem için yeterli bellek yok. Daha küçük bir görsel deneyin.'}
                    else:
                        job.error = {'code': 'inference_failed', 'message': 'Görüntü işleme başarısız oldu. Seçili algoritmayı ve görseli kontrol edip tekrar deneyin.'}
                    job.emit('error', **job.error)
            finally:
                job.mask = None
                self.assets.release_from_job(job.asset_id)
                job.emit(job.status, job_id=job.job_id)
                self.pending.task_done()
