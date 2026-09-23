from pixelmend_engine.sdxl_package import SDXL_INPAINTING_PACKAGE


def test_sdxl_package_is_a_pinned_complete_fp16_diffusers_runtime_set():
    paths = {item.path for item in SDXL_INPAINTING_PACKAGE.files}
    assert SDXL_INPAINTING_PACKAGE.model_id == 'sdxl-inpainting'
    assert SDXL_INPAINTING_PACKAGE.revision == '115134f363124c53c7d878647567d04daf26e41e'
    assert {'model_index.json', 'unet/diffusion_pytorch_model.fp16.safetensors',
            'vae/diffusion_pytorch_model.fp16.safetensors',
            'text_encoder/model.fp16.safetensors',
            'text_encoder_2/model.fp16.safetensors'} <= paths
    assert sum(item.size_bytes for item in SDXL_INPAINTING_PACKAGE.files) == 6_941_218_469
