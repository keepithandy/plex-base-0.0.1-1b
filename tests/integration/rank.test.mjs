import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdir, mkdtemp, realpath, rm, symlink, unlink, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { tmpdir } from 'node:os';
import { scanProject } from '../../dist/repo/scan.js';
import { rankCandidates, RankingError } from '../../dist/repo/rank.js';
import { hashFixture, webFixture } from '../helpers/web-fixture.mjs';

async function project(t, entries) {
  const root = await realpath(await mkdtemp(join(tmpdir(), 'plex ranking café ')));
  t.after(async () => { await rm(root, { recursive: true, force: true }); });
  for (const [path, source] of Object.entries(entries)) {
    await mkdir(dirname(join(root, path)), { recursive: true });
    await writeFile(join(root, path), source);
  }
  return scanProject({ root, source: 'directory', selection: 'cwd' });
}
const page = '<!doctype html><html><head><title>Example</title></head><body></body></html>';

test('title fixture ranks index.html first with inspectable reasons and preserves every file', async () => {
  const before = await hashFixture();
  const manifest = await scanProject({ root: webFixture.replace(/[\\/]$/, ''), source: 'directory', selection: 'explicit' });
  const ranking = await rankCandidates('change the page title to DungeonDex', manifest);
  assert.equal(ranking.status, 'selected');
  assert.deepEqual(ranking.selectedPaths, ['index.html']);
  assert.equal(ranking.candidates[0].path, 'index.html');
  assert.ok(ranking.candidates[0].reasons.some(reason => reason.signal === 'titleElement'));
  for (const candidate of ranking.candidates) {
    assert.equal(candidate.score, candidate.reasons.reduce((sum, reason) => sum + reason.points, 0));
  }
  assert.deepEqual(await hashFixture(), before);
});

test('multiple HTML titles are ambiguous even when index.html scores highest', async t => {
  const manifest = await project(t, { 'index.html': page, 'about.html': page });
  const ranking = await rankCandidates('change page title to DungeonDex', manifest);
  assert.equal(ranking.candidates[0].path, 'index.html');
  assert.equal(ranking.status, 'insufficient_context');
  assert.deepEqual(ranking.selectedPaths, []);
  assert.equal((await rankCandidates('change about page title to DungeonDex', manifest)).selectedPaths[0], 'about.html');
});

test('explicit relative paths, filenames, Windows separators, and quoted spaces disambiguate', async t => {
  const manifest = await project(t, {
    'index.html': page, 'pages/about.html': page, 'pages/about page.html': page,
  });
  for (const task of ['change title in pages/about.html', 'change title in pages\\about.html', 'change title in about.html']) {
    assert.deepEqual((await rankCandidates(task, manifest)).selectedPaths, ['pages/about.html']);
  }
  assert.deepEqual((await rankCandidates('change title in "pages/about page.html"', manifest)).selectedPaths, ['pages/about page.html']);
});

test('missing names and duplicate basenames refuse selection', async t => {
  const manifest = await project(t, { 'one/index.html': page, 'two/index.html': page });
  for (const task of ['change title in missing.html', 'change title in index.html']) {
    assert.equal((await rankCandidates(task, manifest)).status, 'insufficient_context');
  }
  assert.deepEqual((await rankCandidates('change title in one/index.html', manifest)).selectedPaths, ['one/index.html']);
});

test('title tasks require an actual title signal, not just index.html or a commented title', async t => {
  const manifest = await project(t, { 'index.html': '<head><!-- <title>Fake</title> --></head>' });
  for (const task of ['change page title to DungeonDex', 'change title in index.html']) {
    assert.equal((await rankCandidates(task, manifest)).status, 'insufficient_context');
  }
});

test('CSS selector and JavaScript identifier signals rank the matching source', async t => {
  const manifest = await project(t, {
    'card.css': '.card { margin: 4px; }', 'other.css': 'body { padding: 0; }',
    'settings.js': 'const maxAttempts = 3;', 'other.js': 'const unused = 1;',
  });
  const css = await rankCandidates('change .card margin to 8px', manifest);
  assert.deepEqual(css.selectedPaths, ['card.css']);
  assert.ok(css.candidates[0].reasons.some(reason => reason.signal === 'symbol'));
  const javascript = await rankCandidates('change maxAttempts constant to 5', manifest);
  assert.deepEqual(javascript.selectedPaths, ['settings.js']);
  assert.ok(javascript.candidates[0].reasons.some(reason => reason.signal === 'symbol'));
});

test('score ties have lexical ordering but are not confident selections', async t => {
  const manifest = await project(t, { 'z.css': 'body { margin: 0; }', 'a.css': 'body { margin: 0; }' });
  const first = await rankCandidates('change margin to 8px', manifest);
  const reversed = await rankCandidates('change margin to 8px', { ...manifest, files: [...manifest.files].reverse() });
  assert.deepEqual(first, reversed);
  assert.deepEqual(first.candidates.map(candidate => candidate.path), ['a.css', 'z.css']);
  assert.equal(first.status, 'insufficient_context');
});

test('empty projects, unrelated tasks, and multi-file hints stop safely', async t => {
  const manifest = await project(t, { 'index.html': page, 'style.css': 'body {}' });
  for (const task of ['do something unspecified', 'update index.html and style.css', 'change page title and CSS spacing']) {
    assert.equal((await rankCandidates(task, manifest)).status, 'insufficient_context');
  }
  assert.equal((await rankCandidates('change title', { ...manifest, files: [] })).status, 'insufficient_context');
});

test('inspection budget and invalid requests reject rather than return partial results', async t => {
  const manifest = await project(t, { 'app.js': 'const value = 1;' });
  await assert.rejects(rankCandidates('change constant', manifest, { maxInspectionBytes: 1 }), error => error instanceof RankingError && error.code === 'limit_exceeded');
  for (const task of ['', ' ', 'x'.repeat(4097)]) {
    await assert.rejects(rankCandidates(task, manifest), RankingError);
  }
  for (const options of [{ maxInspectionBytes: 0 }, { maxInspectionBytes: 4 * 1024 * 1024 + 1 }, { unknown: 1 }]) {
    await assert.rejects(rankCandidates('change constant', manifest, options), RankingError);
  }
});

test('changed files and invalid UTF-8 are rejected during source inspection', async t => {
  const manifest = await project(t, { 'app.js': 'const value = 1;' });
  await writeFile(join(manifest.root, 'app.js'), 'changed source longer than the original');
  await assert.rejects(rankCandidates('change constant', manifest), RankingError);
  const binary = await project(t, { 'bad.js': Buffer.from([0xff]) });
  await assert.rejects(rankCandidates('change constant', binary), RankingError);
});

test('a junction replacing a source parent after enumeration cannot be followed', async t => {
  const manifest = await project(t, { 'nested/app.js': 'const value = 1;' });
  const outside = join(manifest.root, 'outside');
  await mkdir(outside);
  await writeFile(join(outside, 'app.js'), 'const value = 2;');
  await rm(join(manifest.root, 'nested'), { recursive: true });
  const link = join(manifest.root, 'nested');
  await symlink(outside, link, process.platform === 'win32' ? 'junction' : 'dir');
  try { await assert.rejects(rankCandidates('change constant', manifest), RankingError); }
  finally { await unlink(link); }
});
