import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, readFile, realpath, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { applyPatch, parsePatch } from 'diff';
import { buildContext } from '../../dist/context/build.js';
import { buildProposal, ProposalError } from '../../dist/core/proposal.js';
import { scanProject } from '../../dist/repo/scan.js';
import { rankCandidates } from '../../dist/repo/rank.js';
import { webFixture, hashFixture } from '../helpers/web-fixture.mjs';

const task = 'change the page title to DungeonDex';
const response = (old, replacement) => ({ status: 'patch', reason: 'Change title.',
  edits: [{ path: 'index.html', old, new: replacement }] });
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const fails = code => error => error instanceof ProposalError && error.code === code;

async function context(root) {
  const manifest = await scanProject({ root, source: 'directory', selection: 'explicit' });
  const ranking = await rankCandidates(task, manifest);
  return buildContext(task, manifest, ranking);
}

async function setup(t, contents) {
  const root = await realpath(await mkdtemp(join(tmpdir(), 'plex proposal ')));
  t.after(async () => rm(root, { recursive: true, force: true }));
  const file = join(root, 'index.html');
  await writeFile(file, contents);
  return { root, file, bundle: await context(root) };
}

test('title fixture yields one applicable title-only unified diff and preserves all originals', async () => {
  const root = await realpath(webFixture);
  const before = await hashFixture();
  const bundle = await context(root);
  const original = bundle.snapshots[0].source;
  const proposal = await buildProposal(response('<title>Example</title>', '<title>DungeonDex</title>'), bundle);
  assert.equal(proposal.path, 'index.html');
  assert.equal(proposal.proposedSource, original.replace('<title>Example</title>', '<title>DungeonDex</title>'));
  assert.deepEqual(proposal.proposedBytes, Buffer.from(proposal.proposedSource));
  assert.equal(proposal.proposedSha256, sha256(proposal.proposedBytes));
  assert.equal(proposal.originalSha256, bundle.snapshots[0].sha256);
  assert.equal(proposal.changedLines, 2);
  assert.equal((proposal.diff.match(/^@@/gm) ?? []).length, 1);
  assert.match(proposal.diff, /^--- a\/index\.html\n\+\+\+ b\/index\.html\n/m);
  assert.match(proposal.diff, /^-  <title>Example<\/title>$/m);
  assert.match(proposal.diff, /^\+  <title>DungeonDex<\/title>$/m);
  assert.equal(applyPatch(original, proposal.diff), proposal.proposedSource);
  assert.equal(parsePatch(proposal.diff).length, 1);
  assert.deepEqual(await hashFixture(), before);
});

test('BOM, CRLF and Unicode remain byte-exact outside edited ranges', async t => {
  const source = '<head>\r\n<title>Example</title>\r\n</head>\r\n<body>🐉</body>\r\n';
  const original = Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), Buffer.from(source)]);
  const { file, bundle } = await setup(t, original);
  const proposal = await buildProposal(response('<title>Example</title>', '<title>DungeonDex</title>'), bundle);
  const expected = Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]),
    Buffer.from(source.replace('Example', 'DungeonDex'))]);
  assert.deepEqual(proposal.proposedBytes, expected);
  assert.equal(proposal.proposedSource, source.replace('Example', 'DungeonDex'));
  assert.equal(applyPatch('\ufeff' + source, proposal.diff), '\ufeff' + proposal.proposedSource);
  assert.deepEqual(await readFile(file), original);
});

