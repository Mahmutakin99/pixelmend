import assert from 'node:assert/strict';
import {chmodSync, cpSync, existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {basename, dirname, join, resolve} from 'node:path';
import {spawnSync} from 'node:child_process';
import test from 'node:test';

const root = resolve(import.meta.dirname, '../..');
const launcher = join(root, 'tools/diagnostics/PixelMend-Test.sh');
const generator = join(root, 'tools/ci/make-test-kit.mjs');

function fixture() {
  const dir = mkdtempSync(join(tmpdir(), 'pixelmend-test-kit-'));
  const output = join(dir, 'reports');
  mkdirSync(output);
  const bin = join(dir, 'bin');
  mkdirSync(bin);
  writeFileSync(join(bin, 'uname'), '#!/bin/sh\necho Linux\n');
  chmodSync(join(bin, 'uname'), 0o755);
  return {bin, dir, output};
}

function executable(file, body = '#!/bin/sh\nexit 7\n') {
  writeFileSync(file, body);
  chmodSync(file, 0o755);
}

function runLauncher({args = [], bin, dir, input = '', output, env = {}}) {
  return spawnSync('sh', [launcher, ...args], {
    cwd: dir,
    encoding: 'utf8',
    input,
    env: {...process.env, ...env, PATH: `${bin}:${process.env.PATH}`, PIXELMEND_DIAGNOSTIC_OUTPUT: output},
  });
}

function startupReport(output) {
  const files = spawnSync('find', [output, '-name', 'PixelMend-Test-Baslangic-*.txt'], {encoding: 'utf8'}).stdout.trim().split('\n').filter(Boolean);
  assert.equal(files.length, 1);
  return readFileSync(files[0], 'utf8');
}

test('Linux launcher prefers its explicit application argument', () => {
  const f = fixture();
  try {
    const app = join(f.dir, 'explicit.AppImage');
    executable(app);
    const result = runLauncher({...f, args: [app]});
    assert.equal(result.status, 1);
    assert.match(startupReport(f.output), new RegExp(`Seçilen uygulama: ${app}`));
  } finally { rmSync(f.dir, {recursive: true, force: true}); }
});

test('Linux launcher uses PIXELMEND_TEST_APP before installed applications', () => {
  const f = fixture();
  try {
    const app = join(f.dir, 'environment.AppImage');
    executable(app);
    const result = runLauncher({...f, env: {PIXELMEND_TEST_APP: app}});
    assert.equal(result.status, 1);
    assert.match(startupReport(f.output), new RegExp(`Seçilen uygulama: ${app}`));
  } finally { rmSync(f.dir, {recursive: true, force: true}); }
});

test('Linux launcher finds an installed pixelmend command', () => {
  const f = fixture();
  try {
    const app = join(f.bin, 'pixelmend');
    executable(app);
    const result = runLauncher(f);
    assert.equal(result.status, 1);
    assert.match(startupReport(f.output), new RegExp(`Seçilen uygulama: ${app}`));
  } finally { rmSync(f.dir, {recursive: true, force: true}); }
});

test('Linux launcher finds exactly one AppImage next to its test kit', () => {
  const f = fixture();
  try {
    const kit = join(f.dir, 'test-kit');
    mkdirSync(kit);
    cpSync(launcher, join(kit, 'PixelMend-Test.sh'));
    const app = join(f.dir, 'PixelMend.AppImage');
    executable(app);
    const result = spawnSync('sh', [join(kit, 'PixelMend-Test.sh')], {cwd: f.dir, encoding: 'utf8', env: {...process.env, PATH: `${f.bin}:${process.env.PATH}`, PIXELMEND_DIAGNOSTIC_OUTPUT: f.output}});
    assert.equal(result.status, 1);
    assert.match(startupReport(f.output), new RegExp(`Seçilen uygulama: ${app}`));
  } finally { rmSync(f.dir, {recursive: true, force: true}); }
});

test('Linux launcher rejects multiple nearby AppImages instead of guessing', () => {
  const f = fixture();
  try {
    const kit = join(f.dir, 'test-kit');
    mkdirSync(kit);
    cpSync(launcher, join(kit, 'PixelMend-Test.sh'));
    executable(join(f.dir, 'one.AppImage'));
    executable(join(f.dir, 'two.AppImage'));
    const result = spawnSync('sh', [join(kit, 'PixelMend-Test.sh')], {cwd: f.dir, encoding: 'utf8', input: '\n', env: {...process.env, PATH: `${f.bin}:${process.env.PATH}`, PIXELMEND_DIAGNOSTIC_OUTPUT: f.output}});
    assert.equal(result.status, 1);
    assert.match(result.stderr, /Birden fazla AppImage/);
  } finally { rmSync(f.dir, {recursive: true, force: true}); }
});

test('Linux launcher reports a non-executable AppImage and chmod remedy', () => {
  const f = fixture();
  try {
    const app = join(f.dir, 'locked AppImage.AppImage');
    writeFileSync(app, '#!/bin/sh\nexit 0\n');
    const result = runLauncher({...f, args: [app], input: '\n'});
    assert.equal(result.status, 1);
    const report = startupReport(f.output);
    assert.match(report, new RegExp(`Seçilen uygulama: ${app}`));
    assert.match(report, /çalıştırılabilir değil/);
    assert.match(report, new RegExp(String.raw`chmod \+x -- '${app}'`));
  } finally { rmSync(f.dir, {recursive: true, force: true}); }
});

test('Linux launcher records a manually supplied application path with OS and exit code', () => {
  const f = fixture();
  try {
    const app = join(f.dir, 'manual AppImage');
    executable(app, '#!/bin/sh\nexit 23\n');
    const result = runLauncher({...f, input: `${app}\n`});
    assert.equal(result.status, 1);
    assert.match(startupReport(f.output), new RegExp(`Seçilen uygulama: ${app}\\nİşletim sistemi: Linux[\\s\\S]*Uygulama çıkış kodu: 23`));
  } finally { rmSync(f.dir, {recursive: true, force: true}); }
});

test('Linux launcher leaves a start report with application, OS, and exit code when no ZIP is made', () => {
  const f = fixture();
  try {
    const app = join(f.dir, 'crashes.AppImage');
    executable(app, '#!/bin/sh\nexit 23\n');
    const result = runLauncher({...f, args: [app]});
    assert.equal(result.status, 1);
    const report = startupReport(f.output);
    assert.match(report, new RegExp(`Seçilen uygulama: ${app}`));
    assert.match(report, /İşletim sistemi: Linux/);
    assert.match(report, /Uygulama çıkış kodu: 23/);
    assert.match(report, /ZIP raporu bulunamadı/);
  } finally { rmSync(f.dir, {recursive: true, force: true}); }
});

test('Linux launcher rejects a report directory without write permission', () => {
  const f = fixture();
  try {
    chmodSync(f.output, 0o555);
    const result = runLauncher({...f, input: '\n'});
    assert.equal(result.status, 1);
    assert.match(result.stderr, /Rapor klasörüne yazılamıyor/);
  } finally { chmodSync(f.output, 0o755); rmSync(f.dir, {recursive: true, force: true}); }
});

test('test-kit generator emits only the launcher and guide for its target platform', () => {
  const f = fixture();
  try {
    const windows = join(f.dir, 'windows');
    const linux = join(f.dir, 'linux');
    assert.equal(spawnSync('node', [generator, '--platform', 'windows', windows], {encoding: 'utf8'}).status, 0);
    assert.equal(spawnSync('node', [generator, '--platform', 'linux', linux], {encoding: 'utf8'}).status, 0);
    assert.ok(existsSync(join(windows, 'PixelMend-Test.cmd')));
    assert.ok(!existsSync(join(windows, 'PixelMend-Test.sh')));
    assert.ok(existsSync(join(linux, 'PixelMend-Test.sh')));
    assert.ok(!existsSync(join(linux, 'PixelMend-Test.cmd')));
    assert.match(readFileSync(join(windows, 'ONCE-OKUYUN.md'), 'utf8'), /# .*Windows/);
    assert.match(readFileSync(join(linux, 'ONCE-OKUYUN.md'), 'utf8'), /# .*Linux/);
  } finally { rmSync(f.dir, {recursive: true, force: true}); }
});

test('test-kit generator removes a previous platform launcher from the same output directory', () => {
  const f = fixture();
  try {
    const output = join(f.dir, 'test-kit');
    assert.equal(spawnSync('node', [generator, '--platform', 'windows', output], {encoding: 'utf8'}).status, 0);
    assert.equal(spawnSync('node', [generator, '--platform', 'linux', output], {encoding: 'utf8'}).status, 0);
    assert.ok(existsSync(join(output, 'PixelMend-Test.sh')));
    assert.ok(!existsSync(join(output, 'PixelMend-Test.cmd')));
    assert.ok(!existsSync(join(output, 'PixelMend-Test.command')));
  } finally { rmSync(f.dir, {recursive: true, force: true}); }
});
