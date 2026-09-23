"""Verified MI-GAN ONNX Pipeline adapter for masked object removal."""

import numpy as np
import onnxruntime as ort

from ..inference_evidence import InferenceEvidence


class MIGANInpaint:
    """Adapt PixelMend's selected-pixel mask to MI-GAN's known-pixel mask.

    The upstream pipeline expects NCHW uint8 RGB and a uint8 mask where 255
    means *known*. PixelMend uses 255 for the selected removal area, therefore
    only the model input is inverted. The returned image is composited again so
    no model approximation can alter a pixel outside the user selection.
    """

    def __init__(self, model_path, *, providers=None, session=None, intra_op_threads=4):
        if type(intra_op_threads) is not int or intra_op_threads < 1:
            raise ValueError('intra_op_threads must be positive')
        ort.disable_telemetry_events()
        options = ort.SessionOptions()
        options.intra_op_num_threads = intra_op_threads
        self.evidence = InferenceEvidence(options, providers, enabled=session is None)
        self.session = session if session is not None else ort.InferenceSession(
            str(model_path), sess_options=options, providers=providers or ['CPUExecutionProvider'])
        inputs, outputs = self.session.get_inputs(), self.session.get_outputs()
        if (len(inputs) != 2 or len(outputs) != 1 or inputs[0].type != 'tensor(uint8)'
                or inputs[1].type != 'tensor(uint8)' or outputs[0].type != 'tensor(uint8)'
                or len(inputs[0].shape) != 4 or len(inputs[1].shape) != 4
                or len(outputs[0].shape) != 4 or inputs[0].shape[1] != 3
                or inputs[1].shape[1] != 1 or outputs[0].shape[1] != 3):
            raise ValueError('expected dynamic uint8 NCHW RGB + known-mask MI-GAN contract')
        self.image_name, self.mask_name = inputs[0].name, inputs[1].name

    def run(self, image, mask):
        if (image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3
                or mask.dtype != np.uint8 or mask.shape != image.shape[:2]
                or not np.all((mask == 0) | (mask == 255))):
            raise ValueError('RGB uint8 image and binary selection mask required')
        model_mask = np.ascontiguousarray((255 - mask)[None, None])
        input_image = np.ascontiguousarray(image.transpose(2, 0, 1)[None])
        result = self.session.run(None, {self.image_name: input_image, self.mask_name: model_mask})[0]
        self.evidence.finish(self.session)
        if result.shape != input_image.shape or result.dtype != np.uint8:
            raise ValueError('invalid MI-GAN output')
        candidate = result[0].transpose(1, 2, 0)
        return np.where(mask[:, :, None] == 255, candidate, image)
