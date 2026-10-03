import test from 'node:test';
import assert from 'node:assert/strict';
import { assessPromptBudget } from '../../dist/context/budget.js';
import { ContextError } from '../../dist/context/types.js';

const input = { messages: [{ role: 'system', content: 'System rules' }, { role: 'user', content: 'Task and source' }], responseSchema: { type: 'object' } };

test('budget estimate includes all serialized inputs and reserves generation/overhead', async () => {
  const report = await assessPromptBudget(input);
  assert.equal(report.serializedBytes, Buffer.byteLength(JSON.stringify(input)));
  assert.equal(report.inputTokens, Math.ceil(report.serializedBytes / 4));
  assert.equal(report.inputLimitTokens, 4096 - 768 - 256);
  assert.equal(report.method, 'estimate');
  assert.equal(report.requiresRuntimeCheck, true);
});

test('exact input boundary passes and one extra runtime token fails', async () => {
  assert.equal((await assessPromptBudget(input, { countTokens: async () => 3072 })).inputTokens, 3072);
  await assert.rejects(assessPromptBudget(input, { countTokens: async () => 3073 }), error => error instanceof ContextError && error.code === 'budget_exceeded');
});

test('prompt bytes are bounded independently of an injected token count', async () => {
  const oversized = { ...input, messages: [{ role: 'user', content: 'x'.repeat(32769) }] };
  let called = false;
  await assert.rejects(assessPromptBudget(oversized, { countTokens: async () => { called = true; return 1; } }), ContextError);
  assert.equal(called, false);
});

test('invalid reserves, limits, unknown fields, and counters fail', async () => {
  for (const options of [{ contextTokens: 0 }, { contextTokens: 4097 }, { outputTokens: 0 },
    { safetyTokens: -1 }, { safetyTokens: 257 }, { contextTokens: 1024 },
    { maxPromptBytes: NaN }, { contextTokens: undefined }, { unknown: 1 }, { countTokens: 1 }]) {
    await assert.rejects(assessPromptBudget(input, options), ContextError);
  }
  for (const value of [0, -1, 1.5, NaN, Infinity, '100']) {
    await assert.rejects(assessPromptBudget(input, { countTokens: async () => value }), error => error instanceof ContextError && error.code === 'invalid_counter');
  }
  await assert.rejects(assessPromptBudget(input, { countTokens: async () => { throw new Error('private provider details'); } }), error => {
    assert.ok(error instanceof ContextError);
    assert.doesNotMatch(error.message, /private provider details/);
    return true;
  });
});

test('Unicode estimates use UTF-8 bytes rather than string length', async () => {
  const unicode = { ...input, messages: [{ role: 'user', content: '🐉'.repeat(100) }] };
  const report = await assessPromptBudget(unicode);
  assert.ok(report.serializedBytes > JSON.stringify(unicode).length);
  assert.equal(report.inputTokens, Math.ceil(Buffer.byteLength(JSON.stringify(unicode)) / 4));
});
