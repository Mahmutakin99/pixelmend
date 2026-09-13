import numpy as np
import pytest


@pytest.mark.parametrize("algorithm", ["telea", "ns"])
def test_opencv_adapters_modify_only_the_binary_mask_region(algorithm: str) -> None:
    """Inverting 0/255 semantics would alter the protected surround instead."""
    from pixelmend_engine.models.opencv_inpaint import OpenCVInpaint

    image = np.full((9, 9, 3), 20, dtype=np.uint8)
    image[4, 4] = [255, 0, 0]
    mask = np.zeros((9, 9), dtype=np.uint8)
    mask[4, 4] = 255

    result = OpenCVInpaint(algorithm).run(image, mask)

    assert result.dtype == np.uint8
    assert result.shape == image.shape
    np.testing.assert_array_equal(result[0, 0], image[0, 0])
    assert not np.array_equal(result[4, 4], image[4, 4])


def test_opencv_adapter_rejects_noncanonical_mask_shape() -> None:
    """Letting OpenCV resize an incorrect mask would move the user's stroke."""
    from pixelmend_engine.models.opencv_inpaint import MaskContractError, OpenCVInpaint

    with pytest.raises(MaskContractError):
        OpenCVInpaint("telea").run(
            np.zeros((4, 4, 3), dtype=np.uint8), np.zeros((3, 4), dtype=np.uint8)
        )
