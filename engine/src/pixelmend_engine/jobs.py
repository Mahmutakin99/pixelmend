"""Single-worker inference queue; state transitions belong to its asyncio loop."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from threading import Event
from time import monotonic
from uuid import uuid4

import numpy as np
from PIL import Image

from .assets import AssetStore
from .imageio import ImageAsset
from .models.opencv_inpaint import OpenCVInpaint
from .model_store import ModelFileMissingError, ModelStoreError
from .model_manager import ModelManager, ModelManagerError
from .models.realesrgan_onnx import InferenceCancelled, RealESRGANUpscale
from .policy import POLICY, ResourceLimitError, admit_image_job

TERMINAL = frozenset({'completed', 'failed', 'cancelled'})


def process(image, mask, algorithm, scale, target_size=None, *, model_path=None,
            provider=None, cancel_event=None, progress=None):
    """Execute native inference in the queue's dedicated worker."""
    if algorithm == 'lanczos':
        size = target_size or (image.width * scale, image.height * scale)
        rgb = np.asarray(Image.fromarray(image.rgb).resize(size, Image.Resampling.LANCZOS)).copy()
        alpha = None if image.alpha is None else np.asarray(
            Image.fromarray(image.alpha).resize(size, Image.Resampling.LANCZOS)).copy()
        return replace(image, rgb=rgb, alpha=alpha)
    if algorithm == 'realesrgan_x4plus':
        if model_path is None or provider is None:
            raise ModelManagerError('not_ready', 'AI kalite modeli hazır değil.')
        adapter = RealESRGANUpscale(model_path, providers=[provider],
                                    tile_size=POLICY.tile_size,
                                    overlap=POLICY.tile_overlap)
        rgb = adapter.run(image.rgb, target_size=target_size,
                          cancel_event=cancel_event, progress=progress)
        alpha = None if image.alpha is None else np.asarray(
            Image.fromarray(image.alpha).resize(rgb.shape[1::-1], Image.Resampling.LANCZOS)).copy()
        return replace(image, rgb=rgb, alpha=alpha)
    if algorithm == 'lama':
        from .models.lama_onnx import LamaInpaint
        if model_path is None or provider is None:
            raise ModelManagerError('not_ready', 'LaMa model is not ready.')
        adapter = LamaInpaint(model_path=model_path, providers=[provider])
    else:
        adapter = OpenCVInpaint({'opencv_telea': 'telea', 'opencv_ns': 'ns'}[algorithm])
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
    progress: dict | None = None
    model_lease: object | None = None
    model_revision: str | None = None
    provider: str | None = None
    result_metadata: dict = field(default_factory=dict)
    cancel_event: Event = field(default_factory=Event)

    def emit(self, event, **data):
        """Assign monotonic event ids for deterministic SSE replay."""
        self.events.append({'id': len(self.events) + 1, 'event': event, 'data': data})

    def snapshot(self):
        return {'job_id': self.job_id, 'status': self.status,
                'result_ids': list(self.results), 'algorithms': self.algorithms,
                'error': self.error,
                'progress': self.progress, 'model_revision': self.model_revision, 'provider': self.provider,
                'result_details': [{'result_id': key, 'width': image.width, 'height': image.height, **self.result_metadata[key]}
                                   for key, image in self.results.items()]}


