import numpy as np
from PIL import Image
import sys
from threading import Event
import types
import pytest

from pixelmend_engine.models import sdxl_worker
from pixelmend_engine.models.sdxl_worker import composite_selected, context_box
from pixelmend_engine.models.realesrgan_onnx import InferenceCancelled


def test_sdxl_composite_never_changes_pixels_outside_the_selection():
    source = np.arange(4 * 5 * 3, dtype=np.uint8).reshape(4, 5, 3)
    candidate = np.full_like(source, 255)
    mask = np.zeros((4, 5), dtype=np.uint8)
    mask[1:3, 2:4] = 255

    result = composite_selected(source, candidate, mask)

    np.testing.assert_array_equal(result[mask == 0], source[mask == 0])
    np.testing.assert_array_equal(result[mask == 255], candidate[mask == 255])


def test_sdxl_context_is_bounded_and_contains_edge_selection():
    mask = np.zeros((900, 1600), dtype=np.uint8)
    mask[820:900, 0:120] = 255

    x0, y0, x1, y1 = context_box(mask, maximum=512)

    assert 0 <= x0 < x1 <= 1600 and 0 <= y0 < y1 <= 900
    assert x1 - x0 <= 512 and y1 - y0 <= 512
    assert x0 == 0 and y1 == 900


def test_sdxl_rejects_nonbinary_or_mismatched_selection_before_loading_model(tmp_path, monkeypatch):
    monkeypatch.setattr(sdxl_worker, 'verify_package',
                        lambda *_args, **_kwargs: pytest.fail('invalid inputs must not load a model'))
    source = np.zeros((8, 8, 3), dtype=np.uint8)
    soft_mask = np.zeros((8, 8), dtype=np.uint8)
    soft_mask[2:4, 2:4] = 128

    with pytest.raises(ValueError, match='binary'):
        sdxl_worker.run_sdxl_inpaint(tmp_path, source, soft_mask)
    with pytest.raises(ValueError, match='dimensions'):
        sdxl_worker.run_sdxl_inpaint(tmp_path, source, np.full((4, 4), 255, dtype=np.uint8))


def test_sdxl_loader_requests_only_the_pinned_fp16_files(tmp_path, monkeypatch):
    calls = {}

    class Pipeline:
        @classmethod
        def from_pretrained(cls, root, **kwargs):
            calls.update(kwargs)
            return cls()

        def to(self, device):
            return self

        def enable_vae_tiling(self):
            return None

        def __call__(self, **kwargs):
            return types.SimpleNamespace(images=[Image.new('RGB', (512, 512), (1, 2, 3))])

    fake_torch = types.ModuleType('torch')
    fake_torch.float16, fake_torch.float32 = 'fp16', 'fp32'
    fake_torch.backends = types.SimpleNamespace(mps=types.SimpleNamespace(is_available=lambda: True))
    fake_torch.mps = types.SimpleNamespace(set_per_process_memory_fraction=lambda fraction: None)
    fake_torch.Generator = lambda device: types.SimpleNamespace(manual_seed=lambda seed: seed)
    fake_diffusers = types.ModuleType('diffusers')
    fake_diffusers.StableDiffusionXLInpaintPipeline = Pipeline
    monkeypatch.setitem(sys.modules, 'torch', fake_torch)
    monkeypatch.setitem(sys.modules, 'diffusers', fake_diffusers)
    monkeypatch.setattr(sdxl_worker, 'verify_package', lambda root, manifest, **kwargs: root)
    source = np.zeros((8, 8, 3), dtype=np.uint8)
    mask = np.zeros((8, 8), dtype=np.uint8)
    mask[3:5, 3:5] = 255

    result, _ = sdxl_worker.run_sdxl_inpaint(tmp_path, source, mask)

    assert calls['variant'] == 'fp16'
    np.testing.assert_array_equal(result[mask == 0], source[mask == 0])


