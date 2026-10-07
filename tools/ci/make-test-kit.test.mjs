import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdtempSync,rmSync,existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';

test('test-kit preserves a positional output without a platform flag',()=>{
 const output=mkdtempSync(path.join(tmpdir(),'pixelmend kit '));
 try {
  const result=spawnSync(process.execPath,['tools/ci/make-test-kit.mjs',output],{encoding:'utf8'});
  assert.equal(result.status,0,result.stderr);
  assert.equal(result.stdout.trim(),output);
  assert.ok(existsSync(path.join(output,'ONCE-OKUYUN.md')));
 }finally{rmSync(output,{recursive:true,force:true});}
});
for(const before of [true,false])test(`test-kit accepts output ${before?'before':'after'} platform`,()=>{
 const output=mkdtempSync(path.join(tmpdir(),'pixelmend kit '));
 try {
  const args=before?[output,'--platform','macos']:['--platform','macos',output];
  const result=spawnSync(process.execPath,['tools/ci/make-test-kit.mjs',...args],{encoding:'utf8'});
  assert.equal(result.status,0,result.stderr);assert.equal(result.stdout.trim(),output);
 }finally{rmSync(output,{recursive:true,force:true});}
});
for(const args of [['--platform'],['--platform','invalid']])test(`test-kit rejects ${args.join(' ')}`,()=>{
 assert.notEqual(spawnSync(process.execPath,['tools/ci/make-test-kit.mjs',...args]).status,0);
});
