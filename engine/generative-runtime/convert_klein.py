"""Development-only streaming converter for the pinned distilled Klein 4B snapshot.

Uses MFLUX's own model shapes/mappings, quantizes only supported modules, and
keeps each shard below 1 GiB. Never loads all original weights together.
"""
import argparse
import gc
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile

REVISION = 'e7b7dc27f91deacad38e78976d1f2b499d76a294'
SHARD_BYTES = (1 << 30) - (2 << 20)


def quantize_weight(name, weight, quantizable_modules):
    import mlx.core as mx
    if name.endswith('.weight') and name[:-7] in quantizable_modules:
        packed, scales, biases = mx.quantize(weight, group_size=64, bits=4)
        prefix = name[:-7]
        return {name: packed, f'{prefix}.scales': scales, f'{prefix}.biases': biases}
    return {name: weight}


def generated_buffers(component, parameters, supplied):
    # Pinned Qwen3TextRotaryEmbedding computes this from fixed dim/base in its
    # constructor. HF has no stored tensor for it; native MFLUX saves it unchanged.
    name = 'rotary_emb.inv_freq'
    if component == 'text_encoder' and name in parameters and name not in supplied:
        return {name: parameters[name]}
    return {}


def read_header(path):
    with path.open('rb') as stream:
        size_bytes = stream.read(8)
        if len(size_bytes) != 8:
            raise ValueError('invalid safetensors header')
        size = struct.unpack('<Q', size_bytes)[0]
        if size > 64 << 20:
            raise ValueError('oversized safetensors header')
        return size, json.loads(stream.read(size))


def convert_component(source, destination, definition, model):
    import mlx.core as mx
    from mlx.utils import tree_flatten
    from mflux.models.common.weights.loading.safetensors_reader import SafetensorsReader, SafetensorsTensorInfo
    from mflux.models.common.weights.mapping.weight_mapper import WeightMapper

    paths = sorted((source / definition.hf_subdir).glob('*.safetensors'))
    tensors = {}
    for path in paths:
        if path.is_symlink():
            raise ValueError('source symlink rejected')
        header_size, header = read_header(path)
        for name, info in header.items():
            if name == '__metadata__':
                continue
            if name in tensors:
                raise ValueError('duplicate source tensor')
            tensors[name] = (path, header_size, info)
    names = dict.fromkeys(tensors)
    mapping = definition.mapping_getter()
    missing = WeightMapper.missing_required_names(names, mapping)
    if missing:
        raise ValueError(f'missing required source weights: {missing}')
    flat = WeightMapper._build_flat_mapping(mapping, WeightMapper._detect_num_blocks(names),
                                            WeightMapper._detect_num_layers(names))
    parameters = dict(tree_flatten(model.parameters()))
    expected = {name: tuple(value.shape) for name, value in parameters.items()}
    quantizable = {name for name, module in model.named_modules() if hasattr(module, 'to_quantized')}
    target = destination / definition.hf_subdir
    target.mkdir()
    shard, weight_map, seen = {}, {}, set()
    byte_count, shard_index = 0, 0
    metadata = {'quantization_level': '4', 'quantization_group_size': '64', 'mflux_version': '0.21.0'}

    def flush():
        nonlocal shard, byte_count, shard_index
        if not shard:
            return
        filename = f'{shard_index}.safetensors'
        mx.save_safetensors(str(target / filename), shard, metadata)
        if (target / filename).stat().st_size > 1 << 30:
            raise ValueError('shard exceeds transport limit')
        weight_map.update(dict.fromkeys(shard, filename))
        shard = {}
        byte_count = 0
        shard_index += 1
        gc.collect()
        mx.clear_cache()

    for name, (path, header_size, info) in tensors.items():
        targets = flat.get(name, [])
        if not targets:
            continue
        raw = SafetensorsReader._read_tensor(path, header_size + 8, SafetensorsTensorInfo(
            name=name, dtype=info['dtype'], shape=tuple(info['shape']),
            data_offsets=tuple(info['data_offsets'])))
        for mapped_name, transform in targets:
            tensor = transform(raw) if transform else raw
            if mapped_name not in expected or tuple(tensor.shape) != expected[mapped_name]:
                raise ValueError(f'unsupported mapped weight shape: {mapped_name}')
            if mapped_name in seen:
                raise ValueError('duplicate mapped tensor')
            seen.add(mapped_name)
            tensor = tensor.astype(definition.precision)
            converted = quantize_weight(mapped_name, tensor, quantizable)
            mx.eval(*converted.values())
            for key, value in converted.items():
                if value.nbytes > SHARD_BYTES:
                    raise ValueError('single tensor exceeds transport limit')
                if byte_count + value.nbytes > SHARD_BYTES:
                    flush()
                shard[key] = value
                byte_count += value.nbytes
            del converted, tensor
        del raw
    for name, value in generated_buffers(definition.name, parameters, seen).items():
        if byte_count + value.nbytes > SHARD_BYTES:
            flush()
        shard[name] = value
        byte_count += value.nbytes
        seen.add(name)
    if set(expected) != seen:
        raise ValueError(f'model parameters not supplied: {sorted(set(expected) - seen)}')
    flush()
    (target / 'model.safetensors.index.json').write_text(json.dumps(
        {'metadata': metadata, 'weight_map': weight_map}, indent=2))
    print(json.dumps({'component': definition.name, 'tensors': len(weight_map), 'shards': shard_index}), flush=True)


