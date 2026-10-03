import { Ajv, type ValidateFunction } from 'ajv';
import type { TaskRequest, RepositoryManifest, ModelResponse, RunResult } from './contracts.js';
import { taskRequestSchema, repositoryManifestSchema, modelResponseSchema, runResultSchema } from './schemas.js';

const ajv = new Ajv({ strict: true, allErrors: true, coerceTypes: false, useDefaults: false, removeAdditional: false });

export class ContractError extends Error {
  constructor(contract: string, validator: ValidateFunction) {
    // Include locations and rule names, not source strings or repository data.
    const details = validator.errors?.map(error => `${error.instancePath || '/'} ${error.keyword}`).join('; ');
    super(`Invalid ${contract}: ${details ?? 'schema violation'}`);
    this.name = 'ContractError';
  }
}

function guard<T>(name: string, schema: object): (value: unknown) => T {
  const validate = ajv.compile<T>(schema);
  return (value: unknown): T => {
    if (!validate(value)) throw new ContractError(name, validate);
    return value;
  };
}

export const validateTaskRequest = guard<TaskRequest>('task request', taskRequestSchema);
export const validateRepositoryManifest = guard<RepositoryManifest>('repository manifest', repositoryManifestSchema);
export const validateModelResponse = guard<ModelResponse>('model response', modelResponseSchema);
export const validateRunResult = guard<RunResult>('run result', runResultSchema);
