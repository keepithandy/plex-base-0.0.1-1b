import type { RepositoryManifest, RepositoryFile, SourceExtension } from '../core/contracts.js';
import { limits } from '../core/schemas.js';
import { validateRepositoryManifest } from '../core/validate.js';
import { readSourceSnapshot } from './scan.js';

export const rankingWeights = {
  exactPath: 120, filename: 80, pathKeyword: 12, language: 30,
  sourceKeyword: 4, symbol: 20, titleElement: 40, indexTitle: 5,
} as const;

export interface RankingSignal { signal: keyof typeof rankingWeights; points: number; detail: string }
export interface RankedCandidate extends RepositoryFile { score: number; reasons: RankingSignal[]; sha256: string }
export type RankingResult = {
  candidates: RankedCandidate[];
  reason: string;
} & (
  | { status: 'selected'; selectedPaths: [string] }
  | { status: 'insufficient_context'; selectedPaths: [] }
);

export class RankingError extends Error {
  constructor(public readonly code: 'limit_exceeded' | 'inspection_failed' | 'invalid_request', message: string) {
    super(message);
    this.name = 'RankingError';
  }
}

const stopWords = new Set(['a', 'an', 'the', 'to', 'in', 'on', 'of', 'and', 'or', 'for', 'from', 'with',
  'please', 'change', 'update', 'modify', 'add', 'fix', 'set', 'make', 'existing', 'page', 'file']);
function tokens(text: string): string[] {
  const split = text.replace(/([a-z0-9])([A-Z])/g, '$1 $2').toLowerCase();
  return [...new Set([
    ...(split.match(/[\p{L}\p{N}_$-]+/gu) ?? []),
    ...(text.toLowerCase().match(/[\p{L}\p{N}_$-]+/gu) ?? []),
  ])].filter(word => word.length > 1 && !stopWords.has(word));
}

