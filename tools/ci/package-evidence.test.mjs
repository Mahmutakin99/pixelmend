import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const requireReadPackage=()=>readFileSync(new URL('../../apps/desktop/package.json',import.meta.url),'utf8');
import {resolve} from 'node:path';
import {artifactName, buildManifest, jobPath, sha256} from './package-evidence.mjs';

test('artifact names are stable and include every target dimension', () => {
  assert.equal(artifactName({version:'1.0.0-rc.2', os:'macos', arch:'arm64', format:'dmg'}), 'pixelmend-1.0.0-rc.2-macos-arm64-dmg');
});
test('manifest fingerprints both locked dependency graphs', () => {
  const manifest = buildManifest({os:'linux', arch:'x64'});
  assert.equal(manifest.version, JSON.parse(requireReadPackage()).version);
  assert.match(manifest.lock_sha256['apps/desktop/pnpm-lock.yaml'], /^[a-f0-9]{64}$/);
  assert.match(manifest.lock_sha256['engine/uv.lock'], /^[a-f0-9]{64}$/);
});
test('checksum output is SHA-256 and stable', () => {
  const file = new URL('./package-evidence.test.mjs', import.meta.url);
  assert.match(sha256(file), /^[a-f0-9]{64}$/);
  assert.equal(sha256(file), sha256(file));
});
test('package job paths resolve from the package working directory', () => {
  assert.equal(
    jobPath('out.noindex/PixelMend.dmg', '/workspace/apps/desktop'),
    resolve('/workspace/apps/desktop', 'out.noindex/PixelMend.dmg'),
  );
});

test('manifest binds the isolated runtime and immutable generative packages without enabling unaccepted profiles',()=>{
 const manifest=buildManifest({os:'macos',arch:'arm64'});
 assert.match(manifest.lock_sha256['engine/generative-runtime/uv.lock'],/^[a-f0-9]{64}$/);
 assert.match(manifest.generative.catalog_sha256,/^[a-f0-9]{64}$/);
 assert.equal(manifest.generative.runtime_included,false);
 assert.deepEqual(manifest.generative.versions,{mflux:'0.21.0',mlx:'0.32.2','mlx-lm':'0.32.0'});
 for(const p of manifest.generative.packages){assert.match(p.source_revision,/^[a-f0-9]{40}$/);assert.match(p.package_revision,/^[a-f0-9]{40}$/);assert.deepEqual(p.accepted_profiles,[]);}
});

test('manifest fingerprints native runtime siblings as well as its executable',async()=>{
 const fs=await import('node:fs');const os=await import('node:os');const path=await import('node:path');
 const folder=fs.mkdtempSync(path.join(os.tmpdir(),'pixelmend-runtime-hash-'));
 try{
  const executable=path.join(folder,'runtime'),native=path.join(folder,'libmlx.dylib');
  fs.writeFileSync(executable,'executable');fs.writeFileSync(native,'first native build');
  const first=buildManifest({os:'macos',arch:'arm64',generativeRuntime:executable});
  fs.writeFileSync(native,'second native build');
  const second=buildManifest({os:'macos',arch:'arm64',generativeRuntime:executable});
  assert.equal(first.generative.executable_sha256,second.generative.executable_sha256);
  assert.match(first.generative.bundle_sha256,/^[a-f0-9]{64}$/);
  assert.notEqual(first.generative.bundle_sha256,second.generative.bundle_sha256);
 }finally{fs.rmSync(folder,{recursive:true,force:true});}
});
