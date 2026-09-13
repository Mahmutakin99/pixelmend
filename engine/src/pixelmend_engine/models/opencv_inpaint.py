"""Expose OpenCV's deterministic local inpainting algorithms."""

from typing import Literal

import cv2
import numpy as np


class MaskContractError(ValueError):
    """Raised before an adapter can reinterpret a malformed editor mask."""


class OpenCVInpaint:
    """Run either Telea or Navier-Stokes with PixelMend's 255-means-process mask."""

    def __init__(self, algorithm: Literal["telea", "ns"], radius: float = 3.0) -> None:
        if algorithm not in {"telea", "ns"}:
            raise ValueError(f"unsupported OpenCV inpaint algorithm: {algorithm}")
        self._algorithm = algorithm
        self._radius = radius

    def run(self, image: np.ndarray, mask: np.ndarray | None = None, **_: object) -> np.ndarray:
        """Inpaint a canonical RGB image without resizing or inverting its mask."""
        if mask is None:
            raise MaskContractError("inpainting requires a mask")
        if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("image must be H×W×3 uint8 RGB")
        if mask.dtype != np.uint8 or mask.shape != image.shape[:2]:
            raise MaskContractError("mask must be H×W uint8 matching the image")
        if not np.all((mask == 0) | (mask == 255)):
            raise MaskContractError("mask must contain only 0 and 255")

        method = cv2.INPAINT_TELEA if self._algorithm == "telea" else cv2.INPAINT_NS
        # OpenCV operates independently per color channel; RGB ordering remains stable.
        return cv2.inpaint(image, mask, self._radius, method)
