import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const args=process.argv.slice(2), platformIndex=args.indexOf('--platform');
const platform=platformIndex >= 0 ? args[platformIndex + 1] : process.platform === 'win32' ? 'windows' : process.platform === 'darwin' ? 'macos' : 'linux';
const outputArg=args.filter((_, index) => index !== platformIndex && index !== platformIndex + 1)[0];
const output=path.resolve(outputArg || path.join(root,'apps/desktop/out.noindex/test-kit'));
if (!['windows','linux','macos'].includes(platform)) throw new Error('Use --platform windows, linux, or macos.');
fs.mkdirSync(output,{recursive:true});
for (const name of ['PixelMend-Test.cmd','PixelMend-Test.sh','PixelMend-Test.command','URETKEN-TEST.md']) fs.rmSync(path.join(output,name),{force:true});
if (platform === 'windows') {
  const powershell=fs.readFileSync(path.join(root,'tools/diagnostics/PixelMend-Test.ps1'),'utf8'), encoded=Buffer.from(powershell,'utf16le').toString('base64');
  fs.writeFileSync(path.join(output,'PixelMend-Test.cmd'),`@echo off\r\nsetlocal DisableDelayedExpansion\r\nset "PIXELMEND_TEST_APP=%~1"\r\npowershell.exe -NoProfile -EncodedCommand ${encoded}\r\nexit /b %errorlevel%\r\n`);
  fs.copyFileSync(path.join(root,'tools/diagnostics/README-windows.md'),path.join(output,'ONCE-OKUYUN.md'));
} else if (platform === 'linux') {
  fs.copyFileSync(path.join(root,'tools/diagnostics/PixelMend-Test.sh'),path.join(output,'PixelMend-Test.sh')); fs.chmodSync(path.join(output,'PixelMend-Test.sh'),0o755);
  fs.copyFileSync(path.join(root,'tools/diagnostics/README-linux.md'),path.join(output,'ONCE-OKUYUN.md'));
} else {
  fs.copyFileSync(path.join(root,'tools/diagnostics/PixelMend-Test.sh'),path.join(output,'PixelMend-Test.command')); fs.chmodSync(path.join(output,'PixelMend-Test.command'),0o755);
  fs.copyFileSync(path.join(root,'tools/diagnostics/README-macos.md'),path.join(output,'ONCE-OKUYUN.md'));
  fs.copyFileSync(path.join(root,'tools/diagnostics/URETKEN-TEST.md'),path.join(output,'URETKEN-TEST.md'));
}
console.log(output);