test('reverse-position replacements preserve independent anchors and normalize CRLF additions', async t => {
  const source = '<head>\r\n<title>Example</title>\r\n</head>\r\n<body>Ready</body>\r\n';
  const { file, bundle } = await setup(t, source);
  const patch = { status: 'patch', reason: 'Two changes.', edits: [
    { path: 'index.html', old: 'Ready', new: '🐉 Ready' },
    { path: 'index.html', old: '<title>Example</title>', new: '<title>DungeonDex</title>\n<meta name="x">' },
  ] };
  const proposal = await buildProposal(patch, bundle);
  assert.equal(proposal.proposedSource,
    source.replace('<title>Example</title>', '<title>DungeonDex</title>\r\n<meta name="x">')
      .replace('Ready', '🐉 Ready'));
  assert.ok(!/(?<!\r)\n/.test(proposal.proposedSource));
  assert.equal(applyPatch(source, proposal.diff), proposal.proposedSource);
  assert.equal(await readFile(file, 'utf8'), source);
});

test('mixed newlines require matching replacement pattern', async t => {
  const source = '<head>\r\n<title>Example</title>\n</head>\r\n';
  const { bundle } = await setup(t, source);
  await assert.rejects(buildProposal(response('<title>Example</title>', '<title>New</title>\n'), bundle),
    fails('newline_conflict'));
  const proposal = await buildProposal(response('<title>Example</title>', '<title>New</title>'), bundle);
  assert.equal(proposal.proposedSource, source.replace('Example', 'New'));
});

test('refuses no-op, file deletion, invalid Unicode and NUL replacements', async t => {
  const { bundle } = await setup(t, '<title>Example</title>');
  await assert.rejects(buildProposal(response('<title>Example</title>', '<title>Example</title>'), bundle), fails('no_change'));
  await assert.rejects(buildProposal(response('<title>Example</title>', ''), bundle), fails('empty_file'));
  await assert.rejects(buildProposal(response('Example', '\ud800'), bundle), fails('invalid_encoding'));
  await assert.rejects(buildProposal(response('Example', '\0'), bundle), fails('invalid_encoding'));
  await assert.rejects(buildProposal(response('Example', '\ufeffNew'), bundle), fails('invalid_encoding'));
});

test('refuses proposed UTF-8 size beyond 128 KiB', async t => {
  const { bundle } = await setup(t, '<title>Example</title>');
  await assert.rejects(buildProposal(response('Example', '🐉'.repeat(33_000)), bundle), fails('file_too_large'));
});

test('refuses more than 100 changed lines', async t => {
  const source = `<title>Example</title>\n${Array.from({ length: 60 }, (_, index) => `a${index}`).join('\n')}\n`;
  const { bundle } = await setup(t, source);
  const proposal = response(source, `<title>DungeonDex</title>\n${Array.from({ length: 60 }, (_, index) => `b${index}`).join('\n')}\n`);
  await assert.rejects(buildProposal(proposal, bundle), fails('too_many_changed_lines'));
});

test('permits exactly 100 changed lines at the limit', async t => {
  const oldBlock = Array.from({ length: 50 }, (_, index) => `old-${index}`).join('\n');
  const newBlock = Array.from({ length: 50 }, (_, index) => `new-${index}`).join('\n');
  const { bundle } = await setup(t, `<title>Example</title>\n${oldBlock}\n`);
  const proposal = await buildProposal(response(oldBlock, newBlock), bundle);
  assert.equal(proposal.changedLines, 100);
  assert.match(proposal.diff, /^-old-0$/m);
  assert.match(proposal.diff, /^\+new-49$/m);
});

test('unified diff records a missing final newline correctly', async t => {
  const { bundle } = await setup(t, '<title>Example</title>');
  const proposal = await buildProposal(response('Example', 'DungeonDex'), bundle);
  assert.match(proposal.diff, /\\ No newline at end of file/);
  assert.equal(applyPatch(bundle.snapshots[0].source, proposal.diff), proposal.proposedSource);
});

test('refuses a stale source and leaves it unchanged', async t => {
  const { file, bundle } = await setup(t, '<title>Example</title>');
  await writeFile(file, '<title>Changed</title>');
  await assert.rejects(buildProposal(response('Example', 'DungeonDex'), bundle));
  assert.equal(await readFile(file, 'utf8'), '<title>Changed</title>');
});