def convert(source, destination):
    os.umask(0o077)
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1')
    for name, version in {'mflux': '0.21.0', 'mlx': '0.32.2'}.items():
        if importlib.metadata.version(name) != version:
            raise ValueError('converter runtime revision mismatch')
    import mlx.core as mx
    from mflux.models.common.config.model_config import ModelConfig
    from mflux.models.flux2.model.flux2_transformer.transformer import Flux2Transformer
    from mflux.models.flux2.model.flux2_text_encoder.qwen3_text_encoder import Qwen3TextEncoder
    from mflux.models.flux2.weights.flux2_weight_definition import Flux2KleinWeightDefinition
    mx.set_cache_limit(1 << 30)
    source = Path(source).resolve()
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('output already exists')
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.klein-conversion-', dir=destination.parent))
    config = ModelConfig.flux2_klein_4b()
    constructors = {'transformer': lambda: Flux2Transformer(**config.transformer_overrides),
                    'text_encoder': lambda: Qwen3TextEncoder(**config.text_encoder_overrides)}
    try:
        for definition in Flux2KleinWeightDefinition.get_components():
            if definition.name == 'vae':
                # Preserve original VAE weights; no quantization or rewritten metadata.
                shutil.copytree(source / 'vae', staging / 'vae')
                continue
            model = constructors[definition.name]()
            convert_component(source, staging, definition, model)
            del model
            gc.collect()
            mx.clear_cache()
        shutil.copytree(source / 'tokenizer', staging / 'tokenizer')
        for name in ('LICENSE.md', 'README.md'):
            shutil.copyfile(source / name, staging / name)
        files = []
        for path in sorted(staging.rglob('*')):
            if path.is_file():
                digest = hashlib.sha256()
                with path.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(1 << 20), b''):
                        digest.update(chunk)
                files.append({'path': str(path.relative_to(staging)), 'size': path.stat().st_size,
                              'sha256': digest.hexdigest()})
        provenance = {'source': 'black-forest-labs/FLUX.2-klein-4B', 'revision': REVISION,
                      'license': 'Apache-2.0', 'mflux': '0.21.0', 'mlx': '0.32.2',
                      'bits': 4, 'group_size': 64, 'vae': 'unchanged',
                      'files': files, 'total_bytes': sum(f['size'] for f in files),
                      'mlx_peak_bytes': mx.get_peak_memory(), 'accepted_profiles': []}
        (staging / 'conversion.json').write_text(json.dumps(provenance, indent=2))
        staging.rename(destination)
        print(json.dumps({'event': 'converted', 'total_bytes': provenance['total_bytes'],
                          'mlx_peak_bytes': provenance['mlx_peak_bytes']}), flush=True)
    except BaseException:
        shutil.rmtree(staging)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('destination')
    args = parser.parse_args()
    convert(args.source, args.destination)
