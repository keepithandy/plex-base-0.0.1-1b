import type { ModelEdit, ModelResponse } from './contracts.js';
import { validateModelResponse } from './validate.js';
import { verifySelectionSnapshot } from '../context/build.js';
import type { ContextBundle, SelectionSnapshot } from '../context/types.js';

export type EditValidationCode = 'invalid_response' | 'invalid_selection' | 'unsafe_path'
  | 'unselected_path' | 'missing_anchor' | 'repeated_anchor' | 'outside_span'
  | 'split_character' | 'split_line_ending' | 'overlapping_edits' | 'stale_snapshot';

export class EditValidationError extends Error {
  constructor(readonly code: EditValidationCode) {
    super(`Invalid proposed edit: ${code}`);
    this.name = 'EditValidationError';
  }
}

export interface LocatedEdit extends ModelEdit {
  readonly start: number;
  readonly end: number;
}

export interface ValidatedEdits {
  readonly path: string;
  readonly sha256: string;
  readonly edits: readonly LocatedEdit[];
}

function safeRelativePath(path: string): boolean {
  const parts = path.split('/');
  return !!path && !/[\\\x00-\x1f<>:"|?*]/.test(path)
    && parts.every(part => !!part && part !== '.' && part !== '..' && !/[ .]$/.test(part)
      && !/^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(part));
}

function validSelection(snapshot: SelectionSnapshot): boolean {
  return snapshot.editableSpans.length > 0 && snapshot.editableSpans.every(span =>
    span.unit === 'utf16' && Number.isSafeInteger(span.start) && Number.isSafeInteger(span.end)
      && span.start >= 0 && span.start < span.end && span.end <= snapshot.source.length);
}

function splitsPair(source: string, offset: number): boolean {
  if (offset <= 0 || offset >= source.length) return false;
  const previous = source.charCodeAt(offset - 1);
  const next = source.charCodeAt(offset);
  return previous >= 0xd800 && previous <= 0xdbff && next >= 0xdc00 && next <= 0xdfff;
}

function splitsCrLf(source: string, offset: number): boolean {
  return offset > 0 && offset < source.length
    && source[offset - 1] === '\r' && source[offset] === '\n';
}

/** Locate edits against the unchanged original snapshot. Never constructs or writes a proposal. */
export async function validateEditAnchors(response: ModelResponse,
  bundle: Pick<ContextBundle, 'root' | 'snapshots'>): Promise<ValidatedEdits> {
  try { validateModelResponse(response); }
  catch { throw new EditValidationError('invalid_response'); }
  if (response.status !== 'patch') throw new EditValidationError('invalid_response');
  if (bundle.snapshots.length !== 1 || !validSelection(bundle.snapshots[0]!)) {
    throw new EditValidationError('invalid_selection');
  }
  const snapshot = bundle.snapshots[0]!;
  if (!safeRelativePath(snapshot.path)) throw new EditValidationError('invalid_selection');
  const located: LocatedEdit[] = [];
  for (const edit of response.edits) {
    if (!safeRelativePath(edit.path)) throw new EditValidationError('unsafe_path');
    // Exact equality also rejects Windows case aliases and alternate spellings.
    if (edit.path !== snapshot.path) throw new EditValidationError('unselected_path');
    const start = snapshot.source.indexOf(edit.old);
    if (start < 0) throw new EditValidationError('missing_anchor');
    if (snapshot.source.indexOf(edit.old, start + 1) >= 0) {
      throw new EditValidationError('repeated_anchor');
    }
    const end = start + edit.old.length;
    if (splitsPair(snapshot.source, start) || splitsPair(snapshot.source, end)) {
      throw new EditValidationError('split_character');
    }
    if (splitsCrLf(snapshot.source, start) || splitsCrLf(snapshot.source, end)) {
      throw new EditValidationError('split_line_ending');
    }
    if (!snapshot.editableSpans.some(span => start >= span.start && end <= span.end)) {
      throw new EditValidationError('outside_span');
    }
    located.push(Object.freeze({ path: edit.path, old: edit.old, new: edit.new, start, end }));
  }
  const ordered = [...located].sort((a, b) => a.start - b.start || a.end - b.end);
  for (let index = 1; index < ordered.length; index++) {
    if (ordered[index]!.start < ordered[index - 1]!.end) {
      throw new EditValidationError('overlapping_edits');
    }
  }
  try { await verifySelectionSnapshot(bundle); }
  catch { throw new EditValidationError('stale_snapshot'); }
  return Object.freeze({ path: snapshot.path, sha256: snapshot.sha256,
    edits: Object.freeze(located) });
}
