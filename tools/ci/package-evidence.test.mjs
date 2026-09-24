import test from 'node:test';
import assert from 'node:assert/strict';
import {resolve} from 'node:path';
import {artifactName, buildManifest, jobPath, sha256} from './package-evidence.mjs';

test('artifact names are stable and include every target dimension', () => {
  assert.equal(artifactName({version:'1.0.0-rc.2', os:'macos', arch:'arm64', format:'dmg'}), 'pixelmend-1.0.0-rc.2-macos-arm64-dmg');
});
test('manifest fingerprints both locked dependency graphs', () => {
  const manifest = buildManifest({os:'linux', arch:'x64'});
  assert.equal(manifest.version, '1.0.0-rc.2');
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
