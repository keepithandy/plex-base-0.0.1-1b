import type { ModelResponse } from './contracts.js';
import { validateModelResponse } from './validate.js';

export const responseTextLimits = { bytes: 4 * 1024 * 1024, depth: 64 } as const;
export type ResponseParseErrorCode = 'invalid_text' | 'response_too_large' | 'invalid_json'
  | 'duplicate_key' | 'excessive_depth' | 'invalid_contract';

export class ResponseParseError extends Error {
  readonly status = 'invalid_output' as const;
  constructor(readonly code: ResponseParseErrorCode) {
    // Never echo model text, parser diagnostics, keys, or edit contents.
    super(`Invalid model response: ${code}`);
    this.name = 'ResponseParseError';
  }
}

// JSON.parse establishes syntax first. Walk its original text to detect duplicate
// decoded keys (which JSON.parse otherwise silently overwrites), with bounded depth.
function checkStructure(text: string): void {
  let offset = 0;
  const whitespace = () => { while (/[\x20\t\r\n]/.test(text[offset] ?? '_')) offset++; };
  const string = (): string => {
    const start = offset++;
    while (text[offset] !== '"') {
      if (text[offset] === '\\') offset++;
      offset++;
    }
    offset++;
    return JSON.parse(text.slice(start, offset)) as string;
  };
  const value = (depth: number): void => {
    if (depth > responseTextLimits.depth) throw new ResponseParseError('excessive_depth');
    whitespace();
    const opening = text[offset];
    if (opening === '"') { string(); return; }
    if (opening === '{' || opening === '[') {
      const object = opening === '{';
      const closing = object ? '}' : ']';
      const keys = new Set<string>();
      offset++;
      whitespace();
      while (text[offset] !== closing) {
        if (object) {
          const key = string();
          if (keys.has(key)) throw new ResponseParseError('duplicate_key');
          keys.add(key);
          whitespace();
          offset++; // colon; syntax already checked
        }
        value(depth + 1);
        whitespace();
        if (text[offset] === ',') { offset++; whitespace(); }
      }
      offset++;
      return;
    }
    while (offset < text.length && !/[\x20\t\r\n,}\]]/.test(text[offset]!)) offset++;
  };
  value(0);
}

/** Parse exactly one JSON response. No fence stripping, extraction, or repair. */
export function parseModelResponse(text: unknown): ModelResponse {
  if (typeof text !== 'string') throw new ResponseParseError('invalid_text');
  if (Buffer.byteLength(text, 'utf8') > responseTextLimits.bytes) {
    throw new ResponseParseError('response_too_large');
  }
  let value: unknown;
  try { value = JSON.parse(text) as unknown; }
  catch { throw new ResponseParseError('invalid_json'); }
  checkStructure(text);
  try { return validateModelResponse(value); }
  catch { throw new ResponseParseError('invalid_contract'); }
}
