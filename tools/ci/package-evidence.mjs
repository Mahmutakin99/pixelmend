#!/usr/bin/env node
/** Deterministic, dependency-free release evidence for CI package artifacts. */
import {copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync, openSync, readSync, closeSync, readdirSync, lstatSync, readlinkSync} from 'node:fs';
import {basename, dirname, join, resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';

const root = resolve(import.meta.dirname, '../..');
export const sha256 = file => {
  const hash=createHash('sha256'),buffer=Buffer.alloc(1024**2),fd=openSync(file,'r');
  try{let count;while((count=readSync(fd,buffer,0,buffer.length,null))>0)hash.update(buffer.subarray(0,count));}
  finally{closeSync(fd);}return hash.digest('hex');
};
const bundleHash = folder => {
 const hash=createHash('sha256');
 const visit=(directory,prefix='')=>{
  for(const name of readdirSync(directory).sort()){
   const file=join(directory,name),relative=prefix+name,info=lstatSync(file);
   if(info.isSymbolicLink())hash.update(JSON.stringify(['symlink',relative,readlinkSync(file)])+'\n');
   else if(info.isDirectory())visit(file,relative+'/');
   else if(info.isFile())hash.update(JSON.stringify(['file',relative,info.mode&0o777,info.size,sha256(file)])+'\n');
   else throw new Error('Unexpected runtime bundle file type');
  }
 };visit(folder);return hash.digest('hex');
};
export const jobPath = (file, cwd = process.cwd()) => resolve(cwd, file);
const value = flag => { const index = process.argv.indexOf(flag); return index < 0 ? undefined : process.argv[index + 1]; };
const command = (program, args) => { try { return execFileSync(program, args, {cwd:root, encoding:'utf8', stdio:['ignore', 'pipe', 'ignore']}).trim(); } catch { return 'unavailable'; } };
export function artifactName({version, os, arch, format}) { return `pixelmend-${version}-${os}-${arch}-${format}`; }
export function buildManifest({os, arch, generativeRuntime}) {
  const desktop = join(root, 'apps/desktop/package.json');
  const locks = ['apps/desktop/pnpm-lock.yaml', 'engine/uv.lock', 'engine/generative-runtime/uv.lock'];
  const catalogFile=join(root,'engine/src/pixelmend_engine/generative_catalog.json');
  const catalog=JSON.parse(readFileSync(catalogFile));
  return {
    commit: process.env.GITHUB_SHA || command('git', ['rev-parse', 'HEAD']),
    source_dirty: command('git',['status','--porcelain','--untracked-files=no'])!=='',
    version: JSON.parse(readFileSync(desktop)).version,
    os, arch,
    generative:{runtime_included:!!generativeRuntime,
      executable_sha256:generativeRuntime?sha256(generativeRuntime):null,
      bundle_sha256:generativeRuntime?bundleHash(dirname(generativeRuntime)):null,
      versions:{mflux:'0.21.0',mlx:'0.32.2','mlx-lm':'0.32.0'},
      catalog_sha256:sha256(catalogFile),
      packages:catalog.packages.map(p=>({id:p.id,source_revision:p.source_revision,
        package_revision:p.package_revision,runtime:p.runtime,accepted_profiles:p.accepted_profiles}))},
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
    const output = jobPath(value('--output')); const manifest = buildManifest({os:value('--os'), arch:value('--arch'),generativeRuntime:value('--generative-runtime')});
    mkdirSync(dirname(output), {recursive:true}); writeFileSync(output, `${JSON.stringify(manifest, null, 2)}\n`); return;
  }
  if (action === 'stage') {
    const packageFile = jobPath(value('--package')); const format = value('--format'); const os = value('--os'); const arch = value('--arch');
    const version = JSON.parse(readFileSync(join(root, 'apps/desktop/package.json'))).version;
    const name = artifactName({version, os, arch, format}); const output = join(jobPath(value('--output')), name);
    const manifest = jobPath(value('--manifest')); const nodeSbom = jobPath(value('--node-sbom')); const pythonSbom = jobPath(value('--python-sbom'));
    if (![packageFile, manifest, nodeSbom, pythonSbom].every(existsSync)) throw new Error('package evidence input is missing');
    mkdirSync(output, {recursive:true}); copyFileSync(packageFile, join(output, basename(packageFile)));
    copyFileSync(manifest, join(output, 'build-manifest.json')); copyFileSync(nodeSbom, join(output, 'sbom-node.cdx.json')); copyFileSync(pythonSbom, join(output, 'sbom-python.cdx.json'));
    writeFileSync(join(output, `${basename(packageFile)}.sha256`), `${sha256(packageFile)}  ${basename(packageFile)}\n`);
    process.stdout.write(`${name}\n`); return;
  }
  throw new Error('usage: package-evidence.mjs manifest|stage');
}
if (process.argv[1] === import.meta.filename) main();
