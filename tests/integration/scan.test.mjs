import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { tmpdir } from 'node:os';
import { mkdir, mkdtemp, readFile, realpath, rm, rmdir, symlink, unlink, writeFile } from 'node:fs/promises';
import { detectProjectRoot } from '../../dist/repo/detect.js';
import { scanProject, RepositoryScanError, defaultScanLimits } from '../../dist/repo/scan.js';

async function fixture(t, git = false) {
  const root = await realpath(await mkdtemp(join(tmpdir(), 'plex scan café with spaces ')));
  t.after(async () => { await rm(root, { recursive: true, force: true }); });
  if (git) runGit(root, ['init', '--quiet']);
  return root;
}

function runGit(root, args) {
  return execFileSync('git', ['--no-optional-locks', '-c', 'core.autocrlf=false', '-C', root, ...args], {
    encoding: 'utf8', windowsHide: true, timeout: 5_000,
  });
}

async function file(root, path, content = 'const value = 1;\n') {
  const absolute = join(root, path);
  await mkdir(dirname(absolute), { recursive: true });
  await writeFile(absolute, content);
}

const directoryProject = root => ({ root, source: 'directory', selection: 'cwd' });
const paths = manifest => manifest.files.map(file => file.path);
const limitError = error => error instanceof RepositoryScanError && error.code === 'limit_exceeded';

test('directory enumeration returns supported source metadata in stable order', async t => {
  const root = await fixture(t);
  await file(root, 'z.js');
  await file(root, 'a/index.html', '<title>Example</title>\r\n');
  await file(root, 'a/style.CSS', 'body { margin: 0; }\n');
  await file(root, 'module.mjs');
  await file(root, 'module.cjs');
  for (const excluded of ['node_modules/dependency.js', 'dist/app.js', 'coverage/report.html',
    '.git/config.js', '.aws/secrets.js', '.env.js', 'bundle.min.js', 'style.min.css',
    'app.generated.js', 'app.js.map', 'README.md', 'image.png', 'app.ts']) {
    await file(root, excluded);
  }
  const scan = await scanProject(directoryProject(root));
  assert.deepEqual(paths(scan), ['a/index.html', 'a/style.CSS', 'module.cjs', 'module.mjs', 'z.js']);
  assert.deepEqual(scan.files[0], { path: 'a/index.html', extension: '.html', sizeBytes: Buffer.byteLength('<title>Example</title>\r\n') });
  assert.equal(scan.files[1].extension, '.css');
  assert.deepEqual(await scanProject(directoryProject(root)), scan);
});

test('nested ignore rules override parent file patterns but cannot traverse ignored directories', async t => {
  const root = await fixture(t);
  await file(root, '.gitignore', '*.js\nignored/\n/only-root.css\n');
  await file(root, 'app.js');
  await file(root, 'only-root.css');
  await file(root, 'nested/.gitignore', '!keep.js\nprivate.css\n');
  await file(root, 'nested/keep.js');
  await file(root, 'nested/drop.js');
  await file(root, 'nested/private.css');
  await file(root, 'nested/only-root.css');
  await file(root, 'ignored/.gitignore', '!*.js\n');
  await file(root, 'ignored/hidden.js');
  await file(root, 'index.html');
  assert.deepEqual(paths(await scanProject(directoryProject(root))), ['index.html', 'nested/keep.js', 'nested/only-root.css']);
});

test('Git lists tracked and untracked files, respects ignore rules, and skips missing tracked files', async t => {
  const root = await fixture(t, true);
  await file(root, 'tracked.js');
  await file(root, 'missing.js');
  await file(root, 'tracked.css');
  runGit(root, ['add', '--', 'tracked.js', 'missing.js', 'tracked.css']);
  await unlink(join(root, 'missing.js'));
  await file(root, '.gitignore', '*.css\nignored/\n');
  await file(root, '.git/info/exclude', 'local-only.js\n');
  await file(root, 'ignored/hidden.js');
  await file(root, 'local-only.js');
  await file(root, 'untracked.js');
  await file(root, 'untracked.css');
  const indexBefore = await readFile(join(root, '.git', 'index'));
  const project = await detectProjectRoot({ cwd: root });
  const scan = await scanProject(project);
  assert.deepEqual(paths(scan), ['tracked.css', 'tracked.js', 'untracked.js']);
  assert.deepEqual(await scanProject(project), scan);
  assert.deepEqual(await readFile(join(root, '.git', 'index')), indexBefore);
});

