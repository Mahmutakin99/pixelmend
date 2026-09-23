from pathlib import Path
from threading import Event
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from pixelmend_engine.models.realesrgan_onnx import RealESRGANUpscale, InferenceCancelled
from pixelmend_engine.models.hat_onnx import HATGANUpscale
from pixelmend_engine.models.swin2sr_onnx import Swin2SRUpscale


class NearestSession:
    def get_inputs(self):
        return [SimpleNamespace(name='input', type='tensor(float)', shape=[1, 3, 'h', 'w'])]

    def get_outputs(self):
        return [SimpleNamespace(name='output', type='tensor(float)', shape=[1, 3, 'h4', 'w4'])]

    def run(self, _, inputs):
        return [np.repeat(np.repeat(inputs['input'], 4, axis=2), 4, axis=3)]


@pytest.mark.parametrize('size', [(1, 1), (17, 29), (30, 30)])
def test_tiles_cover_edges_and_preserve_rgb_without_seams(tmp_path, size):
    image = np.random.default_rng(2).integers(0, 256, (*size, 3), dtype=np.uint8)
    adapter = RealESRGANUpscale('unused', session=NearestSession(), tile_size=12, overlap=3, temp_dir=tmp_path)
    progress = []
    result = adapter.run(image, progress=lambda done, total: progress.append((done, total)))
    np.testing.assert_array_equal(result, image.repeat(4, axis=0).repeat(4, axis=1))
    assert progress[-1][0] == progress[-1][1]
    assert not list(tmp_path.iterdir())


def test_custom_target_is_lanczos_after_natural_four_x(tmp_path):
    image = np.random.default_rng(4).integers(0, 256, (13, 16, 3), dtype=np.uint8)
    adapter = RealESRGANUpscale('unused', session=NearestSession(), tile_size=12, overlap=3, temp_dir=tmp_path)
    natural = image.repeat(4, axis=0).repeat(4, axis=1)
    expected = np.asarray(Image.fromarray(natural).resize((21, 19), Image.Resampling.LANCZOS))
    np.testing.assert_array_equal(adapter.run(image, target_size=(21, 19)), expected)


def test_cancel_between_tiles_removes_private_intermediates(tmp_path):
    cancel = Event()
    adapter = RealESRGANUpscale('unused', session=NearestSession(), tile_size=12, overlap=3, temp_dir=tmp_path)
    with pytest.raises(InferenceCancelled):
        adapter.run(np.zeros((25, 25, 3), np.uint8), cancel_event=cancel,
                    progress=lambda *_: cancel.set())
    assert not list(tmp_path.iterdir())


def test_nonfinite_inference_removes_intermediates(tmp_path):
    class Bad(NearestSession):
        def run(self, _, inputs):
            return [super().run(_, inputs)[0] * np.nan]
    adapter = RealESRGANUpscale('unused', session=Bad(), temp_dir=tmp_path)
    with pytest.raises(ValueError, match='invalid RealESRGAN output'):
        adapter.run(np.zeros((2, 2, 3), np.uint8))
    assert not list(tmp_path.iterdir())


def test_hat_pads_windowed_edge_tiles_then_crops_to_the_requested_pixels(tmp_path):
    class RecordingSession(NearestSession):
        def __init__(self):
            self.shapes = []

        def run(self, names, inputs):
            self.shapes.append(inputs['input'].shape)
            return super().run(names, inputs)

    session = RecordingSession()
    image = np.random.default_rng(9).integers(0, 256, (17, 19, 3), dtype=np.uint8)
    adapter = HATGANUpscale('unused', session=session, tile_size=48, overlap=16, temp_dir=tmp_path)

    result = adapter.run(image)

    np.testing.assert_array_equal(result, image.repeat(4, axis=0).repeat(4, axis=1))
    assert session.shapes == [(1, 3, 32, 32)]


@pytest.mark.parametrize('tile_size, overlap', [(257, 16), (64, 0), (64, 64)])
def test_hat_uses_a_bounded_window_compatible_tile_contract(tile_size, overlap):
    with pytest.raises(ValueError):
        HATGANUpscale('unused', session=NearestSession(), tile_size=tile_size, overlap=overlap)


def test_swin2sr_pads_eight_pixel_attention_windows_and_crops_edge_tiles(tmp_path):
    class RecordingSession(NearestSession):
        def __init__(self):
            self.shapes = []

        def run(self, names, inputs):
            self.shapes.append(inputs['input'].shape)
            return super().run(names, inputs)

    session = RecordingSession()
    image = np.random.default_rng(11).integers(0, 256, (13, 17, 3), dtype=np.uint8)
    adapter = Swin2SRUpscale('unused', session=session, tile_size=48, overlap=8, temp_dir=tmp_path)

    result = adapter.run(image)

    np.testing.assert_array_equal(result, image.repeat(4, axis=0).repeat(4, axis=1))
    assert session.shapes == [(1, 3, 16, 24)]
