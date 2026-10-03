import test from 'node:test';
import assert from 'node:assert/strict';
import { parseModelResponse, ResponseParseError, responseTextLimits } from '../../dist/core/parse.js';

const patch = { status: 'patch', reason: 'Update title.', edits: [
  { path: 'index.html', old: '<title>Example</title>', new: '<title>DungeonDex</title>' },
] };
const reject = (text, code) => assert.throws(() => parseModelResponse(text), error =>
  error instanceof ResponseParseError && error.code === code && error.status === 'invalid_output');

test('parses exact patch and nonpatch JSON with JSON whitespace', () => {
  assert.deepEqual(parseModelResponse(` \r\n${JSON.stringify(patch)}\t `), patch);
  for (const status of ['no_change', 'insufficient_context', 'unsupported']) {
    const response = { status, reason: 'Nothing to edit.', edits: [] };
    assert.deepEqual(parseModelResponse(JSON.stringify(response)), response);
  }
});

test('preserves escaped anchors, Unicode, whitespace, and empty replacement', () => {
  const response = structuredClone(patch);
  response.edits[0].old = ' \r\n"\\😀\t{}[], ';
  response.edits[0].new = '';
  assert.deepEqual(parseModelResponse(JSON.stringify(response)), response);
});

test('rejects prose, fences, trailing documents, incomplete and non-JSON syntax', () => {
  const json = JSON.stringify(patch);
  for (const text of ['', ' ', `Here: ${json}`, `${json} done`, `\uFEFF${json}`,
    `\u00a0${json}`, `\x60\x60\x60json\n${json}\n\x60\x60\x60`, `${json}${json}`,
    json.slice(0, -1), '{"status":"patch",}', '{/* comment */}', '{status:"patch"}', 'NaN']) {
    reject(text, 'invalid_json');
  }
});

test('rejects nonstring input without coercion', () => {
  for (const value of [null, undefined, patch, Buffer.from('{}'), 1, true]) reject(value, 'invalid_text');
});

test('schema remains authoritative for types, statuses, fields and edit limits', () => {
  for (const value of [null, [], 1, {}, { ...patch, extra: true },
    { ...patch, status: 'runtime_unavailable' }, { ...patch, reason: ' ' },
    { ...patch, edits: [] }, { ...patch, status: 'no_change' },
    { ...patch, edits: [{ ...patch.edits[0], old: '' }] },
    { ...patch, edits: [{ ...patch.edits[0], new: null }] },
    { ...patch, edits: [{ ...patch.edits[0], shell: 'command' }] },
    { ...patch, edits: Array(11).fill(patch.edits[0]) }]) {
    reject(JSON.stringify(value), 'invalid_contract');
  }
  assert.equal(parseModelResponse(JSON.stringify({ ...patch, edits: Array(10).fill(patch.edits[0]) })).edits.length, 10);
});

test('rejects duplicate decoded keys at any object level', () => {
  for (const text of [
    '{"status":"patch","status":"no_change","reason":"x","edits":[]}',
    '{"status":"no_change","sta\\u0074us":"no_change","reason":"x","edits":[]}',
    '{"status":"patch","reason":"x","edits":[{"path":"a","old":"x","old":"y","new":"z"}]}',
    '{"extra":{"__proto__":1,"__proto__":2}}',
  ]) reject(text, 'duplicate_key');
  // Equal names in separate edit objects are normal.
  assert.equal(parseModelResponse(JSON.stringify({ ...patch, edits: [patch.edits[0], patch.edits[0]] })).edits.length, 2);
});

test('bounds response UTF-8 bytes and nesting depth', () => {
  const json = JSON.stringify({ status: 'no_change', reason: 'x', edits: [] });
  assert.equal(parseModelResponse(json.padEnd(responseTextLimits.bytes, ' ')).status, 'no_change');
  reject(json.padEnd(responseTextLimits.bytes + 1, ' '), 'response_too_large');
  reject('😀'.repeat(responseTextLimits.bytes / 4 + 1), 'response_too_large');
  reject('['.repeat(66) + '0' + ']'.repeat(66), 'excessive_depth');
  reject('['.repeat(64) + '0' + ']'.repeat(64), 'invalid_contract');
});

test('failure messages do not expose model contents or unknown keys', () => {
  for (const text of ['SECRET_MODEL_TEXT', '{"SECRET_KEY": true}']) {
    try { parseModelResponse(text); assert.fail('Expected rejection'); }
    catch (error) { assert.ok(error instanceof ResponseParseError); assert.doesNotMatch(error.message, /SECRET/); }
  }
});