test('hard exclusions also apply to tracked dependencies and generated files', async t => {
  const root = await fixture(t, true);
  await file(root, 'node_modules/large.js', 'x'.repeat(defaultScanLimits.maxFileBytes + 1));
  await file(root, 'build/output.js');
  await file(root, 'app.min.js');
  await file(root, '.env.js');
  await file(root, 'app.js');
  runGit(root, ['add', '--', '.']);
  assert.deepEqual(paths(await scanProject(await detectProjectRoot({ cwd: root }))), ['app.js']);
});

test('Git enumeration remains within an explicit subdirectory boundary', async t => {
  const root = await fixture(t, true);
  await file(root, 'outside.js');
  await file(root, 'web/index.html', '<title>Example</title>');
  await file(root, 'web/nested/app.js');
  runGit(root, ['add', '--', 'outside.js', 'web/index.html']);
  const selected = await detectProjectRoot({ cwd: root, repo: 'web' });
  const scan = await scanProject(selected);
  assert.equal(scan.root, join(root, 'web'));
  assert.deepEqual(paths(scan), ['index.html', 'nested/app.js']);
});

test('Git enumeration skips submodule entries and nested repositories', async t => {
  const root = await fixture(t, true);
  await file(root, 'app.js');
  await file(root, 'module/hidden.js');
  runGit(join(root, 'module'), ['init', '--quiet']);
  runGit(root, ['update-index', '--add', '--cacheinfo', `160000,${'1'.repeat(40)},module`]);
  await file(root, 'untracked-repo/hidden.js');
  runGit(join(root, 'untracked-repo'), ['init', '--quiet']);
  assert.deepEqual(paths(await scanProject(await detectProjectRoot({ cwd: root }))), ['app.js']);
});

test('directory traversal skips nested Git projects', async t => {
  const root = await fixture(t);
  await file(root, 'app.js');
  await file(root, 'nested/hidden.js');
  await file(root, 'nested/.git', 'gitdir: elsewhere\n');
  assert.deepEqual(paths(await scanProject(directoryProject(root))), ['app.js']);
});

test('Git index modes exclude emulated symlinks and gitlinks even if they are ordinary files', async t => {
  const root = await fixture(t, true);
  await file(root, 'target.js');
  await file(root, 'link.js', 'target.js\n');
  await file(root, 'module.js', 'not a source file\n');
  const hash = execFileSync('git', ['-C', root, 'hash-object', '-w', '--stdin'], {
    encoding: 'utf8', input: 'target.js\n', windowsHide: true, timeout: 5_000,
  }).trim();
  runGit(root, ['update-index', '--add', '--cacheinfo', `120000,${hash},link.js`]);
  runGit(root, ['update-index', '--add', '--cacheinfo', `160000,${'1'.repeat(40)},module.js`]);
  assert.deepEqual(paths(await scanProject(await detectProjectRoot({ cwd: root }))), ['target.js']);
});

test('junctions or directory symlinks cannot expose outside files or create loops', async t => {
  const root = await fixture(t);
  const outside = join(root, 'outside');
  const project = join(root, 'project');
  await file(outside, 'secret.js', 'secret content');
  await file(project, 'app.js');
  const linked = join(project, 'external');
  const loop = join(project, 'loop');
  const linkType = process.platform === 'win32' ? 'junction' : 'dir';
  await symlink(outside, linked, linkType);
  await symlink(project, loop, linkType);
  try {
    assert.deepEqual(paths(await scanProject(directoryProject(project))), ['app.js']);
    assert.equal(await readFile(join(outside, 'secret.js'), 'utf8'), 'secret content');
  } finally {
    await unlink(linked);
    await unlink(loop);
  }
});

test('tracked paths whose parent became a junction or symlink are skipped', async t => {
  const root = await fixture(t);
  const project = join(root, 'project');
  const outside = join(root, 'outside');
  await file(project, 'nested/app.js');
  await file(project, 'safe.js');
  await file(outside, 'app.js', 'outside content');
  runGit(project, ['init', '--quiet']);
  runGit(project, ['add', '--', '.']);
  await unlink(join(project, 'nested', 'app.js'));
  await rmdir(join(project, 'nested'));
  const linked = join(project, 'nested');
  await symlink(outside, linked, process.platform === 'win32' ? 'junction' : 'dir');
  try {
    assert.deepEqual(paths(await scanProject(await detectProjectRoot({ cwd: project }))), ['safe.js']);
    assert.equal(await readFile(join(outside, 'app.js'), 'utf8'), 'outside content');
  } finally { await unlink(linked); }
});

