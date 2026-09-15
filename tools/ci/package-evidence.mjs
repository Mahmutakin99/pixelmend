#!/usr/bin/env node
/** Deterministic, dependency-free release evidence for CI package artifacts. */
import {copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync} from 'node:fs';
import {basename, join, resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';

const root = resolve(import.meta.dirname, '../..');
export const sha256 = file => createHash('sha256').update(readFileSync(file)).digest('hex');
const value = flag => { const index = process.argv.indexOf(flag); return index < 0 ? undefined : process.argv[index + 1]; };
const command = (program, args) => { try { return execFileSync(program, args, {cwd:root, encoding:'utf8', stdio:['ignore', 'pipe', 'ignore']}).trim(); } catch { return 'unavailable'; } };
export function artifactName({version, os, arch, format}) { return `pixelmend-${version}-${os}-${arch}-${format}`; }
export function buildManifest({os, arch}) {
  const desktop = join(root, 'apps/desktop/package.json');
  const locks = ['apps/desktop/pnpm-lock.yaml', 'engine/uv.lock'];
  return {
    commit: process.env.GITHUB_SHA || command('git', ['rev-parse', 'HEAD']),
    version: JSON.parse(readFileSync(desktop)).version,
    os, arch,
    tools: {
      node: process.version, pnpm: command('pnpm', ['--version']), uv: command('uv', ['--version']),
      python: process.env.PIXELMEND_PYTHON_VERSION || command('uv', ['--directory', 'engine', 'run', 'python', '--version']),
    },
    lock_sha256: Object.fromEntries(locks.map(file => [file, sha256(join(root, file))])),
  };
}
function main() {
  const action = process.argv[2];
  if (action === 'manifest') {
    const output = value('--output'); const manifest = buildManifest({os:value('--os'), arch:value('--arch')});
    mkdirSync(resolve(root, output, '..'), {recursive:true}); writeFileSync(resolve(root, output), `${JSON.stringify(manifest, null, 2)}\n`); return;
  }
  if (action === 'stage') {
    const packageFile = resolve(root, value('--package')); const format = value('--format'); const os = value('--os'); const arch = value('--arch');
    const version = JSON.parse(readFileSync(join(root, 'apps/desktop/package.json'))).version;
    const name = artifactName({version, os, arch, format}); const output = resolve(root, value('--output'), name);
    const manifest = resolve(root, value('--manifest')); const nodeSbom = resolve(root, value('--node-sbom')); const pythonSbom = resolve(root, value('--python-sbom'));
    if (![packageFile, manifest, nodeSbom, pythonSbom].every(existsSync)) throw new Error('package evidence input is missing');
    mkdirSync(output, {recursive:true}); copyFileSync(packageFile, join(output, basename(packageFile)));
    copyFileSync(manifest, join(output, 'build-manifest.json')); copyFileSync(nodeSbom, join(output, 'sbom-node.cdx.json')); copyFileSync(pythonSbom, join(output, 'sbom-python.cdx.json'));
    writeFileSync(join(output, `${basename(packageFile)}.sha256`), `${sha256(packageFile)}  ${basename(packageFile)}\n`);
    process.stdout.write(`${name}\n`); return;
  }
  throw new Error('usage: package-evidence.mjs manifest|stage');
}
if (process.argv[1] === import.meta.filename) main();
