export interface TaskRequest {
  task: string;
  cwd: string;
  repo?: string;
}

export type SourceExtension = '.html' | '.css' | '.js' | '.mjs' | '.cjs';

export interface RepositoryFile {
  path: string;
  extension: SourceExtension;
  sizeBytes: number;
}

export interface RepositoryManifest {
  root: string;
  source: 'git' | 'directory';
  files: RepositoryFile[];
}

export interface ModelEdit {
  path: string;
  old: string;
  new: string;
}

export type ModelResponse =
  | { status: 'patch'; reason: string; edits: ModelEdit[] }
  | { status: 'no_change' | 'insufficient_context' | 'unsupported'; reason: string; edits: [] };

export interface ValidationCheck {
  name: string;
  status: 'pass' | 'fail' | 'unavailable';
  detail: string;
}

export interface ProposedFileDiff {
  path: string;
  diff: string;
}

interface ResultBase {
  reason: string;
  applied: false;
  repairAttempts: 0 | 1;
  durationMs: number;
  checks: ValidationCheck[];
}

export type RunResult = ResultBase & (
  | { status: 'proposal_validated'; files: ProposedFileDiff[] }
  | {
      status: 'no_change' | 'insufficient_context' | 'unsupported' | 'invalid_output'
        | 'validation_failed' | 'repair_failed' | 'runtime_unavailable' | 'stale_snapshot';
      files: [];
    }
);
