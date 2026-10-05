"""Preserve native Klein arithmetic while ending denoising before VAE decode."""
import hashlib
import os
from pathlib import Path
import stat


class DenoiseComplete(Exception):
    pass


def _latent_shape(width,height):return (1,128,height//16,width//16)


def intercept_decode(model,session,width,height):
    import mlx.core as mx
    native_finish=model._component_phases.finish_prompt
    path=Path(session)/'latents.safetensors'
    def save_latents(packed_latents,**_):
        mx.eval(packed_latents)
        if (tuple(packed_latents.shape)!=_latent_shape(width,height)
                or packed_latents.dtype!=mx.bfloat16
                or not bool(mx.all(mx.isfinite(packed_latents)).item())):
            raise ValueError('invalid_output')
        with path.open('xb'):os.chmod(path,0o600)
        mx.save_safetensors(str(path),{'packed_latents':packed_latents})
        os.chmod(path,0o600)
        raise DenoiseComplete()
    def finish(encoded):
        native_finish(encoded)
        model.vae.decode_packed_latents=save_latents
    model._component_phases.finish_prompt=finish


def decode_latents(model_path,session,width,height,digest):
    import mlx.core as mx
    from mlx.utils import tree_flatten
    from mflux.models.flux2.model.flux2_vae.vae import Flux2VAE
    from mflux.models.flux2.weights.flux2_weight_definition import Flux2KleinWeightDefinition
    from mflux.models.common.weights.loading.weight_loader import WeightLoader
    from mflux.models.common.weights.loading.weight_applier import WeightApplier
    from mflux.utils.image_util import ImageUtil
    path=Path(session)/'latents.safetensors'
    try:
        with os.fdopen(os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)),'rb') as stream:
            info=os.fstat(stream.fileno())
            maximum=8+4096+2*128*(height//16)*(width//16)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid()
                    or stat.S_IMODE(info.st_mode)!=0o600 or info.st_nlink!=1
                    or not 8<info.st_size<=maximum):raise ValueError()
            raw=stream.read(maximum+1)
        if (not isinstance(digest,str) or len(digest)!=64
                or hashlib.sha256(raw).hexdigest()!=digest):raise ValueError()
    except (OSError,ValueError):raise ValueError('invalid_input') from None
    latents=mx.load(str(path))
    if set(latents)!={'packed_latents'}:raise ValueError('invalid_input')
    packed=latents['packed_latents']
    if (tuple(packed.shape)!=_latent_shape(width,height) or packed.dtype!=mx.bfloat16
            or not bool(mx.all(mx.isfinite(packed)).item())):raise ValueError('invalid_input')
    component=next(x for x in Flux2KleinWeightDefinition.get_components() if x.name=='vae')
    weights=WeightLoader.load_single_local(component=component,root_path=Path(model_path))
    if weights.meta_data.quantization_level is not None:raise ValueError('invalid_input')
    vae=Flux2VAE()
    WeightApplier.apply_and_quantize_single(weights=weights,model=vae,component=component,
        quantize_arg=None,quantization_predicate=Flux2KleinWeightDefinition.quantization_predicate)
    mx.eval(*[value for _,value in tree_flatten(vae.parameters())])
    return ImageUtil.to_pil(vae.decode_packed_latents(packed,tiling_config=None))