test('file symlinks are excluded from both Git and directory manifests', async t => {
  const root = await fixture(t, true);
  await file(root, 'target.js');
  const linked = join(root, 'link.js');
  try { await symlink(join(root, 'target.js'), linked, 'file'); }
  catch (error) {
    if (process.platform === 'win32' && error.code === 'EPERM') {
      t.skip('File symlink creation requires Windows developer mode or elevated privileges.');
      return;
    }
    throw error;
  }
  try {
    assert.deepEqual(paths(await scanProject(directoryProject(root))), ['target.js']);
    // Git mode applies to untracked symlinks too; staging links is not required.
    assert.deepEqual(paths(await scanProject(await detectProjectRoot({ cwd: root }))), ['target.js']);
  } finally { await unlink(linked); }
});

test('NUL-containing binary impostors are excluded without loading whole source files', async t => {
  const root = await fixture(t);
  await file(root, 'binary.js', Buffer.from([1, 2, 0, 3]));
  await file(root, 'empty.css', '');
  await file(root, 'valid.js');
  assert.deepEqual(paths(await scanProject(directoryProject(root))), ['empty.css', 'valid.js']);
});

test('source count, file size, inspection, traversal, and depth limits fail without partial results', async t => {
  const root = await fixture(t);
  await file(root, 'a.js', '1234');
  await file(root, 'b.js', '1234');
  await file(root, 'nested/c.js', '1234');
  const project = directoryProject(root);
  for (const limit of [{ maxFiles: 2 }, { maxFileBytes: 3 }, { maxInspectionBytes: 3 },
    { maxEntries: 2 }, { maxDepth: 1 }]) {
    await assert.rejects(scanProject(project, limit), limitError);
  }
});

test('oversized or invalid ignore files stop non-Git scans', async t => {
  const root = await fixture(t);
  await file(root, 'app.js');
  await file(root, '.gitignore', 'x'.repeat(65_537));
  await assert.rejects(scanProject(directoryProject(root)), limitError);
  await file(root, '.gitignore', Buffer.from([0xff, 0xfe]));
  await assert.rejects(scanProject(directoryProject(root)), RepositoryScanError);
});

test('Git output and entry limits stop instead of falling back to traversal', async t => {
  const root = await fixture(t, true);
  await file(root, 'app.js');
  await file(root, 'other.js');
  const project = await detectProjectRoot({ cwd: root });
  await assert.rejects(scanProject(project, { maxGitOutputBytes: 1 }), limitError);
  await assert.rejects(scanProject(project, { maxEntries: 1 }), limitError);
});

test('invalid options, noncanonical roots, missing roots, and failed Git scans are rejected', async t => {
  const root = await fixture(t);
  for (const options of [{ maxFiles: 0 }, { maxFiles: 1001 }, { maxFileBytes: NaN },
    { maxDepth: 1.5 }, { maxEntries: undefined }, { unknown: 1 }, { toString: 1 }]) {
    await assert.rejects(scanProject(directoryProject(root), options), RepositoryScanError);
  }
  await assert.rejects(scanProject(directoryProject('relative')), RepositoryScanError);
  await assert.rejects(scanProject(directoryProject(join(root, 'missing'))), RepositoryScanError);
  await assert.rejects(scanProject({ root, source: 'git', selection: 'git' }), RepositoryScanError);
  const linked = `${root}-link`;
  await symlink(root, linked, process.platform === 'win32' ? 'junction' : 'dir');
  try { await assert.rejects(scanProject(directoryProject(linked)), RepositoryScanError); }
  finally { await unlink(linked); }
});

test('Git enumeration ignores inherited location overrides', async t => {
  const root = await fixture(t);
  const project = join(root, 'project');
  const other = join(root, 'other');
  await file(project, 'app.js');
  await file(other, 'other.js');
  runGit(project, ['init', '--quiet']);
  runGit(other, ['init', '--quiet']);
  const moduleUrl = new URL('../../dist/repo/scan.js', import.meta.url).href;
  const script = `import { scanProject } from ${JSON.stringify(moduleUrl)};
    console.log(JSON.stringify(await scanProject({ root: process.argv[1], source: 'git', selection: 'git' })));`;
  const output = execFileSync(process.execPath, ['--input-type=module', '-e', script, project], {
    encoding: 'utf8', windowsHide: true, timeout: 10_000,
    env: { ...process.env, GIT_DIR: join(other, '.git'), GIT_WORK_TREE: other },
  });
  assert.deepEqual(paths(JSON.parse(output)), ['app.js']);
});
