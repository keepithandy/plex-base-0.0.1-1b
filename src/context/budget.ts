import { ContextError, type ContextBudgetOptions, type ContextBudgetReport, type PromptInputs } from './types.js';

export const defaultContextBudget = {
  contextTokens: 4_096, outputTokens: 768, safetyTokens: 256, maxPromptBytes: 32_768,
} as const;

export async function assessPromptBudget(input: PromptInputs, options: ContextBudgetOptions = {}): Promise<ContextBudgetReport> {
  for (const key of Object.keys(options)) {
    if (!Object.hasOwn(defaultContextBudget, key) && key !== 'countTokens') {
      throw new ContextError('invalid_options', `Unknown context budget option: ${key}`);
    }
  }
  const { contextTokens, outputTokens, safetyTokens, maxPromptBytes } = { ...defaultContextBudget, ...options };
  for (const [key, value] of Object.entries({ contextTokens, outputTokens, safetyTokens, maxPromptBytes })) {
    if (!Number.isSafeInteger(value) || value < (key === 'safetyTokens' ? 0 : 1)
      || value > defaultContextBudget[key as keyof typeof defaultContextBudget]) {
      throw new ContextError('invalid_options', `Invalid context budget option: ${key}`);
    }
  }
  if (options.countTokens !== undefined && typeof options.countTokens !== 'function') {
    throw new ContextError('invalid_options', 'Token counter must be a function.');
  }
  const inputLimitTokens = contextTokens - outputTokens - safetyTokens;
  if (inputLimitTokens < 1) throw new ContextError('invalid_options', 'Context must leave room for prompt input after reserves.');
  // Count all serialized message text, structure and schema, not just source.
  // Four UTF-8 bytes/token is only an estimate and does not certify model fit.
  const serializedBytes = Buffer.byteLength(JSON.stringify(input), 'utf8');
  if (serializedBytes > maxPromptBytes) {
    throw new ContextError('budget_exceeded', 'Required prompt exceeds the byte budget; selected source was not truncated.');
  }
  let inputTokens = Math.ceil(serializedBytes / 4);
  const method = options.countTokens ? 'runtime' : 'estimate';
  if (options.countTokens) {
    try { inputTokens = await options.countTokens(input); }
    catch { throw new ContextError('invalid_counter', 'Runtime token accounting failed.'); }
    if (!Number.isSafeInteger(inputTokens) || inputTokens < 1) {
      throw new ContextError('invalid_counter', 'Runtime returned an invalid prompt token count.');
    }
  }
  if (inputTokens > inputLimitTokens) {
    throw new ContextError('budget_exceeded', 'Required prompt exceeds the input token budget; selected source was not truncated.');
  }
  return { contextTokens, outputTokens, safetyTokens, inputLimitTokens, inputTokens, serializedBytes,
    method, requiresRuntimeCheck: method === 'estimate' };
}
