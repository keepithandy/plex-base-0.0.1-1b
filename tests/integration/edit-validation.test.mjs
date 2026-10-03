import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, realpath, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { buildContext } from '../../dist/context/build.js';
import { validateEditAnchors, EditValidationError } from '../../dist/core/edit-validation.js';
import { scanProject } from '../../dist/repo/scan.js';
import { rankCandidates } from '../../dist/repo/rank.js';

const source = '<html><head><title>Example</title></head><body>Welcome</body></html>';
const task = 'change the page title to DungeonDex';
const proposed = (...edits) => ({ status: 'patch', reason: 'Update page.', edits });
const edit = (old, replacement, path = 'index.html') => ({ path, old, new: replacement });
const fails = code => error => error instanceof EditValidationError && error.code === code;

async function setup(t, content = source) {
  const root = await realpath(await mkdtemp(join(tmpdir(), 'plex anchors ')));
  t.after(async () => rm(root, { recursive: true, force: true }));
  const file = join(root, 'index.html');
  await writeFile(file, content);
  const manifest = await scanProject({ root, source: 'directory', selection: 'cwd' });
  const ranking = await rankCandidates(task, manifest);
  return { root, file, bundle: await buildContext(task, manifest, ranking) };
}

test('locates independent edits against original bytes and leaves source unchanged', async t => {
  const { file, bundle } = await setup(t);
  const original = await readFile(file);
  const response = proposed(edit('<title>Example</title>', '<title>DungeonDex</title>'),
    edit('Welcome', 'Hello'));
  const result = await validateEditAnchors(response, bundle);
  assert.equal(result.path, 'index.html');
  assert.equal(result.sha256, bundle.snapshots[0].sha256);
  assert.deepEqual(result.edits.map(({ start, end }) => source.slice(start, end)),
    ['<title>Example</title>', 'Welcome']);
  assert.ok(Object.isFrozen(result));
  assert.ok(Object.isFrozen(result.edits));
  assert.deepEqual(await readFile(file), original);
});

test('rejects unselected files, case aliases, traversal and Windows path variants', async t => {
  const { bundle } = await setup(t);
  for (const path of ['style.css', 'INDEX.HTML']) {
    await assert.rejects(validateEditAnchors(proposed(edit('Welcome', 'Hello', path)), bundle), fails('unselected_path'));
  }
  for (const path of ['../index.html', './index.html', '/index.html', 'C:/index.html',
    'C:\\index.html', '\\\\server\\share\\index.html', 'index.html:stream', 'index.html/',
    'index.html.']) {
    await assert.rejects(validateEditAnchors(proposed(edit('Welcome', 'Hello', path)), bundle), fails('unsafe_path'));
  }
});

test('requires exactly one full anchor occurrence and nonoverlapping original ranges', async t => {
  const { bundle } = await setup(t, source.replace('Welcome', 'Example'));
  await assert.rejects(validateEditAnchors(proposed(edit('missing', 'x')), bundle), fails('missing_anchor'));
  await assert.rejects(validateEditAnchors(proposed(edit('Example', 'x')), bundle), fails('repeated_anchor'));
  await assert.rejects(validateEditAnchors(proposed(
    edit('<title>Example</title>', 'x'), edit('Example</title>', 'y')), bundle), fails('overlapping_edits'));
  await assert.rejects(validateEditAnchors(proposed(edit('Example</body>', 'x'), edit('Example</body>', 'y')), bundle), fails('overlapping_edits'));
});

test('refuses anchors outside selected UTF-16 span', async t => {
  const { bundle } = await setup(t);
  const limited = { ...bundle, snapshots: [{ ...bundle.snapshots[0], editableSpans: [
    { start: source.indexOf('<title>'), end: source.indexOf('</title>') + 8, unit: 'utf16' },
  ] }] };
  assert.equal((await validateEditAnchors(proposed(edit('<title>Example</title>', 'x')), limited)).edits.length, 1);
  await assert.rejects(validateEditAnchors(proposed(edit('Welcome', 'Hello')), limited), fails('outside_span'));
});

test('refuses anchors that split a UTF-16 surrogate pair', async t => {
  const { bundle } = await setup(t, source.replace('Welcome', '🐉 Welcome'));
  await assert.rejects(validateEditAnchors(proposed(edit('\ud83d', 'x')), bundle), fails('split_character'));
  await assert.rejects(validateEditAnchors(proposed(edit('\udc09', 'x')), bundle), fails('split_character'));
});

test('refuses anchors that split a CRLF pair', async t => {
  const { bundle } = await setup(t, '<head>\r\n<title>Example</title>\r\n</head>');
  await assert.rejects(validateEditAnchors(proposed(edit('\r', 'x')), bundle), fails('repeated_anchor'));
  await assert.rejects(validateEditAnchors(proposed(edit('head>\r', 'x')), bundle), fails('split_line_ending'));
  await assert.rejects(validateEditAnchors(proposed(edit('\n<title>', 'x')), bundle), fails('split_line_ending'));
});

test('rejects malformed responses and forged selections', async t => {
  const { bundle } = await setup(t);
  for (const response of [proposed(edit('', 'x')), proposed(edit('Welcome', 'x'), edit('Welcome', 'y'),
    ...Array(9).fill(edit('Welcome', 'z'))), { status: 'no_change', reason: 'x', edits: [] },
    proposed({ ...edit('Welcome', 'Hello'), command: 'run' })]) {
    await assert.rejects(validateEditAnchors(response, bundle), fails('invalid_response'));
  }
  await assert.rejects(validateEditAnchors(proposed(edit('Welcome', 'x')),
    { ...bundle, snapshots: [] }), fails('invalid_selection'));
});

test('rejects a selected file changed after prompt construction', async t => {
  const { file, bundle } = await setup(t);
  await writeFile(file, source.replace('Welcome', 'Goodbye'));
  await assert.rejects(validateEditAnchors(proposed(edit('Welcome', 'Hello')), bundle), fails('stale_snapshot'));
});
