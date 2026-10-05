"""Lazy block inputs must be released before the next full spatial block."""
import importlib.util
from pathlib import Path
import unittest
import weakref


class VAEMemoryTests(unittest.TestCase):
    def test_materialization_releases_previous_graph_without_replacing_output(self):
        spec=importlib.util.spec_from_file_location('vae_memory',Path(__file__).parents[1]/'vae_memory.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        class Tensor:
            def __init__(self,parents=()):self.parents=parents
        class Block:
            def __call__(self,value):return Tensor((value,))
        evaluated=[];cleared=[]
        def evaluate(value):
            evaluated.append(weakref.ref(value));value.parents=()
        module.materialize_block_calls((Block,),evaluate,lambda:cleared.append(True))
        source=Tensor();reference=weakref.ref(source)
        output=Block()(source);del source
        self.assertIsNone(reference(),'previous lazy graph retained at a block boundary')
        self.assertIs(evaluated[0](),output)
        self.assertEqual(cleared,[True])
        # Reconfiguration must not stack wrappers or repeatedly evaluate a block.
        module.materialize_block_calls((Block,),evaluate,lambda:cleared.append(True))
        Block()(output)
        self.assertEqual(len(evaluated),2)


if __name__=='__main__':unittest.main()
