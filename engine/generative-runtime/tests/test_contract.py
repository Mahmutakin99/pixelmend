import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

spec = importlib.util.spec_from_file_location('runtime', Path(__file__).parents[1] / 'runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class ContractTests(unittest.TestCase):
    def test_supported_runtime_limits_only_its_own_unused_gpu_cache(self):
        from types import ModuleType,SimpleNamespace
        from unittest.mock import Mock,patch
        core=ModuleType('mlx.core');core.metal=SimpleNamespace(is_available=lambda:True)
        core.set_cache_limit=Mock();core.set_memory_limit=Mock();core.set_wired_limit=Mock()
        mlx=ModuleType('mlx');mlx.core=core
        with patch.dict(sys.modules,{'mlx':mlx,'mlx.core':core}), \
                patch('platform.machine',return_value='arm64'), \
                patch('platform.mac_ver',return_value=('15.0',(),'')), \
                patch.object(runtime.sys,'platform','darwin'), \
                patch.object(runtime.importlib.metadata,'version',side_effect=lambda name:runtime.VERSIONS[name]):
            self.assertIs(runtime.check_runtime(),core)
        core.set_cache_limit.assert_called_once_with(256*1024**2)
        core.set_memory_limit.assert_not_called();core.set_wired_limit.assert_not_called()

    def test_one_shot_memory_saver_preserves_global_peak_and_never_forces_vae_tiling(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from unittest.mock import Mock
        factory=Mock(return_value=object())
        model=SimpleNamespace(callbacks=SimpleNamespace(register=Mock()),tiling_config=None)
        self.assertTrue(hasattr(runtime,'configure_memory_saving'))
        with patch.dict(sys.modules,{'mflux.callbacks.instances.memory_saver':SimpleNamespace(MemorySaver=factory)}):
            runtime.configure_memory_saving(model)
        factory.assert_called_once_with(model=model,keep_transformer=False,cache_limit_bytes=None,num_seeds=1)
        model.callbacks.register.assert_called_once_with(factory.return_value)
        self.assertIsNone(model.tiling_config)

    def test_bounded_cancel_message_interrupts_without_echo(self):
        import io
        called=[]
        self.assertTrue(hasattr(runtime,'read_cancellation'))
        runtime.read_cancellation(io.BytesIO(b'{"event":"cancel"}\n'),lambda:called.append(True))
        self.assertEqual(called,[True])
        for data in [b'',b'{"event":"other"}\n',b'x'*65537,b'{"event":"cancel","prompt":"private"}\n']:
            runtime.read_cancellation(io.BytesIO(data),lambda:self.fail('invalid control message'))

    def test_progress_counts_evaluated_native_steps(self):
        from types import SimpleNamespace
        self.assertTrue(hasattr(runtime,'StepProgress'))
        events=[];original=runtime.emit
        try:
            runtime.emit=events.append
            callback=runtime.StepProgress(lambda value:events.append('evaluated'))
            callback.call_in_loop(t=1,latents=object(),config=SimpleNamespace(num_inference_steps=4))
            self.assertEqual(events,['evaluated',{'event':'progress','completed':2,'total':4}])
        finally:runtime.emit=original

    def test_image_limit_includes_native_tokenizer_special_tokens(self):
        from types import SimpleNamespace
        class Tokenizer:
            def apply_chat_template(self, messages, **kwargs):
                self.assert_format = kwargs
                return messages[0]['content']
            def __call__(self, text, **kwargs):
                self.assert_tokens = kwargs
                return {'input_ids': list(range(len(text) + 2))}
        tokenizer = Tokenizer()
        wrapper = SimpleNamespace(tokenizer=tokenizer, add_special_tokens=True,
                                  chat_template_kwargs={'enable_thinking': False}, max_length=512)
        self.assertTrue(hasattr(runtime, 'validate_image_prompt'))
        runtime.validate_image_prompt(wrapper, 'x' * 510)
        with self.assertRaisesRegex(ValueError, 'prompt_token_limit'):
            runtime.validate_image_prompt(wrapper, 'x' * 511)
        self.assertFalse(tokenizer.assert_format['tokenize'])
        self.assertFalse(tokenizer.assert_tokens['truncation'])
        self.assertTrue(tokenizer.assert_tokens['add_special_tokens'])

    @unittest.skipUnless(os.environ.get('PIXELMEND_TEST_GENERATIVE_EXECUTABLE')
                         and os.environ.get('PIXELMEND_TEST_TRANSLATION_MODEL'),
                         'explicit packaged translation acceptance')
    def test_packaged_translation_has_one_result_and_no_helper_protocol_errors(self):
        result = subprocess.run(
            [os.environ['PIXELMEND_TEST_GENERATIVE_EXECUTABLE']],
            input=json.dumps({'operation': 'translate',
                              'model_dir': os.environ['PIXELMEND_TEST_TRANSLATION_MODEL'],
                              'prompt': 'Bir kedi ekle.'}) + '\n',
            text=True, capture_output=True, timeout=45,
        )
        self.assertEqual(result.returncode, 0)
        events = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([event['event'] for event in events], ['stage', 'result'])
        self.assertEqual(events[-1]['english'], 'Add a cat.')
        self.assertEqual(result.stderr, '')

    def test_translation_rejects_truncated_or_echoed_output(self):
        self.assertTrue(hasattr(runtime, 'validate_translation_completion'))
        self.assertEqual(runtime.validate_translation_completion(
            [42, 0], 0, 'Add a cat.', 'Bir kedi ekle.'), 'Add a cat.')
        for ids, text in [([42, 17], 'Add'), ([0], ''),
                          ([42, 0], 'Bir kedi ekle.'),
                          ([42, 0], '<think>cat</think>')]:
            with self.assertRaises(ValueError):
                runtime.validate_translation_completion(ids, 0, text, 'Bir kedi ekle.')

    def test_translation_source_tokens_are_never_silently_cut(self):
        self.assertTrue(hasattr(runtime, 'validate_translation_token_count'))
        runtime.validate_translation_token_count(512, 512)
        with self.assertRaisesRegex(ValueError, 'prompt_token_limit'):
            runtime.validate_translation_token_count(513, 512)

    def test_translated_text_uses_token_limit_not_user_character_limit(self):
        translated = 'An orange cat sitting on the couch. ' * 30
        self.assertGreater(len(translated), 1000)
        self.assertEqual(runtime.parse_translation(json.dumps({'english': translated})),
                         translated.strip())

    def test_prompt_limit_counts_unicode(self):
        self.assertEqual(runtime.validate_prompt('  yağmur  '), 'yağmur')
        self.assertEqual(len(runtime.validate_prompt('ğ' * 1000)), 1000)
        for value in ['', '  ', 'ğ' * 1001, None, 5]:
            with self.subTest(value=type(value)):
                with self.assertRaises(ValueError):
                    runtime.validate_prompt(value)

    def test_strict_translation_envelope(self):
        self.assertEqual(runtime.parse_translation('{"english":"Add two white cats."}'),
                         'Add two white cats.')
        for value in ['<think>reason</think>cat', 'Here is the translation: cat',
                      '{"english":""}', '{"english":"cat","reason":"extra"}',
                      '{"english":"cat"} trailing', '{"english":17}',
                      '{"english":"<think>cat</think>"}', '{"english":"cat","english":"dog"}']:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    runtime.parse_translation(value)

    def test_bounded_one_line_request(self):
        import io
        self.assertEqual(runtime.read_request(io.BytesIO(b'{"operation":"probe"}\n')),
                         {'operation': 'probe'})
        for value in [b'x' * 65537, b'[]\n', b'{"operation":"probe"', b'\xff\n']:
            with self.assertRaises(ValueError):
                runtime.read_request(io.BytesIO(value))

    def test_exact_seed_and_dimensions(self):
        self.assertEqual(runtime.validate_image_options({'seed': 0, 'width': 512, 'height': 512}),
                         (0, 512, 512))
        for changes in [{'seed': True}, {'seed': -1}, {'seed': 2**32},
                        {'width': 513}, {'height': 2048}, {'width': 512.0}]:
            with self.assertRaises(ValueError):
                runtime.validate_image_options({'seed': 3, 'width': 512, 'height': 512} | changes)

    def test_invalid_request_does_not_import_models_or_echo_content(self):
        private = 'PRIVATE synthetic content must not appear in diagnostics'
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parents[1] / 'runtime.py')],
            input=json.dumps({'operation': 'unknown', 'prompt': private}) + '\n',
            text=True, capture_output=True, timeout=5,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout), {'event': 'error', 'code': 'invalid_operation'})
        self.assertEqual(result.stderr, '')
        self.assertNotIn(private, result.stdout)


if __name__ == '__main__':
    unittest.main()
