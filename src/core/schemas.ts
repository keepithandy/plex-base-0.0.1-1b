// Draft-07 contracts. Filesystem containment, anchor matching, token budgeting,
// and actual validation outcomes belong to their later deterministic subsystems.
export const limits = {
  taskCharacters: 4_096,
  pathCharacters: 4_096,
  reasonCharacters: 2_048,
  sourceBytes: 131_072,
  files: 1_000,
  edits: 10,
  changedFiles: 3,
} as const;

const nonblank = (maxLength: number) => ({
  type: 'string', minLength: 1, maxLength, pattern: '\\S',
});
const path = nonblank(limits.pathCharacters);
const reason = nonblank(limits.reasonCharacters);
const emptyArray = { type: 'array', maxItems: 0 };

export const taskRequestSchema = {
  type: 'object',
  additionalProperties: false,
  required: ['task', 'cwd'],
  properties: {
    task: nonblank(limits.taskCharacters),
    cwd: path,
    repo: path,
  },
} as const;

export const repositoryManifestSchema = {
  type: 'object',
  additionalProperties: false,
  required: ['root', 'source', 'files'],
  properties: {
    root: path,
    source: { enum: ['git', 'directory'] },
    files: {
      type: 'array', maxItems: limits.files,
      items: {
        type: 'object', additionalProperties: false,
        required: ['path', 'extension', 'sizeBytes'],
        properties: {
          path,
          extension: { enum: ['.html', '.css', '.js', '.mjs', '.cjs'] },
          sizeBytes: { type: 'integer', minimum: 0, maximum: limits.sourceBytes },
        },
      },
    },
  },
} as const;

// This is also the schema to send to Plex Runtime for constrained generation.
// Ajv validation remains authoritative, regardless of runtime constraints.
export const modelResponseSchema = {
  type: 'object', additionalProperties: false,
  required: ['status', 'reason', 'edits'],
  properties: {
    status: { enum: ['patch', 'no_change', 'insufficient_context', 'unsupported'] },
    reason,
    edits: {
      type: 'array', maxItems: limits.edits,
      items: {
        type: 'object', additionalProperties: false,
        required: ['path', 'old', 'new'],
        properties: {
          path,
          old: { type: 'string', minLength: 1, maxLength: limits.sourceBytes },
          new: { type: 'string', maxLength: limits.sourceBytes },
        },
      },
    },
  },
  oneOf: [
    { properties: { status: { const: 'patch' }, edits: { type: 'array', minItems: 1 } } },
    {
      properties: {
        status: { enum: ['no_change', 'insufficient_context', 'unsupported'] },
        edits: emptyArray,
      },
    },
  ],
} as const;

export const runResultSchema = {
  type: 'object', additionalProperties: false,
  required: ['status', 'reason', 'applied', 'repairAttempts', 'durationMs', 'checks', 'files'],
  properties: {
    status: {
      enum: ['proposal_validated', 'no_change', 'insufficient_context', 'unsupported',
        'invalid_output', 'validation_failed', 'repair_failed', 'runtime_unavailable', 'stale_snapshot'],
    },
    reason,
    applied: { const: false },
    repairAttempts: { type: 'integer', enum: [0, 1] },
    durationMs: { type: 'number', minimum: 0 },
    checks: {
      type: 'array', maxItems: 100,
      items: {
        type: 'object', additionalProperties: false,
        required: ['name', 'status', 'detail'],
        properties: {
          name: nonblank(256),
          status: { enum: ['pass', 'fail', 'unavailable'] },
          detail: nonblank(4_096),
        },
      },
    },
    files: {
      type: 'array', maxItems: limits.changedFiles,
      items: {
        type: 'object', additionalProperties: false,
        required: ['path', 'diff'],
        properties: { path, diff: nonblank(limits.sourceBytes * 2) },
      },
    },
  },
  oneOf: [
    {
      properties: {
        status: { const: 'proposal_validated' },
        files: { type: 'array', minItems: 1 },
        checks: {
          type: 'array', minItems: 1,
          contains: { type: 'object', properties: { status: { const: 'pass' } }, required: ['status'] },
          items: { type: 'object', properties: { status: { enum: ['pass', 'unavailable'] } } },
        },
      },
    },
    {
      properties: {
        status: { enum: ['no_change', 'insufficient_context', 'unsupported', 'invalid_output',
          'validation_failed', 'repair_failed', 'runtime_unavailable', 'stale_snapshot'] },
        files: emptyArray,
      },
    },
  ],
} as const;
