from types import SimpleNamespace

import numpy as np

from pixelmend_engine.models.migan_onnx import MIGANInpaint


class BlackFillSession:
    def __init__(self):
        self.inputs = None

    def get_inputs(self):
        return [
            SimpleNamespace(name='image', type='tensor(uint8)', shape=['batch', 3, 'height', 'width']),
            SimpleNamespace(name='mask', type='tensor(uint8)', shape=['batch', 1, 'height', 'width']),
        ]

    def get_outputs(self):
        return [SimpleNamespace(name='result', type='tensor(uint8)', shape=['batch', 3, 'height', 'width'])]

    def run(self, _, inputs):
        self.inputs = inputs
        return [np.zeros_like(inputs['image'])]


def test_migan_inverts_selection_for_its_known_region_contract_and_preserves_unmasked_pixels():
    session = BlackFillSession()
    adapter = MIGANInpaint('unused', session=session)
    image = np.array([[[1, 2, 3], [4, 5, 6]], [[7, 8, 9], [10, 11, 12]]], dtype=np.uint8)
    selection = np.array([[0, 255], [0, 0]], dtype=np.uint8)

    result = adapter.run(image, selection)

    assert session.inputs['image'].dtype == np.uint8
    np.testing.assert_array_equal(session.inputs['image'][0], image.transpose(2, 0, 1))
    np.testing.assert_array_equal(session.inputs['mask'][0, 0], 255 - selection)
    np.testing.assert_array_equal(result, np.array([[[1, 2, 3], [0, 0, 0]], [[7, 8, 9], [10, 11, 12]]], dtype=np.uint8))
