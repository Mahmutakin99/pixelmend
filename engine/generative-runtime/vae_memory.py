"""Materialize complete native VAE blocks without tiling or altered arithmetic."""
from functools import wraps


def materialize_block_calls(block_types,evaluate,clear):
    for block in block_types:
        original=block.__call__
        if getattr(original,'_pixelmend_materialized',False):continue
        @wraps(original)
        def materialized(self,*args,_original=original,**kwargs):
            value=_original(self,*args,**kwargs)
            evaluate(value)
            clear()
            return value
        materialized._pixelmend_materialized=True
        block.__call__=materialized


def configure_vae_evaluation(mx):
    from mflux.models.flux2.model.flux2_vae.common.resnet_block_2d import Flux2ResnetBlock2D
    from mflux.models.flux2.model.flux2_vae.common.attention import Flux2AttentionBlock
    from mflux.models.flux2.model.flux2_vae.common.upsample_2d import Flux2Upsample2D
    from mflux.models.flux2.model.flux2_vae.common.downsample_2d import Flux2Downsample2D
    materialize_block_calls((Flux2ResnetBlock2D,Flux2AttentionBlock,Flux2Upsample2D,Flux2Downsample2D),
                            mx.eval,mx.clear_cache)
