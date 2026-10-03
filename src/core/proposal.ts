import { createHash } from 'node:crypto';
import { formatPatch, structuredPatch } from 'diff';
import type { ModelResponse } from './contracts.js';
import { limits } from './schemas.js';
import { validateEditAnchors } from './edit-validation.js';
import { verifySelectionSnapshot } from '../context/build.js';
import type { ContextBundle, SelectionSnapshot } from '../context/types.js';

export const proposalLimits = { changedLines: 100, diffBytes: limits.sourceBytes * 2 } as const;
export type ProposalErrorCode = 'stale_snapshot' | 'invalid_encoding' | 'newline_conflict'
  | 'empty_file' | 'no_change' | 'file_too_large' | 'too_many_changed_lines'
  | 'diff_unavailable' | 'diff_too_large';

export class ProposalError extends Error {
  constructor(readonly code: ProposalErrorCode) {
    super(`Cannot construct proposal: ${code}`);
    this.name = 'ProposalError';
  }
}

export interface ProposedFile {
  readonly path: string;
  readonly originalSha256: string;
  readonly proposedSha256: string;
  readonly proposedSource: string;
  readonly proposedBytes: Buffer;
  readonly diff: string;
  readonly changedLines: number;
}

function hasUnpairedSurrogate(text: string): boolean {
  for (let index = 0; index < text.length; index++) {
    const code = text.charCodeAt(index);
    if (code >= 0xd800 && code <= 0xdbff) {
      const following = text.charCodeAt(++index);
      if (!(following >= 0xdc00 && following <= 0xdfff)) return true;
    } else if (code >= 0xdc00 && code <= 0xdfff) return true;
  }
  return false;
}

function lineEndings(text: string): string[] { return text.match(/\r\n|\r|\n/g) ?? []; }

function normalizeReplacement(newText: string, oldText: string, snapshot: SelectionSnapshot): string {
  if (newText.includes('\0') || newText.includes('\ufeff') || hasUnpairedSurrogate(newText)) {
    throw new ProposalError('invalid_encoding');
  }
  if (snapshot.newlineStyle === 'mixed') {
    if (lineEndings(newText).join('\0') !== lineEndings(oldText).join('\0')) {
      throw new ProposalError('newline_conflict');
    }
    return newText;
  }
  const ending = snapshot.newlineStyle === 'crlf' ? '\r\n'
    : snapshot.newlineStyle === 'cr' ? '\r' : '\n';
  return newText.replace(/\r\n|\r|\n/g, ending);
}

function byteOffset(snapshot: SelectionSnapshot, utf16Offset: number): number {
  return (snapshot.hasBom ? 3 : 0) + Buffer.byteLength(snapshot.source.slice(0, utf16Offset), 'utf8');
}

/** Construct one in-memory preview from validated original-snapshot edit locations. */
export async function buildProposal(response: ModelResponse, bundle: ContextBundle): Promise<ProposedFile> {
  const located = await validateEditAnchors(response, bundle);
  const snapshot = bundle.snapshots[0]!;
  if (snapshot.sha256 !== located.sha256 || snapshot.path !== located.path) {
    throw new ProposalError('stale_snapshot');
  }
  let proposedBytes = Buffer.from(snapshot.originalBytes);
  const edits = [...located.edits].sort((left, right) => right.start - left.start);
  for (const edit of edits) {
    const start = byteOffset(snapshot, edit.start);
    const end = byteOffset(snapshot, edit.end);
    const replacement = Buffer.from(normalizeReplacement(edit.new, edit.old, snapshot), 'utf8');
    if (!proposedBytes.subarray(start, end).equals(Buffer.from(edit.old, 'utf8'))) {
      throw new ProposalError('stale_snapshot');
    }
    proposedBytes = Buffer.concat([
      proposedBytes.subarray(0, start), replacement, proposedBytes.subarray(end),
    ]);
  }
  if (proposedBytes.length === 0 || (snapshot.hasBom && proposedBytes.length === 3)) {
    throw new ProposalError('empty_file');
  }
  if (proposedBytes.equals(snapshot.originalBytes)) throw new ProposalError('no_change');
  if (proposedBytes.length > limits.sourceBytes) throw new ProposalError('file_too_large');
  let proposedSource: string;
  try {
    proposedSource = new TextDecoder('utf-8', { fatal: true }).decode(proposedBytes);
  } catch { throw new ProposalError('invalid_encoding'); }
  if (proposedSource.includes('\0')) throw new ProposalError('invalid_encoding');
  const originalWithBom = (snapshot.hasBom ? '\ufeff' : '') + snapshot.source;
  const proposedWithBom = (snapshot.hasBom ? '\ufeff' : '') + proposedSource;
  const patch = structuredPatch(`a/${snapshot.path}`, `b/${snapshot.path}`,
    originalWithBom, proposedWithBom, undefined, undefined,
    { context: 3, maxEditLength: proposalLimits.changedLines });
  if (!patch) throw new ProposalError('too_many_changed_lines');
  if (patch.hunks.length === 0) throw new ProposalError('diff_unavailable');
  const changedLines = patch.hunks.reduce((total, hunk) => total + hunk.lines.filter(line =>
    line.startsWith('+') || line.startsWith('-')).length, 0);
  if (changedLines > proposalLimits.changedLines) throw new ProposalError('too_many_changed_lines');
  const diff = formatPatch(patch);
  if (Buffer.byteLength(diff, 'utf8') > proposalLimits.diffBytes) {
    throw new ProposalError('diff_too_large');
  }
  try { await verifySelectionSnapshot(bundle); }
  catch { throw new ProposalError('stale_snapshot'); }
  return Object.freeze({ path: snapshot.path, originalSha256: snapshot.sha256,
    proposedSha256: createHash('sha256').update(proposedBytes).digest('hex'),
    proposedSource, proposedBytes, diff, changedLines });
}
