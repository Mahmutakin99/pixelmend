"""The prompt encoder and diffusion transformer must never coexist in a worker."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

class SequentialTests(unittest.TestCase):
    def module(self):
        spec=importlib.util.spec_from_file_location('sequential_klein',Path(__file__).parents[1]/'sequential_klein.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

    def test_prompt_is_materialized_before_encoder_release_and_transformer_load(self):
        module=self.module();events=[];model=SimpleNamespace(text_encoder=None,vae=None,transformer=None)
        def load(name):
            if name!='text_encoder':self.assertIsNone(model.text_encoder)
            events.append(('load',name));return name
        def evaluate(*arrays):events.append(('eval',arrays));self.assertIsNotNone(model.text_encoder if arrays==('prompt','ids') else model.vae)
        phases=module.ComponentPhases(model,load,evaluate,lambda:events.append(('clear',)))
        phases.initialize();self.assertIsNone(model.transformer);self.assertIsNone(model.vae)
        phases.finish_prompt(('prompt','ids',None,None))
        self.assertIsNone(model.text_encoder);self.assertEqual(model.vae,'vae');self.assertIsNone(model.transformer)
        phases.call_before_loop(latents='latents')
        self.assertIsNone(model.transformer, 'reference VAE graph must finish before diffusion weights load')
        phases.start_prediction(('reference','grid'))
        self.assertEqual(model.transformer,'transformer')
        self.assertLess(events.index(('eval',('prompt','ids'))),events.index(('clear',)))
        self.assertLess(events.index(('clear',)),events.index(('load','vae')))
        self.assertLess(events.index(('eval',('reference','grid'))),events.index(('load','transformer')))

    def test_early_denoise_and_encoder_reuse_are_rejected(self):
        module=self.module();model=SimpleNamespace(text_encoder=None,vae=None,transformer=None)
        phases=module.ComponentPhases(model,lambda name:name,lambda *args:None,lambda:None)
        phases.initialize()
        with self.assertRaisesRegex(RuntimeError,'prompt'):phases.call_before_loop(latents='noise')
        phases.finish_prompt(('encoded',None,None,None))
        with self.assertRaisesRegex(RuntimeError,'one-shot'):phases.finish_prompt(('encoded',))
        phases.call_before_loop(latents='noise');phases.start_prediction(('condition',));phases.start_prediction(('condition',))
        self.assertEqual(model.transformer,'transformer')

if __name__=='__main__':unittest.main()
