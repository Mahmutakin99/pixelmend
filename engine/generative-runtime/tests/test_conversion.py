import importlib.util
import os
from pathlib import Path
import unittest

path = Path(__file__).parents[1] / 'convert_klein.py'
converter = None
if path.exists():
    spec = importlib.util.spec_from_file_location('convert_klein', path)
    converter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(converter)


@unittest.skipUnless(os.environ.get('PIXELMEND_TEST_MLX') == '1', 'explicit native MLX check')
class ConversionTests(unittest.TestCase):
    def test_only_native_derived_rotary_buffer_is_supplied(self):
        self.assertTrue(hasattr(converter, 'generated_buffers'))
        import mlx.core as mx
        parameters = {'rotary_emb.inv_freq': mx.array([1.0, 0.1]),
                      'missing_trainable.weight': mx.ones((64, 64))}
        self.assertEqual(set(converter.generated_buffers('text_encoder', parameters, set())),
                         {'rotary_emb.inv_freq'})
        self.assertEqual(converter.generated_buffers('transformer', parameters, set()), {})
        self.assertEqual(converter.generated_buffers('text_encoder', parameters,
                                                     {'rotary_emb.inv_freq'}), {})

    def test_streamed_linear_matches_native_quantization(self):
        self.assertIsNotNone(converter)
        import mlx.core as mx
        import mlx.nn as nn
        weight = mx.arange(64 * 128).reshape(64, 128).astype(mx.bfloat16) / 1000
        layer = nn.Linear(128, 64, bias=False)
        layer.update({'weight': weight})
        native = layer.to_quantized(group_size=64, bits=4)
        actual = converter.quantize_weight('linear.weight', weight, {'linear'})
        for name in ('weight', 'scales', 'biases'):
            self.assertTrue(bool(mx.array_equal(actual[f'linear.{name}'], getattr(native, name))))

    def test_norm_and_vae_weights_remain_unquantized(self):
        self.assertIsNotNone(converter)
        import mlx.core as mx
        for name, weight in [('norm.weight', mx.ones((128,))),
                             ('vae.linear.weight', mx.ones((64, 128)))]:
            actual = converter.quantize_weight(name, weight, set())
            self.assertEqual(set(actual), {name})
            self.assertTrue(bool(mx.array_equal(actual[name], weight)))


if __name__ == '__main__':
    unittest.main()
