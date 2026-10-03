import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdir, mkdtemp, realpath, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { detectProjectRoot, ProjectDetectionError } from '../../dist/repo/detect.js';

async function fixture(t) {
  const root = await mkdtemp(join(tmpdir(), 'plex root café with spaces '));
  t.after(async () => { await rm(root, { recursive: true, force: true }); });
  return realpath(root);
}

function gitInit(directory, extra = []) {
  execFileSync('git', ['init', '--quiet', ...extra, directory], { windowsHide: true, timeout: 5_000 });
}

test('nested Git working directory resolves to the repository top level', async t => {
  const root = await fixture(t);
  gitInit(root);
  const nested = join(root, 'src', 'pages');
  await mkdir(nested, { recursive: true });
  assert.deepEqual(await detectProjectRoot({ cwd: nested }), {
    root, source: 'git', selection: 'git', gitRoot: root,
  });
});

test('inherited Git location overrides do not redirect project detection', async t => {
  const root = await fixture(t);
  const project = join(root, 'selected');
  const other = join(root, 'other');
  await mkdir(project);
  await mkdir(other);
  gitInit(project);
  gitInit(other);
  const moduleUrl = new URL('../../dist/repo/detect.js', import.meta.url).href;
  const script = `import { detectProjectRoot } from ${JSON.stringify(moduleUrl)};
    console.log(JSON.stringify(await detectProjectRoot({ cwd: process.argv[1] })));`;
  const output = execFileSync(process.execPath, ['--input-type=module', '-e', script, project], {
    encoding: 'utf8', windowsHide: true, timeout: 10_000,
    env: { ...process.env, GIT_DIR: join(other, '.git'), GIT_WORK_TREE: other },
  });
  assert.equal(JSON.parse(output).root, project);
});

test('explicit relative directory remains the boundary inside a larger Git repo', async t => {
  const root = await fixture(t);
  gitInit(root);
  const selected = join(root, 'fixtures', 'web project');
  await mkdir(selected, { recursive: true });
  assert.deepEqual(await detectProjectRoot({ cwd: root, repo: 'fixtures/web project' }), {
    root: selected, source: 'git', selection: 'explicit', gitRoot: root,
  });
});

test('explicit absolute directory overrides an unrelated current Git repo', async t => {
  const temporary = await fixture(t);
  const repo = join(temporary, 'repo');
  const selected = join(temporary, 'other project');
  await mkdir(repo);
  await mkdir(selected);
  gitInit(repo);
  assert.deepEqual(await detectProjectRoot({ cwd: repo, repo: selected }), {
    root: selected, source: 'directory', selection: 'explicit',
  });
});

test('non-Git detection uses the working directory without searching project markers above it', async t => {
  const root = await fixture(t);
  const nested = join(root, 'nested');
  await mkdir(nested);
  await writeFile(join(root, 'package.json'), '{}');
  assert.deepEqual(await detectProjectRoot({ cwd: nested }), {
    root: nested, source: 'directory', selection: 'cwd',
  });
});

test('invalid explicit paths fail without falling back to current repo', async t => {
  const root = await fixture(t);
  gitInit(root);
  await writeFile(join(root, 'index.html'), '<title>Example</title>');
  for (const repo of ['', '   ', 'missing', 'index.html']) {
    await assert.rejects(detectProjectRoot({ cwd: root, repo }), ProjectDetectionError);
  }
  await assert.rejects(detectProjectRoot({ cwd: 'relative' }), ProjectDetectionError);
  await assert.rejects(detectProjectRoot({ cwd: join(root, 'missing') }), ProjectDetectionError);
});

test('Git metadata stored in a separate directory is supported', async t => {
  const root = await fixture(t);
  const project = join(root, 'project');
  const metadata = join(root, 'metadata');
  gitInit(project, [`--separate-git-dir=${metadata}`]);
  const nested = join(project, 'nested');
  await mkdir(nested);
  assert.equal((await detectProjectRoot({ cwd: nested })).root, project);
});

test('corrupt Git markers and bare repos stop instead of falling back', async t => {
  const root = await fixture(t);
  const broken = join(root, 'broken');
  const bare = join(root, 'bare');
  await mkdir(broken);
  await mkdir(join(broken, '.git'));
  gitInit(bare, ['--bare']);
  await assert.rejects(detectProjectRoot({ cwd: broken }), ProjectDetectionError);
  await assert.rejects(detectProjectRoot({ cwd: bare }), ProjectDetectionError);
});

test('missing Git is a documented directory fallback', async t => {
  const root = await fixture(t);
  const detected = await detectProjectRoot({ cwd: root }, async () => ({ status: 'unavailable' }));
  assert.equal(detected.root, root);
  assert.equal(detected.source, 'directory');
  assert.match(detected.note, /Git is unavailable/);
});

test('malformed or unrelated Git roots are rejected', async t => {
  const root = await fixture(t);
  const selected = join(root, 'selected');
  const unrelated = join(root, 'unrelated');
  await mkdir(selected);
  await mkdir(unrelated);
  for (const gitRoot of ['relative', unrelated]) {
    await assert.rejects(detectProjectRoot({ cwd: selected }, async () => ({ status: 'found', root: gitRoot })), ProjectDetectionError);
  }
});
