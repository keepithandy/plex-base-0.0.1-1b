import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { cp, mkdir, mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { hashFixture, webFixture } from '../helpers/web-fixture.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));
const cli = join(root, 'dist', 'cli', 'main.js');
const run = (args, cwd = root, entry = cli) => spawnSync(process.execPath, [entry, ...args], {
  cwd, encoding: 'utf8', timeout: 10_000,
});

test('help, short help, and no arguments show usage successfully', () => {
  for (const args of [['--help'], ['-h'], []]) {
    const result = run(args);
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /Usage:/);
    assert.match(result.stdout, /Implementation requests are not available yet/);
    assert.equal(result.stderr, '');
  }
});

test('CLI version matches package metadata', async () => {
  const metadata = JSON.parse(await readFile(join(root, 'package.json'), 'utf8'));
  const result = run(['--version']);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout.trim(), `Plex v${metadata.version}`);
  assert.equal(metadata.bin.plex, 'dist/cli/main.js');
});

test('unknown flags and malformed requests fail with usage exit code', () => {
  for (const args of [['--unknown'], ['first', 'second'], ['   ']]) {
    const result = run(args);
    assert.equal(result.status, 2);
    assert.match(result.stderr, /Plex:/);
  }
});

test('a task is not falsely reported as implemented and all three fixture files stay unchanged', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'plex project with spaces '));
  try {
    await cp(webFixture, directory, { recursive: true });
    const before = await hashFixture(directory);
    assert.deepEqual(before, await hashFixture());
    const result = run(['change the page title to DungeonDex'], directory);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /not available/);
    assert.deepEqual(await hashFixture(directory), before);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('compiled CLI runs when its own installation path contains spaces and Unicode', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'plex install with spaces '));
  try {
    const installation = join(directory, 'Plex café');
    await mkdir(installation);
    await cp(join(root, 'dist'), join(installation, 'dist'), { recursive: true });
    await cp(join(root, 'package.json'), join(installation, 'package.json'));
    const result = run(['--help'], directory, join(installation, 'dist', 'cli', 'main.js'));
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /Plex v0\.1\.0/);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('CLI --repo detects the explicit fixture boundary', () => {
  const result = run(['--repo', 'fixtures/simple-web-project', 'change the page title to DungeonDex']);
  assert.equal(result.status, 1);
  assert.ok(result.stdout.includes(`Repository: ${webFixture.replace(/[\\/]$/, '')}`));
  assert.match(result.stdout, /Detection: git; explicit/);
  assert.match(result.stdout, /Source files: 3/);
  for (const name of ['app.js', 'index.html', 'style.css']) assert.ok(result.stdout.includes(`  ${name} (`));
  assert.match(result.stdout, /Candidate ranking:/);
  assert.match(result.stdout, /1\. index\.html/);
  assert.match(result.stdout, /Selected: index\.html/);
  assert.match(result.stdout, /Context: 1 file; estimated input \d+\/3072 tokens/);
  assert.match(result.stdout, /Runtime token verification: pending/);
  assert.match(result.stdout, /Snapshot: index\.html; SHA-256 [a-f0-9]{64}/);
  assert.match(result.stderr, /not available/);
});

test('CLI reports insufficient context for ambiguous page titles', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'plex ambiguous pages '));
  try {
    await cp(webFixture, directory, { recursive: true });
    await cp(join(directory, 'index.html'), join(directory, 'about.html'));
    const before = await hashFixture(directory);
    const result = run(['change page title to DungeonDex'], directory);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /INSUFFICIENT CONTEXT/);
    assert.doesNotMatch(result.stdout, /Selected:/);
    assert.deepEqual(await hashFixture(directory), before);
  } finally { await rm(directory, { recursive: true, force: true }); }
});

test('CLI rejects a missing or empty explicit repo', () => {
  for (const repo of ['missing-project-directory', '']) {
    const result = run(['--repo', repo, 'change the title']);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /Plex:/);
    assert.doesNotMatch(result.stdout, /Repository:/);
  }
});