class JobQueue:
    """Serialize native work and keep cancellation independent of thread preemption."""

    def __init__(self, assets: AssetStore, *, processor=process, max_jobs=32,
                 result_budget=POLICY.result_budget_bytes, model_manager: ModelManager | None = None):
        self.assets = assets
        self.processor = processor
        self.max_jobs = max_jobs
        self.result_budget = result_budget
        self.model_manager = model_manager
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
        if any(a not in {'opencv_telea', 'opencv_ns', 'lama', 'lanczos', 'realesrgan_x4plus'} for a in algorithms):
            raise ValueError('algorithm unavailable')
        image = self.assets.get_image(asset_id)
        target_size = None
        if any(a in {'lanczos', 'realesrgan_x4plus'} for a in algorithms):
            if len(algorithms) != 1:
                raise ValueError('upscale requires a separate job')
            has_target = target_width is not None or target_height is not None
            if has_target:
                if not (isinstance(target_width, int) and isinstance(target_height, int) and target_width > 0 and target_height > 0):
                    raise ValueError('target width and height must be positive integers')
                target_size = (target_width, target_height)
            elif scale not in (2, 4):
                raise ValueError('upscale requires scale 2 or 4, or a target size')
            target_size = target_size or (image.width * scale, image.height * scale)
            admit_image_job(image, target_size, ai=algorithms == ['realesrgan_x4plus'],
                            result_bytes=sum(j.result_bytes for j in self.jobs.values()))
        else:
            if scale != 1:
                raise ValueError('inpaint scale must be 1')
            if mask is None or mask.shape != image.rgb.shape[:2] or mask.dtype != np.uint8:
                raise ValueError('mask dimensions must match the source')
            if not np.all((mask == 0) | (mask == 255)) or not np.any(mask):
                raise ValueError('mask must contain a binary selection')
        self.assets.acquire_for_job(asset_id)
        job = Job(uuid4().hex, asset_id, list(algorithms), None if mask is None else mask.copy(), scale, target_size)
        if 'realesrgan_x4plus' in algorithms or 'lama' in algorithms:
            if self.model_manager is None:
                self.assets.release_from_job(asset_id)
                raise ModelManagerError('not_ready', 'AI model is not ready.')
            model_id = 'lama' if 'lama' in algorithms else 'realesrgan-x4plus'
            try:
                job.model_lease = self.model_manager.lease(model_id)
                job.model_path = job.model_lease.__enter__()
                job.provider = self.model_manager.selected_provider(model_id)
                job.model_revision = job.model_path.parent.name
            except Exception:
                if getattr(job, 'model_path', None) is not None:
                    job.model_lease.__exit__(None, None, None)
                self.assets.release_from_job(asset_id)
                raise
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
            job.cancel_event.set()
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
                        if self.processor is process:
                            def update_progress(done, total):
                                job.progress = {'completed': done, 'total': total, 'phase': 'tiles'}
                            result = await asyncio.get_running_loop().run_in_executor(
                                self.executor, lambda: self.processor(
                                    image, job.mask, algorithm, job.scale, job.target_size,
                                    model_path=getattr(job, 'model_path', None),
                                    provider=getattr(job, 'provider', None),
                                    cancel_event=job.cancel_event, progress=update_progress))
                        else:
                            result = await asyncio.get_running_loop().run_in_executor(
                                self.executor, self.processor, image, job.mask, algorithm, job.scale)
                        if job.status == 'cancelling':
                            break
                        size = result.rgb.nbytes + (result.alpha.nbytes if result.alpha is not None else 0)
                        if sum(j.result_bytes for j in self.jobs.values()) + size > self.result_budget:
                            raise MemoryError('result budget exceeded')
                        result_id = uuid4().hex
                        job.results[result_id] = result
                        job.result_metadata[result_id] = {'algorithm': algorithm,
                            'model_revision': job.model_revision if algorithm in {'lama', 'realesrgan_x4plus'} else None,
                            'provider': job.provider if algorithm in {'lama', 'realesrgan_x4plus'} else 'CPU'}
                        job.result_bytes += size
                        job.emit('result', result_id=result_id, **job.result_metadata[result_id],
                                 seconds=monotonic() - started, width=result.width, height=result.height)
                job.status = 'cancelled' if job.status == 'cancelling' else 'completed'
            except (InferenceCancelled, asyncio.CancelledError):
                job.status = 'cancelled'
            except Exception as error:
                job.status = 'cancelled' if job.status == 'cancelling' else 'failed'
                if job.status == 'failed':
                    if isinstance(error, ModelFileMissingError):
                        job.error = {'code': 'model_missing', 'message': 'LaMa modeli kurulu değil. Model kurulana kadar Sil veya Lanczos kullanabilirsiniz.'}
                    elif isinstance(error, ModelStoreError):
                        job.error = {'code': 'model_invalid', 'message': 'LaMa modelinin bütünlük doğrulaması başarısız. Model yeniden kurulmalı.'}
                    elif isinstance(error, MemoryError):
                        job.error = {'code': 'memory_limit', 'message': 'İşlem için yeterli bellek yok. Daha küçük bir görsel deneyin.'}
                    elif isinstance(error, ResourceLimitError):
                        job.error = {'code': error.code, 'message': str(error)}
                    elif isinstance(error, ModelManagerError):
                        job.error = {'code': error.code, 'message': str(error)}
                    else:
                        job.error = {'code': 'inference_failed', 'message': 'Görüntü işleme başarısız oldu. Seçili algoritmayı ve görseli kontrol edip tekrar deneyin.'}
                    job.emit('error', **job.error)
            finally:
                job.mask = None
                self.assets.release_from_job(job.asset_id)
                if job.model_lease is not None:
                    job.model_lease.__exit__(None, None, None)
                    job.model_lease = None
                job.emit(job.status, job_id=job.job_id)
                self.pending.task_done()
