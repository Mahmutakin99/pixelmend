import test from 'node:test';import assert from 'node:assert/strict';import {spawnSync} from 'node:child_process';import path from 'node:path';
const run=source=>spawnSync('python3',['-c',source],{encoding:'utf8',cwd:path.resolve(import.meta.dirname,'../..')});
test('distribution audit rejects a native dependency requiring macOS 26.2',()=>{
 const result=run(`import importlib.util,struct\ns=importlib.util.spec_from_file_location('audit','tools/generative/native-audit.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nh=struct.pack('<8I',0xfeedfacf,0x100000c,0,6,1,24,0,0)\nc=struct.pack('<6I',0x32,24,1,(26<<16)|(2<<8),0,0)\nassert m.native_minimums(h+c)==[(26,2,0)]\ntry:m.require_supported(h+c,(15,0,0))\nexcept ValueError:pass\nelse:raise AssertionError('incompatible dylib was accepted')`);
 assert.equal(result.status,0,result.stderr);
});
test('distribution audit accepts macOS 15 native dependencies and ignores data files',()=>{
 const result=run(`import importlib.util,struct\ns=importlib.util.spec_from_file_location('audit','tools/generative/native-audit.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nh=struct.pack('<8I',0xfeedfacf,0x100000c,0,6,1,24,0,0)\nc=struct.pack('<6I',0x32,24,1,15<<16,0,0)\nm.require_supported(h+c,(15,0,0))\nassert m.native_minimums(b'not a native file')==[]`);
 assert.equal(result.status,0,result.stderr);
});
