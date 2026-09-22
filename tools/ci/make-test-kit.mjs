import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const output=path.resolve(process.argv[2] || path.join(root,'apps/desktop/out.noindex/test-kit'));
fs.mkdirSync(output,{recursive:true});
const shell=fs.readFileSync(path.join(root,'tools/diagnostics/PixelMend-Test.sh'));
for(const name of ['PixelMend-Test.sh','PixelMend-Test.command'])fs.writeFileSync(path.join(output,name),shell,{mode:0o755});
const powershell=fs.readFileSync(path.join(root,'tools/diagnostics/PixelMend-Test.ps1'),'utf8');
// EncodedCommand avoids cmd.exe interpreting Unicode paths or PowerShell quoting.
const encoded=Buffer.from(powershell,'utf16le').toString('base64');
fs.writeFileSync(path.join(output,'PixelMend-Test.cmd'),`@echo off\r\nsetlocal DisableDelayedExpansion\r\nset "PIXELMEND_TEST_APP=%~1"\r\npowershell.exe -NoProfile -EncodedCommand ${encoded}\r\nexit /b %errorlevel%\r\n`);
fs.copyFileSync(path.join(root,'tools/diagnostics/README.md'),path.join(output,'ONCE-OKUYUN.md'));
console.log(output);
