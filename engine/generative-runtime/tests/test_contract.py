import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

spec = importlib.util.spec_from_file_location('runtime', Path(__file__).parents[1] / 'runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class ContractTests(unittest.TestCase):
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