function fileHints(task: string): string[] {
  const normalized = task.replace(/\\/g, '/');
  const quoted = [...normalized.matchAll(/["'`]([^"'`\r\n]+\.(?:html|css|mjs|cjs|js))["'`]/gi)].map(match => match[1]!);
  const unquoted = [...normalized.matchAll(/(?:[\p{L}\p{N}_.-]+\/)*[\p{L}\p{N}_.-]+\.(?:html|css|mjs|cjs|js)\b/giu)].map(match => match[0]);
  return [...new Set([...quoted, ...unquoted.filter(hint => !quoted.some(full => full.endsWith(hint)))])]
    .map(hint => hint.replace(/^\.\//, '').toLowerCase());
}

function languages(task: string, titleTask: boolean): Set<SourceExtension> {
  const result = new Set<SourceExtension>();
  if (titleTask || /\b(html|markup|attribute|element)\b/i.test(task)) result.add('.html');
  if (/\b(css|spacing|margin|padding|layout|selector|responsive|color|colour)\b/i.test(task)) result.add('.css');
  if (/\b(javascript|constant|function|conditional|event handler|click handler|validation rule)\b/i.test(task)) {
    for (const extension of ['.js', '.mjs', '.cjs'] as const) result.add(extension);
  }
  return result;
}

export async function rankCandidates(task: string, manifest: RepositoryManifest,
  options: { maxInspectionBytes?: number } = {}): Promise<RankingResult> {
  if (typeof task !== 'string' || !task.trim() || task.length > limits.taskCharacters) {
    throw new RankingError('invalid_request', 'Ranking requires a bounded, nonempty task.');
  }
  const budget = options.maxInspectionBytes ?? 4 * 1024 * 1024;
  if (Object.keys(options).some(key => key !== 'maxInspectionBytes')
    || !Number.isSafeInteger(budget) || budget < 1 || budget > 4 * 1024 * 1024) {
    throw new RankingError('invalid_request', 'Invalid ranking inspection limit.');
  }
  validateRepositoryManifest(manifest);
  if (manifest.files.reduce((sum, file) => sum + file.sizeBytes, 0) > budget) {
    throw new RankingError('limit_exceeded', 'Ranking source exceeds the inspection budget; no partial ranking was returned.');
  }
  const query = tokens(task);
  const hints = fileHints(task);
  const titleTask = /\btitle\b/i.test(task) && !/\b(?:tooltip|attribute)\b/i.test(task);
  const preferred = languages(task, titleTask);
  const candidates: RankedCandidate[] = [];
  const titlePaths = new Set<string>();
  const hintMatches = new Map<string, string[]>();
  for (const hint of hints) hintMatches.set(hint, []);

  // Inspect sequentially and discard each source after extracting signals.
  for (const file of manifest.files) {
    let source: string;
    let sha256: string;
    try { const snapshot = await readSourceSnapshot(manifest.root, file); source = snapshot.source; sha256 = snapshot.sha256; }
    catch { throw new RankingError('inspection_failed', `Cannot safely inspect source: ${file.path}`); }
    const path = file.path.toLowerCase();
    const filename = path.split('/').at(-1)!;
    const reasons: RankingSignal[] = [];
    const add = (signal: keyof typeof rankingWeights, detail: string) => {
      reasons.push({ signal, points: rankingWeights[signal], detail });
    };
    for (const hint of hints) {
      if ((hint.includes('/') && path === hint) || (!hint.includes('/') && filename === hint)) {
        hintMatches.get(hint)!.push(file.path);
        add(hint.includes('/') ? 'exactPath' : 'filename', `Task names ${hint}`);
      }
    }
    for (const keyword of query.filter(word => tokens(path.replace(/\.[^.]+$/, '')).includes(word)).slice(0, 3)) {
      add('pathKeyword', `Path keyword: ${keyword}`);
    }
    if (preferred.has(file.extension)) add('language', `Task suggests ${file.extension}`);
    const sourceTokens = new Set(tokens(source));
    for (const keyword of query.filter(word => sourceTokens.has(word)).slice(0, 5)) {
      add('sourceKeyword', `Source keyword: ${keyword}`);
    }
    // Lexical evidence only: these patterns are not parsers or correctness checks.
    const symbols = new Set([
      ...[...source.matchAll(/\b(?:function|const|let|var|class)\s+([A-Za-z_$][\w$]*)/g)].map(match => match[1]!.toLowerCase()),
      ...[...source.matchAll(/[.#]([A-Za-z_][\w-]*)/g)].map(match => match[1]!.toLowerCase()),
      ...[...source.matchAll(/\b(?:id|class)\s*=\s*["']([^"']+)["']/g)].flatMap(match => match[1]!.toLowerCase().split(/\s+/)),
    ]);
    for (const keyword of query.filter(word => symbols.has(word)).slice(0, 3)) add('symbol', `Identifier/selector: ${keyword}`);
    const html = source.replace(/<!--[\s\S]*?-->/g, '');
    if (titleTask && file.extension === '.html' && /<title(?:\s[^>]*)?>/i.test(html)) {
      titlePaths.add(file.path);
      add('titleElement', 'Contains an HTML title element');
      if (filename === 'index.html') add('indexTitle', 'Conventional index page');
    }
    candidates.push({ ...file, sha256, reasons, score: reasons.reduce((sum, reason) => sum + reason.points, 0) });
  }
  candidates.sort((a, b) => b.score - a.score || (a.path < b.path ? -1 : a.path > b.path ? 1 : 0));
  const refuse = (reason: string): RankingResult => ({ status: 'insufficient_context', reason, candidates, selectedPaths: [] });
  const select = (path: string, reason: string): RankingResult => ({ status: 'selected', reason, candidates, selectedPaths: [path] });
  if (!candidates.length) return refuse('No eligible source files are available.');
  if (hints.length) {
    if ([...hintMatches.values()].some(matches => matches.length !== 1)) {
      return refuse('A named file is missing or ambiguous; provide its exact relative path.');
    }
    const matches = [...new Set([...hintMatches.values()].flat())];
    if (matches.length !== 1) return refuse('Multi-file selection is not supported by the Phase 1 ranker.');
    if (titleTask && !titlePaths.has(matches[0]!)) return refuse('The named file does not contain the required HTML title context.');
    return select(matches[0]!, 'Task names one available source file.');
  }
  const languageFamilies = new Set([...preferred].map(extension => ['.js', '.mjs', '.cjs'].includes(extension) ? 'javascript' : extension));
  if (languageFamilies.size > 1) return refuse('The task suggests multiple source languages; Phase 1 requires one explicit target file.');
  const eligible = titleTask ? candidates.filter(candidate => titlePaths.has(candidate.path))
    : preferred.size ? candidates.filter(candidate => preferred.has(candidate.extension)) : candidates;
  if (!eligible.length) return refuse('Required source context was not found.');
  const top = eligible[0]!;
  const next = eligible[1];
  if (next && (next.score === top.score || (titleTask
    && !top.reasons.some(reason => reason.signal === 'pathKeyword')))) {
    return refuse('Several files match the task; name the target file or relative path.');
  }
  if (!top.score) return refuse('No useful task-to-file signal was found.');
  return select(top.path, 'One candidate has the strongest available task signals.');
}
