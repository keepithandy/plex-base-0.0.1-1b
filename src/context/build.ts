import { createHash } from 'node:crypto';
import { open } from 'node:fs/promises';
import type { RepositoryManifest } from '../core/contracts.js';
import { modelResponseSchema } from '../core/schemas.js';
import { validateRepositoryManifest, validateTaskRequest } from '../core/validate.js';
import type { RankingResult } from '../repo/rank.js';
import { readSourceSnapshot } from '../repo/scan.js';
import { assessPromptBudget } from './budget.js';
import { ContextError, type ContextBudgetOptions, type ContextBundle, type SelectionSnapshot, type PromptInputs } from './types.js';

export async function verifySelectionSnapshot(bundle: Pick<ContextBundle, 'root' | 'snapshots'>): Promise<void> {
  if (bundle.snapshots.length !== 1) {
    throw new ContextError('insufficient_context', 'Phase 1 verification requires one selected snapshot.');
  }
  for (const snapshot of bundle.snapshots) {
    if (createHash('sha256').update(snapshot.originalBytes).digest('hex') !== snapshot.sha256) {
      throw new ContextError('snapshot_corrupted', 'Original snapshot bytes were modified in memory.');
    }
    try {
      const current = await readSourceSnapshot(bundle.root, snapshot);
      if (current.sha256 !== snapshot.sha256) throw new Error('Hash changed');
    } catch {
      throw new ContextError('stale_snapshot', `Selected source changed or became inaccessible: ${snapshot.path}`);
    }
  }
}

export async function buildContext(task: string, manifest: RepositoryManifest, ranking: RankingResult,
  options: ContextBudgetOptions = {}): Promise<ContextBundle> {
  validateRepositoryManifest(manifest);
  validateTaskRequest({ task, cwd: manifest.root });
  if (ranking.status !== 'selected' || ranking.selectedPaths.length !== 1) {
    throw new ContextError('insufficient_context', 'Context requires one unambiguous selected source file.');
  }
  const path = ranking.selectedPaths[0];
  const matches = manifest.files.filter(file => file.path === path);
  const ranked = ranking.candidates.filter(file => file.path === path);
  if (matches.length !== 1 || ranked.length !== 1 || !/^[a-f0-9]{64}$/.test(ranked[0]!.sha256)
    || ranked[0]!.sizeBytes !== matches[0]!.sizeBytes || ranked[0]!.extension !== matches[0]!.extension) {
    throw new ContextError('insufficient_context', 'Selected file is not uniquely available in the manifest and ranking.');
  }
  let original;
  try { original = await readSourceSnapshot(manifest.root, matches[0]!); }
  catch { throw new ContextError('inspection_failed', `Cannot safely snapshot selected source: ${path}`); }
  if (original.sha256 !== ranked[0]!.sha256) {
    throw new ContextError('stale_snapshot', 'Selected source changed after candidate ranking.');
  }
  if (!original.source.length) throw new ContextError('insufficient_context', 'Selected source has no usable edit anchor.');
  const editableSpans = Object.freeze([Object.freeze({ start: 0, end: original.source.length, unit: 'utf16' as const })]);
  const snapshot: SelectionSnapshot = Object.freeze({ ...original, editableSpans });
  // The original bytes/hash/BOM stay local; model source is losslessly decoded
  // UTF-8 without the BOM. Offsets refer to JavaScript UTF-16 string positions.
  const data = {
    task,
    project: { source: manifest.source, eligibleFileCount: manifest.files.length,
      languageScope: ['HTML', 'CSS', 'JavaScript'], selectedPaths: [path] },
    files: [{ path, extension: snapshot.extension, source: snapshot.source, editableSpans }],
    constraints: { editSelectedFilesOnly: true, preserveUnrelatedBytes: true,
      allowCreation: false, allowDeletion: false, maximumFiles: 1 },
    expectedOutput: { schema: modelResponseSchema },
  };
  let rules: string;
  try {
    const handle = await open(new URL('../../prompts/implementation.txt', import.meta.url), 'r');
    try {
      const info = await handle.stat();
      if (!info.isFile() || !info.size || info.size > 16_384) throw new Error('Invalid prompt size');
      const bytes = Buffer.alloc(info.size + 1);
      let read = 0;
      while (read < bytes.length) {
        const chunk = await handle.read(bytes, read, bytes.length - read, read);
        if (!chunk.bytesRead) break;
        read += chunk.bytesRead;
      }
      const after = await handle.stat();
      if (read !== info.size || after.size !== info.size || after.mtimeMs !== info.mtimeMs) throw new Error('Prompt changed');
      rules = new TextDecoder('utf-8', { fatal: true }).decode(bytes.subarray(0, read));
    } finally { await handle.close(); }
  } catch { throw new ContextError('inspection_failed', 'Cannot load the packaged implementation prompt.'); }
  const input: PromptInputs = {
    messages: Object.freeze([
      Object.freeze({ role: 'system' as const, content: rules }),
      Object.freeze({ role: 'user' as const, content: JSON.stringify(data) }),
    ]),
    responseSchema: modelResponseSchema,
  };
  const budget = await assessPromptBudget(input, options);
  const bundle: ContextBundle = Object.freeze({ ...input, root: manifest.root,
    promptVersion: 'plex-implementation-v1', snapshots: Object.freeze([snapshot]), budget: Object.freeze(budget) });
  await verifySelectionSnapshot(bundle);
  return bundle;
}
