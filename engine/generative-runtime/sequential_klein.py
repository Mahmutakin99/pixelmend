"""One-shot phased loading for the pinned MFLUX Klein 4B implementation.

Keep native prompt encoding, reference conditioning, denoising and VAE decode.
Only change when each unchanged component is loaded and released.
"""

class ComponentPhases:
    def __init__(self,model,load,evaluate,clear):
        self.model=model;self.load=load;self.evaluate=evaluate;self.clear=clear
        self.prompt_ready=False;self.loop_ready=False
        self.vae_after_conditioning=None

    def initialize(self):
        self.model.text_encoder=self.load('text_encoder')

    def finish_prompt(self,encoded):
        if self.prompt_ready:raise RuntimeError('one-shot prompt encoder already released')
        self.evaluate(*(value for value in encoded if value is not None))
        self.model.text_encoder=None
        self.clear()
        self.model.vae=self.load('vae')
        self.prompt_ready=True

    def call_before_loop(self,*,latents,**kwargs):
        if not self.prompt_ready:raise RuntimeError('prompt must be encoded before denoising')
        self.evaluate(latents)
        self.loop_ready=True

    def start_prediction(self,conditions):
        if not self.loop_ready:raise RuntimeError('prompt and latents must be ready before denoising')
        if self.model.transformer is None:
            # Materialize the complete VAE reference graph before diffusion weights
            # consume memory. No tiling or numerical operation is changed.
            self.evaluate(*conditions)
            if self.vae_after_conditioning is not None:
                self.model.vae=self.vae_after_conditioning
            self.clear()
            self.model.transformer=self.load('transformer')


def create_sequential_klein(*,model_path,model_config,edit=False,progress=None):
    import gc
    from pathlib import Path
    import mlx.core as mx
    import mlx.nn as nn
    from mlx.utils import tree_flatten
    from mflux.models.flux2 import Flux2Klein
    from mflux.models.flux2.variants.edit.flux2_klein_edit import Flux2KleinEdit
    from mflux.models.flux2.flux2_initializer import Flux2Initializer
    from mflux.models.flux2.model.flux2_text_encoder.qwen3_text_encoder import Qwen3TextEncoder
    from mflux.models.flux2.model.flux2_transformer.transformer import Flux2Transformer
    from mflux.models.flux2.model.flux2_vae.vae import Flux2VAE
    from mflux.models.flux2.weights.flux2_weight_definition import Flux2KleinWeightDefinition
    from mflux.models.common.weights.loading.weight_loader import WeightLoader
    from mflux.models.common.weights.loading.weight_applier import WeightApplier

    if model_config.model_name!='black-forest-labs/FLUX.2-klein-4B' or model_config.supports_kv_cache:
        raise ValueError('unsupported phased model')
    definitions={component.name:component for component in Flux2KleinWeightDefinition.get_components()}
    constructors={'text_encoder':lambda:Qwen3TextEncoder(**model_config.text_encoder_overrides),
                  'transformer':lambda:Flux2Transformer(**model_config.transformer_overrides),
                  'vae':Flux2VAE}

    def load(name):
        component=definitions[name]
        weights=WeightLoader.load_single_local(component=component,root_path=Path(model_path))
        if name!='vae' and weights.meta_data.quantization_level!=4:
            raise ValueError('expected verified q4 component')
        module=constructors[name]()
        WeightApplier.apply_and_quantize_single(weights=weights,model=module,component=component,
            quantize_arg=None,quantization_predicate=Flux2KleinWeightDefinition.quantization_predicate)
        mx.eval(*[value for _,value in tree_flatten(module.parameters())])
        if progress is not None:progress()
        return module

    def clear():
        gc.collect();mx.clear_cache()

    base=Flux2KleinEdit if edit else Flux2Klein
    class SequentialKlein(base):
        def __init__(self):
            nn.Module.__init__(self)
            Flux2Initializer._init_config(self,model_config)
            Flux2Initializer._init_tokenizers(self,model_path)
            self.vae=None;self.transformer=None;self.text_encoder=None
            self.bits=4;self.lora_paths=[];self.lora_scales=[]
            phases=ComponentPhases(self,load,mx.eval,clear)
            self._component_phases=phases
            phases.initialize()
            self.callbacks.register(phases)

        def _encode_prompt_pair(self,**kwargs):
            encoded=super()._encode_prompt_pair(**kwargs)
            self._component_phases.finish_prompt(encoded)
            if progress is not None:progress()
            return encoded

        def _predict(self,transformer):
            native_predict=None
            def predict(**kwargs):
                nonlocal native_predict
                if native_predict is None:
                    self._component_phases.start_prediction(
                        tuple(value for value in kwargs.values() if isinstance(value,mx.array)))
                    native_predict=super(SequentialKlein,self)._predict(self.transformer)
                return native_predict(**kwargs)
            # The native loop deletes this closure before MemorySaver frees the
            # transformer, so the compiled callable cannot retain decode weights.
            return predict

    return SequentialKlein()


def probe_components(load,materialize,clear):
    """Load-only check; each component ends its lifetime before the next load."""
    for name in ('text_encoder','vae','transformer'):
        component=load(name)
        try:materialize(component)
        finally:
            del component
            clear()


def probe_klein_loading(model_path):
    import mlx.core as mx
    from mlx.utils import tree_flatten
    from mflux.models.common.config.model_config import ModelConfig
    model=create_sequential_klein(model_path=model_path,model_config=ModelConfig.flux2_klein_4b())
    phases=model._component_phases
    def load(name):
        if name=='text_encoder':
            component=model.text_encoder;model.text_encoder=None;return component
        return phases.load(name)
    probe_components(load,lambda module:mx.eval(*[value for _,value in tree_flatten(module.parameters())]),phases.clear)