def test_sdxl_cancellation_during_diffusion_never_returns_partial_pixels(tmp_path, monkeypatch):
    stopped = Event()

    class Pipeline:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            return cls()

        def to(self, device):
            return self

        def enable_vae_tiling(self):
            return None

        def __call__(self, **kwargs):
            stopped.set()
            kwargs['callback_on_step_end'](self, 1, 1, {})
            raise AssertionError('diffusion should have been cancelled')

    fake_torch = types.ModuleType('torch')
    fake_torch.float16 = 'fp16'
    fake_torch.backends = types.SimpleNamespace(mps=types.SimpleNamespace(is_available=lambda: True,
                                                                          empty_cache=lambda: None))
    fake_torch.mps = types.SimpleNamespace(set_per_process_memory_fraction=lambda fraction: None)
    fake_torch.Generator = lambda device: types.SimpleNamespace(manual_seed=lambda seed: seed)
    fake_diffusers = types.ModuleType('diffusers')
    fake_diffusers.StableDiffusionXLInpaintPipeline = Pipeline
    monkeypatch.setitem(sys.modules, 'torch', fake_torch)
    monkeypatch.setitem(sys.modules, 'diffusers', fake_diffusers)
    monkeypatch.setattr(sdxl_worker, 'verify_package', lambda root, manifest, **kwargs: root)
    source = np.zeros((8, 8, 3), dtype=np.uint8)
    mask = np.zeros((8, 8), dtype=np.uint8)
    mask[3:5, 3:5] = 255

    with pytest.raises(InferenceCancelled):
        sdxl_worker.run_sdxl_inpaint(tmp_path, source, mask, cancel_event=stopped)


def test_sdxl_rejects_nonfinite_mps_latents_instead_of_publishing_black_output(tmp_path, monkeypatch):
    class Pipeline:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            return cls()

        def enable_vae_tiling(self):
            return None

        def to(self, device):
            return self

        def __call__(self, **kwargs):
            kwargs['callback_on_step_end'](self, 0, 0, {'latents': object()})
            raise AssertionError('a nonfinite result must stop diffusion')

    fake_torch = types.ModuleType('torch')
    fake_torch.float16 = 'fp16'
    fake_torch.backends = types.SimpleNamespace(mps=types.SimpleNamespace(is_available=lambda: True))
    fake_torch.mps = types.SimpleNamespace(set_per_process_memory_fraction=lambda fraction: None)
    fake_torch.isfinite = lambda latents: types.SimpleNamespace(all=lambda: False)
    fake_torch.Generator = lambda device: types.SimpleNamespace(manual_seed=lambda seed: seed)
    fake_diffusers = types.ModuleType('diffusers')
    fake_diffusers.StableDiffusionXLInpaintPipeline = Pipeline
    monkeypatch.setitem(sys.modules, 'torch', fake_torch)
    monkeypatch.setitem(sys.modules, 'diffusers', fake_diffusers)
    monkeypatch.setattr(sdxl_worker, 'verify_package', lambda root, manifest, **kwargs: root)
    source = np.zeros((8, 8, 3), dtype=np.uint8)
    mask = np.zeros((8, 8), dtype=np.uint8)
    mask[3:5, 3:5] = 255

    with pytest.raises(sdxl_worker.SDXLRuntimeUnavailable, match='sayısal'):
        sdxl_worker.run_sdxl_inpaint(tmp_path, source, mask)


@pytest.mark.parametrize('shape,selection',[
    ((100,2000),(slice(40,60),slice(500,1400))),
    ((2000,100),(slice(500,1400),slice(40,60))),
    ((1600,1600),(slice(900,1500),slice(900,1500))),
])
def test_bounded_crop_keeps_entire_selection(shape,selection):
    mask=np.zeros(shape,np.uint8);mask[selection]=255
    x0,y0,x1,y1=context_box(mask,maximum=1024)
    kept=np.zeros_like(mask);kept[y0:y1,x0:x1]=mask[y0:y1,x0:x1]
    np.testing.assert_array_equal(kept,mask)
    assert x1-x0<=1024 and y1-y0<=1024
