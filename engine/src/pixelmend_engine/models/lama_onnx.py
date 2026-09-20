"""Pinned LaMa inference with aspect-preserving ROI and exact source protection."""

import cv2
import numpy as np
import onnxruntime as ort

from ..model_store import LAMA_ONNX_MANIFEST, model_file_path, verify_model_file


def prepare_roi(image, mask):
    """Letterbox a contextual ROI so narrow selections are never stretched square."""
    if mask is None or mask.shape != image.shape[:2] or mask.dtype != np.uint8:
        raise ValueError('mask must match image')
    if not np.all((mask == 0) | (mask == 255)) or not np.any(mask):
        raise ValueError('binary selection required')
    ys, xs = np.where(mask != 0)
    margin = max(32, (max(xs.max()-xs.min(), ys.max()-ys.min()) + 1) // 2)
    x0, y0 = max(0, int(xs.min())-margin), max(0, int(ys.min())-margin)
    x1, y1 = min(image.shape[1], int(xs.max())+margin+1), min(image.shape[0], int(ys.max())+margin+1)
    ratio = 512 / max(x1-x0, y1-y0)
    width, height = max(1, round((x1-x0)*ratio)), max(1, round((y1-y0)*ratio))
    roi = cv2.resize(image[y0:y1, x0:x1], (width, height), interpolation=cv2.INTER_AREA)
    selection = cv2.resize(mask[y0:y1, x0:x1], (width, height), interpolation=cv2.INTER_NEAREST)
    roi = cv2.copyMakeBorder(roi, 0, 512-height, 0, 512-width, cv2.BORDER_REFLECT_101)
    selection = np.pad(selection, ((0, 512-height), (0, 512-width)))
    return (roi.transpose(2, 0, 1)[None].astype(np.float32) / 255,
            selection[None, None].astype(np.float32) / 255,
            (x0, y0, x1, y1, width, height))


class LamaInpaint:
    def __init__(self, models_dir=None, *, model_path=None, providers=None):
        """Verify provenance before loading native model code."""
        path = verify_model_file(model_path if model_path is not None else model_file_path(models_dir, LAMA_ONNX_MANIFEST), LAMA_ONNX_MANIFEST)
        ort.disable_telemetry_events()
        self.session = ort.InferenceSession(str(path), providers=providers or ['CPUExecutionProvider'])
        inputs = {i.name: i for i in self.session.get_inputs()}
        for name, channels in [('image', 3), ('mask', 1)]:
            if name not in inputs or inputs[name].shape[1:] != [channels, 512, 512] or inputs[name].type != 'tensor(float)':
                raise ValueError('unexpected LaMa input contract')

    def run(self, image, mask=None, **params):
        """Return RGB uint8; unmasked pixels remain byte-identical to the source."""
        if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
            raise ValueError('RGB uint8 required')
        data, selection, geometry = prepare_roi(image, mask)
        output = self.session.run(None, {'image': data, 'mask': selection})[0]
        if output.shape != (1, 3, 512, 512) or not np.isfinite(output).all():
            raise ValueError('invalid model output')
        x0, y0, x1, y1, width, height = geometry
        pixels = output[0].transpose(1, 2, 0)[:height, :width]
        pixels = cv2.resize(pixels, (x1-x0, y1-y0), interpolation=cv2.INTER_CUBIC)
        pixels = np.clip(pixels, 0, 255).astype(np.uint8)
        result = image.copy()
        selected = mask[y0:y1, x0:x1] != 0
        result[y0:y1, x0:x1][selected] = pixels[selected]
        return result
