#!/usr/bin/env node
/** Prepare an isolated Mac alpha. Never publishes or installs the application. */
import {existsSync,mkdirSync,readFileSync,writeFileSync} from 'node:fs';
import path from 'node:path';import {spawnSync} from 'node:child_process';
import {buildManifest,sha256} from '../ci/package-evidence.mjs';
import {notarizeApp,notarizeDmg} from './signing-workflow.mjs';
const root=path.resolve(import.meta.dirname,'../..'),desktop=path.join(root,'apps/desktop');
const unsigned=process.argv.includes('--unsigned');
if(process.platform!=='darwin'||process.arch!=='arm64')throw new Error('Apple Silicon Mac required');
const runtime=path.join(root,'.local-notes/generative/dist/pixelmend-generative-runtime/pixelmend-generative-runtime');
if(!existsSync(runtime))throw new Error('Build the locked standalone runtime first; see engine/generative-runtime/README.md');
if(!unsigned&&!process.env.CSC_NAME)throw new Error('Set CSC_NAME to the installed Developer ID Application identity. --unsigned prepares local review artifacts only.');
if(!unsigned&&!process.env.PIXELMEND_NOTARY_PROFILE)throw new Error('Set PIXELMEND_NOTARY_PROFILE to an existing notarytool Keychain profile. No credentials are read into logs.');
const run=(command,args,options={})=>{
 const env={...process.env,CSC_IDENTITY_AUTO_DISCOVERY:unsigned?'false':'true'};
 if(unsigned){delete env.CSC_NAME;delete env.CSC_LINK;delete env.CSC_KEY_PASSWORD;}
 const result=spawnSync(command,args,{cwd:options.cwd||desktop,stdio:options.capture?['ignore','pipe','inherit']:'inherit',encoding:'utf8',env});
 if(result.error)throw result.error;if(result.status!==0)throw new Error(`${path.basename(command)} failed (${result.status})`);return result.stdout;
};
run(path.join(root,'engine/generative-runtime/.venv/bin/python'),[path.join(root,'tools/generative/native-audit.py'),path.dirname(runtime)],{capture:true});
run(path.join(root,'engine/.venv/bin/python'),['-m','PyInstaller','--noconfirm','pixelmend-engine.spec'],{cwd:path.join(root,'engine')});
run(process.execPath,[path.join(desktop,'node_modules/typescript/bin/tsc'),'--noEmit']);
run(process.execPath,[path.join(desktop,'node_modules/vite/bin/vite.js'),'build']);
run(path.join(root,'engine/generative-runtime/.venv/bin/python'),[path.join(root,'tools/generative/runtime-licenses.py'),path.dirname(runtime)]);
const builder=path.join(desktop,'node_modules/electron-builder/cli.js');
const config=path.join(root,'tools/generative/electron-builder.cjs');
run(process.execPath,[builder,'--config',config,'--mac','--dir','--arm64','--publish','never']);
const version=JSON.parse(readFileSync(path.join(desktop,'package.json'))).version;
const output=path.join(root,'.local-notes/generative/releases',version);
const app=path.join(output,'mac-arm64/PixelMend.app');
if(!existsSync(app))throw new Error('Packaged app is missing');
const profile=process.env.PIXELMEND_NOTARY_PROFILE;
const nativeAudit=run(path.join(root,'engine/generative-runtime/.venv/bin/python'),[path.join(root,'tools/generative/native-audit.py'),app],{capture:true});
writeFileSync(path.join(output,'native-os-audit.json'),nativeAudit);
let appSubmission=null,dmgSubmission=null;
if(!unsigned)appSubmission=notarizeApp({app,archive:path.join(output,'notarization-input.zip'),profile,run});
// --prepackaged retains the signed and stapled app instead of signing it again.
run(process.execPath,[builder,'--config',config,'--prepackaged',app,'--mac','dmg','zip','--arm64','--publish','never']);
const packagedRuntime=path.join(app,'Contents/Resources/generative-runtime/pixelmend-generative-runtime');
writeFileSync(path.join(output,'build-manifest.json'),JSON.stringify(buildManifest({os:'macos',arch:'arm64',generativeRuntime:packagedRuntime}),null,2)+'\n');
for(const format of ['dmg','zip']){
 const artifact=path.join(output,`PixelMend-${version}-arm64.${format}`);
 if(!unsigned&&format==='dmg')dmgSubmission=notarizeDmg({artifact,profile,run});
 writeFileSync(artifact+'.sha256',`${sha256(artifact)}  ${path.basename(artifact)}\n`);
}
writeFileSync(path.join(output,'signing-status.json'),JSON.stringify({developer_id_signed:!unsigned,
 app_notarization_id:appSubmission,dmg_notarization_id:dmgSubmission,
 app_ticket_stapled:!unsigned,dmg_ticket_stapled:!unsigned,
 extracted_artifact_native_acceptance:'pending'},null,2)+'\n');
console.log(output);
