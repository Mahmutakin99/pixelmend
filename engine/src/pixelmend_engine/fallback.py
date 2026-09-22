"""Retry only accelerator execution failures, with the same verified artifact."""
from .model_manager import ModelManagerError
from .policy import admit_image_job, ResourceLimitError
import psutil


def may_retry_cpu(error, provider, cancelled):
    if cancelled or provider in {None, 'CPUExecutionProvider'}:
        return False
    if isinstance(error, ModelManagerError):
        return error.code == 'provider_unavailable'
    return type(error).__module__.startswith('onnxruntime.') and type(error).__name__ in {'Fail', 'RuntimeException', 'EPFail'}


def check_cpu_capacity(image, target_size, *, upscale, result_bytes):
    if upscale:
        admit_image_job(image, target_size, ai=True, result_bytes=result_bytes)
    elif psutil.virtual_memory().available < 1024**3:
        raise ResourceLimitError('memory_limit', 'CPU ile yeniden denemek için yeterli kullanılabilir bellek yok.')
