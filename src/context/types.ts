import type { modelResponseSchema } from '../core/schemas.js';
import type { SourceSnapshot } from '../repo/scan.js';

export interface PromptMessage { readonly role: 'system' | 'user'; readonly content: string }
export interface PromptInputs {
  readonly messages: readonly PromptMessage[];
  readonly responseSchema: typeof modelResponseSchema;
}
// The runtime must count the COMPLETE native chat template, including the
// schema already present in the user message. This is not a source-only count.
export type TokenCounter = (input: PromptInputs) => Promise<number>;

export interface ContextBudgetOptions {
  contextTokens?: number;
  outputTokens?: number;
  safetyTokens?: number;
  maxPromptBytes?: number;
  countTokens?: TokenCounter;
}
export interface ContextBudgetReport {
  contextTokens: number;
  outputTokens: number;
  safetyTokens: number;
  inputLimitTokens: number;
  inputTokens: number;
  serializedBytes: number;
  method: 'estimate' | 'runtime';
  requiresRuntimeCheck: boolean;
}
export interface EditableSpan {
  readonly start: number;
  readonly end: number;
  readonly unit: 'utf16';
}
export interface SelectionSnapshot extends SourceSnapshot {
  readonly editableSpans: readonly EditableSpan[];
}
export interface ContextBundle extends PromptInputs {
  readonly root: string;
  readonly promptVersion: 'plex-implementation-v1';
  readonly snapshots: readonly SelectionSnapshot[];
  readonly budget: ContextBudgetReport;
}
export class ContextError extends Error {
  constructor(public readonly code: 'insufficient_context' | 'budget_exceeded' | 'invalid_options'
    | 'invalid_counter' | 'inspection_failed' | 'stale_snapshot' | 'snapshot_corrupted', message: string) {
    super(message);
    this.name = 'ContextError';
  }
}
