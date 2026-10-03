import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ContractError, validateTaskRequest, validateRepositoryManifest,
  validateModelResponse, validateRunResult,
} from '../../dist/core/validate.js';

const edit = { path: 'index.html', old: '<title>Example</title>', new: '<title>DungeonDex</title>' };
const patch = () => ({ status: 'patch', reason: 'Update title.', edits: [{ ...edit }] });
const result = () => ({
  status: 'proposal_validated', reason: 'HTML check passed.', applied: false,
  repairAttempts: 0, durationMs: 12,
  checks: [{ name: 'HTML', status: 'pass', detail: 'No new parse errors.' }],
  files: [{ path: 'index.html', diff: '-Example\n+DungeonDex' }],
});

test('request contract accepts explicit repo without altering input', () => {
  const value = Object.freeze({ task: 'Update title', cwd: 'C:\\Projects', repo: 'C:\\Projects\\web' });
  assert.equal(validateTaskRequest(value), value);
  assert.doesNotThrow(() => validateTaskRequest({ task: 'Update title', cwd: 'C:\\Projects' }));
});

test('request rejects missing, blank, unknown, oversized, and wrongly typed fields', () => {
  for (const value of [null, [], {}, { task: 'x' }, { task: ' ', cwd: 'C:\\web' },
    { task: 'x', cwd: '' }, { task: 'x', cwd: 'C:\\web', shell: true },
    { task: 1, cwd: 'C:\\web' }, { task: 'x', cwd: 'C:\\web', repo: null },
    { task: 'x'.repeat(4097), cwd: 'C:\\web' }]) {
    assert.throws(() => validateTaskRequest(value), ContractError);
  }
});

test('manifest accepts supported source metadata and empty projects', () => {
  for (const source of ['git', 'directory']) {
    for (const extension of ['.html', '.css', '.js', '.mjs', '.cjs']) {
      assert.doesNotThrow(() => validateRepositoryManifest({
        root: 'C:\\web', source, files: [{ path: `file${extension}`, extension, sizeBytes: 0 }],
      }));
    }
  }
  assert.doesNotThrow(() => validateRepositoryManifest({ root: 'C:\\web', source: 'git', files: [] }));
});

test('manifest rejects unsupported languages, invalid sizes, and unexpected fields', () => {
  const manifest = { root: 'C:\\web', source: 'git', files: [] };
  for (const file of [
    { path: 'app.ts', extension: '.ts', sizeBytes: 10 },
    { path: 'app.js', extension: '.js', sizeBytes: -1 },
    { path: 'app.js', extension: '.js', sizeBytes: 1.5 },
    { path: 'app.js', extension: '.js', sizeBytes: '10' },
    { path: 'app.js', extension: '.js', sizeBytes: 131073 },
    { path: 'app.js', extension: '.js', sizeBytes: 10, content: 'secret' },
  ]) assert.throws(() => validateRepositoryManifest({ ...manifest, files: [file] }), ContractError);
  assert.throws(() => validateRepositoryManifest({ ...manifest, source: 'cloud' }), ContractError);
  assert.throws(() => validateRepositoryManifest({ ...manifest, files: Array(1001).fill({ path: 'a.js', extension: '.js', sizeBytes: 0 }) }), ContractError);
});

test('all model statuses accept their required edit shape', () => {
  assert.doesNotThrow(() => validateModelResponse(patch()));
  for (const status of ['no_change', 'insufficient_context', 'unsupported']) {
    assert.doesNotThrow(() => validateModelResponse({ status, reason: 'Cannot edit.', edits: [] }));
    assert.throws(() => validateModelResponse({ status, reason: 'Cannot edit.', edits: [edit] }), ContractError);
  }
});

test('model output rejects missing/unknown fields, empty patch, and orchestrator statuses', () => {
  for (const value of [{ status: 'patch', edits: [edit] }, { ...patch(), confidence: 1 },
    { ...patch(), edits: [] }, { ...patch(), status: 'repair_failed' },
    { ...patch(), reason: ' ' }, { ...patch(), edits: [{ ...edit, old: '' }] },
    { ...patch(), edits: [{ ...edit, command: 'npm test' }] },
    { ...patch(), edits: [{ ...edit, new: 42 }] },
    { ...patch(), edits: Array(11).fill(edit) }]) {
    assert.throws(() => validateModelResponse(value), ContractError);
  }
});

test('result contract separates validated previews and non-proposal outcomes', () => {
  assert.doesNotThrow(() => validateRunResult(result()));
  for (const status of ['no_change', 'insufficient_context', 'unsupported', 'invalid_output',
    'validation_failed', 'repair_failed', 'runtime_unavailable', 'stale_snapshot']) {
    assert.doesNotThrow(() => validateRunResult({ ...result(), status, files: [], checks: [], repairAttempts: 1 }));
    assert.throws(() => validateRunResult({ ...result(), status }), ContractError);
  }
});

test('results reject applied work, excess repairs, and inconsistent success', () => {
  for (const value of [{ ...result(), applied: true }, { ...result(), repairAttempts: 2 },
    { ...result(), durationMs: -1 }, { ...result(), durationMs: Infinity },
    { ...result(), files: [] }, { ...result(), files: Array(4).fill(result().files[0]) },
    { ...result(), checks: [] },
    { ...result(), checks: [{ name: 'HTML', status: 'fail', detail: 'Bad HTML' }] },
    { ...result(), checks: [{ name: 'HTML', status: 'unavailable', detail: 'Missing parser' }] },
    { ...result(), modelConfidence: 1 }]) {
    assert.throws(() => validateRunResult(value), ContractError);
  }
});

test('rejection does not strip unknown fields or expose source values', () => {
  const value = { ...patch(), secret: 'sensitive-source-value' };
  assert.throws(() => validateModelResponse(value), error => {
    assert.ok(error instanceof ContractError);
    assert.doesNotMatch(error.message, /sensitive-source-value/);
    return true;
  });
  assert.equal(value.secret, 'sensitive-source-value');
});
