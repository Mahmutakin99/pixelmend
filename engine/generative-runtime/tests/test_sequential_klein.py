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

    def test_denoise_only_decoder_replaces_vae_after_reference_evaluation_before_load(self):
        module=self.module();model=SimpleNamespace(text_encoder=None,vae=None,transformer=None)
        decoder=SimpleNamespace(decode_packed_latents=lambda *args:None)
        events=[]
        def load(name):
            if name=='transformer':self.assertIs(model.vae,decoder)
            events.append(('load',name));return name
        def evaluate(*values):
            if values==('references',):self.assertEqual(model.vae,'vae')
            events.append(('eval',values))
        phases=module.ComponentPhases(model,load,evaluate,lambda:events.append(('clear',)))
        phases.vae_after_conditioning=decoder
        phases.initialize();phases.finish_prompt(('prompt',));phases.call_before_loop(latents='noise')
        phases.start_prediction(('references',))
        self.assertIs(model.vae,decoder)
        self.assertLess(events.index(('eval',('references',))),events.index(('load','transformer')))
        phases.start_prediction(('references',))
        self.assertEqual(events.count(('load','transformer')),1)

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

class ProbeTests(unittest.TestCase):
    def test_loading_probe_materializes_and_releases_each_component_before_next(self):
        import weakref
        module=SequentialTests().module();refs=[];seen=[]
        class Component:pass
        def load(name):
            self.assertTrue(all(ref() is None for ref in refs))
            value=Component();refs.append(weakref.ref(value));seen.append(name);return value
        def evaluate(value):self.assertIs(refs[-1](),value)
        module.probe_components(load,evaluate,lambda:None)
        self.assertEqual(seen,['text_encoder','vae','transformer'])
        self.assertTrue(all(ref() is None for ref in refs))
