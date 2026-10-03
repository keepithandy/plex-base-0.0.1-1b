import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { constants, type Stats } from 'node:fs';
import { lstat, open, opendir, realpath } from 'node:fs/promises';
import { extname, isAbsolute, join, relative, resolve, sep } from 'node:path';
import { promisify } from 'node:util';
import ignore from 'ignore';
import type { RepositoryFile, RepositoryManifest, SourceExtension } from '../core/contracts.js';
import { limits } from '../core/schemas.js';
import { validateRepositoryManifest } from '../core/validate.js';
import type { ProjectRoot } from './detect.js';
import { gitEnvironment } from './git.js';

const execute = promisify(execFile);
const extensions = new Set<SourceExtension>(['.html', '.css', '.js', '.mjs', '.cjs']);
const excludedDirectories = new Set([
  '.git', '.agents', '.codex', '.aws', 'node_modules', 'bower_components', 'vendor',
  'dist', 'build', 'out', 'target', 'coverage', '.next', '.nuxt', '.cache',
  '.parcel-cache', '.test-artifacts', '.venv', 'venv', '__pycache__',
]);

export const defaultScanLimits = {
  maxFiles: limits.files,
  maxFileBytes: limits.sourceBytes,
  maxEntries: 20_000,
  maxDepth: 64,
  maxInspectionBytes: 4 * 1024 * 1024,
  maxGitOutputBytes: 1024 * 1024,
  gitTimeoutMs: 5_000,
} as const;

export type ScanOptions = Partial<{ [K in keyof typeof defaultScanLimits]: number }>;
type IgnoreScope = { base: string; rules: ReturnType<typeof ignore> };

export class RepositoryScanError extends Error {
  constructor(public readonly code: 'limit_exceeded' | 'unsafe_path' | 'scan_failed', message: string) {
    super(message);
    this.name = 'RepositoryScanError';
  }
}

function failLimit(name: string): never {
  throw new RepositoryScanError('limit_exceeded', `Repository scan exceeded ${name}; no partial manifest was returned.`);
}

function samePath(a: string, b: string): boolean {
  return process.platform === 'win32' ? a.toLowerCase() === b.toLowerCase() : a === b;
}

function contained(root: string, path: string): boolean {
  const child = relative(root, path);
  return child !== '..' && !child.startsWith(`..${sep}`) && !isAbsolute(child);
}

function pathParts(path: string): string[] {
  const parts = path.split('/');
  if (!path || isAbsolute(path) || path.length > limits.pathCharacters
    || /[\\\x00-\x1f<>:"|?*]/.test(path)
    || parts.some(part => !part || part === '.' || part === '..' || /[ .]$/.test(part)
      || /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(part))) {
    throw new RepositoryScanError('unsafe_path', 'Repository scan encountered a path incompatible with safe Windows traversal.');
  }
  return parts;
}

function hardExcluded(parts: string[]): boolean {
  return parts.some(part => excludedDirectories.has(part.toLowerCase()) || /^\.env(?:\.|$)/i.test(part))
    || /\.(?:min|bundle|generated)\.(?:js|mjs|cjs|css)$/i.test(parts.at(-1) ?? '');
}

async function exists(path: string): Promise<boolean> {
  try { await lstat(path); return true; }
  catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return false;
    throw error;
  }
}

// Bounded source inspection shared with ranking and later context construction.
// Recheck every component; a manifest does not authorize following new links.
export interface SourceSnapshot extends RepositoryFile {
  readonly source: string;
  readonly originalBytes: Buffer;
  readonly sha256: string;
  readonly encoding: 'utf8';
  readonly hasBom: boolean;
  readonly newlineStyle: 'lf' | 'crlf' | 'cr' | 'mixed' | 'none';
}

export async function readSourceSnapshot(root: string, file: RepositoryFile): Promise<SourceSnapshot> {
  if (!isAbsolute(root) || !samePath(await realpath(root), resolve(root))) {
    throw new RepositoryScanError('unsafe_path', 'Source inspection requires a canonical project root.');
  }
  const parts = pathParts(file.path);
  if (hardExcluded(parts) || !extensions.has(file.extension) || extname(file.path).toLowerCase() !== file.extension) {
    throw new RepositoryScanError('unsafe_path', 'Source inspection requires an eligible source path and matching extension.');
  }
  if (parts.length > defaultScanLimits.maxDepth || file.sizeBytes > limits.sourceBytes
    || !Number.isSafeInteger(file.sizeBytes) || file.sizeBytes < 0) failLimit('source inspection');
  async function inspect(): Promise<Stats> {
    let current = root;
    let info: Stats | undefined;
    for (const part of parts) {
      current = join(current, part);
      info = await lstat(current);
      if (info.isSymbolicLink() || !contained(root, await realpath(current))
        || !samePath(await realpath(current), current)
        || (info.isDirectory() && await exists(join(current, '.git')))) {
        throw new RepositoryScanError('unsafe_path', 'A source path changed or resolved through a link or nested repository.');
      }
    }
    if (!info?.isFile() || info.size !== file.sizeBytes) {
      throw new RepositoryScanError('scan_failed', 'Source metadata changed after enumeration.');
    }
    return info;
  }
  const before = await inspect();
  const handle = await open(join(root, ...parts), constants.O_RDONLY | (process.platform === 'win32' ? 0 : constants.O_NOFOLLOW));
  try {
    const opened = await handle.stat();
    if (opened.dev !== before.dev || opened.ino !== before.ino || opened.size !== before.size
      || opened.mtimeMs !== before.mtimeMs || !opened.isFile()) {
      throw new RepositoryScanError('scan_failed', 'Source changed while opening it.');
    }
    const buffer = Buffer.alloc(file.sizeBytes + 1);
    let read = 0;
    while (read < buffer.length) {
      const chunk = await handle.read(buffer, read, buffer.length - read, read);
      if (!chunk.bytesRead) break;
      read += chunk.bytesRead;
    }
    const after = await inspect();
    const descriptor = await handle.stat();
    if (read !== file.sizeBytes || after.dev !== opened.dev || after.ino !== opened.ino
      || after.mtimeMs !== opened.mtimeMs || descriptor.size !== opened.size
      || descriptor.mtimeMs !== opened.mtimeMs) {
      throw new RepositoryScanError('scan_failed', 'Source changed during inspection.');
    }
    const bytes = buffer.subarray(0, read);
    if (bytes.includes(0)) throw new RepositoryScanError('scan_failed', 'Source is not supported UTF-8 text.');
    const source = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
    const endings = new Set(source.match(/\r\n|\r|\n/g) ?? []);
    const newlineStyle = endings.size > 1 ? 'mixed' : endings.has('\r\n') ? 'crlf'
      : endings.has('\n') ? 'lf' : endings.has('\r') ? 'cr' : 'none';
    return Object.freeze({ ...file, source, originalBytes: bytes,
      sha256: createHash('sha256').update(bytes).digest('hex'), encoding: 'utf8' as const,
      hasBom: bytes.subarray(0, 3).equals(Buffer.from([0xef, 0xbb, 0xbf])), newlineStyle });
  } finally { await handle.close(); }
}

export async function readSourceFile(root: string, file: RepositoryFile): Promise<string> {
  return (await readSourceSnapshot(root, file)).source;
}

export async function scanProject(project: ProjectRoot, options: ScanOptions = {}): Promise<RepositoryManifest> {
  const budget = { ...defaultScanLimits, ...options };
  for (const key of Object.keys(budget) as (keyof typeof budget)[]) {
    const value = budget[key];
    if (!Object.hasOwn(defaultScanLimits, key) || !Number.isSafeInteger(value) || value < 1 || value > defaultScanLimits[key]) {
      throw new RepositoryScanError('scan_failed', `Invalid scan limit: ${key}; overrides may only lower the default.`);
    }
  }
  if (!isAbsolute(project.root) || !['git', 'directory'].includes(project.source)) {
    throw new RepositoryScanError('unsafe_path', 'Scan requires an absolute project root and a known source.');
  }

  try {
    const root = await realpath(project.root);
    if (!(await lstat(root)).isDirectory() || !samePath(root, resolve(project.root))) {
      throw new RepositoryScanError('unsafe_path', 'Scan requires an existing canonical project directory.');
    }
    const files: RepositoryFile[] = [];
    const aliases = new Set<string>();
    let entries = 0;
    let inspectedBytes = 0;

    // Check every component, including tracked paths whose parent became a link.
    // An explicitly selected canonical root is allowed; traversal links are not.
    async function inspectPath(path: string): Promise<{ absolute: string; info: Stats } | undefined> {
      const parts = pathParts(path);
      if (parts.length > budget.maxDepth) failLimit('maxDepth');
      let absolute = root;
      let info: Stats | undefined;
      for (const [index, part] of parts.entries()) {
        absolute = join(absolute, part);
        try { info = await lstat(absolute); }
        catch (error) {
          if ((error as NodeJS.ErrnoException).code === 'ENOENT') return undefined;
          throw error;
        }
        if (info.isSymbolicLink()) return undefined;
        if (index < parts.length - 1 && !info.isDirectory()) return undefined;
        if (info.isDirectory() && await exists(join(absolute, '.git'))) return undefined;
        const actual = await realpath(absolute);
        if (!contained(root, actual) || !samePath(actual, absolute)) {
          throw new RepositoryScanError('unsafe_path', 'A repository path resolved outside its expected location.');
        }
      }
      return info ? { absolute, info } : undefined;
    }

    async function readPrefix(path: string, bytes: number, expected: Stats): Promise<Buffer> {
      const entry = await inspectPath(path);
      if (!entry?.info.isFile() || entry.info.size !== expected.size || entry.info.mtimeMs !== expected.mtimeMs
        || entry.info.dev !== expected.dev || entry.info.ino !== expected.ino) {
        throw new RepositoryScanError('scan_failed', 'A repository file changed during inspection.');
      }
      const handle = await open(entry.absolute, constants.O_RDONLY | (process.platform === 'win32' ? 0 : constants.O_NOFOLLOW));
      try {
        const opened = await handle.stat();
        if (!opened.isFile() || opened.dev !== entry.info.dev || opened.ino !== entry.info.ino
          || opened.size !== entry.info.size || opened.mtimeMs !== entry.info.mtimeMs) {
          throw new RepositoryScanError('scan_failed', 'A repository file changed during inspection.');
        }
        const length = Math.min(bytes, opened.size);
        if (inspectedBytes + length > budget.maxInspectionBytes) failLimit('maxInspectionBytes');
        const buffer = Buffer.alloc(length);
        const { bytesRead } = await handle.read(buffer, 0, length, 0);
        inspectedBytes += bytesRead;
        const after = await handle.stat();
        const current = await inspectPath(path);
        if (bytesRead !== length || after.size !== opened.size || after.mtimeMs !== opened.mtimeMs
          || !current || current.info.dev !== opened.dev || current.info.ino !== opened.ino
          || current.info.size !== opened.size || current.info.mtimeMs !== opened.mtimeMs) {
          throw new RepositoryScanError('scan_failed', 'A repository file changed during inspection.');
        }
        return buffer.subarray(0, bytesRead);
      } finally { await handle.close(); }
    }

    async function addFile(path: string): Promise<void> {
      const parts = pathParts(path);
      if (hardExcluded(parts)) return;
      const extension = extname(path).toLowerCase() as SourceExtension;
      if (!extensions.has(extension)) return;
      const entry = await inspectPath(path);
      if (!entry?.info.isFile()) return; // Deleted tracked files, links, and submodules.
      if (entry.info.size > budget.maxFileBytes) failLimit(`maxFileBytes (${path})`);
      // Small sniff only; full text decoding and source reads belong to context construction.
      if ((await readPrefix(path, 4_096, entry.info)).includes(0)) return;
      const key = process.platform === 'win32' ? path.toLowerCase() : path;
      if (aliases.has(key)) throw new RepositoryScanError('unsafe_path', 'Multiple repository paths identify the same source file.');
      aliases.add(key);
      if (files.length >= budget.maxFiles) failLimit('maxFiles');
      files.push({ path, extension, sizeBytes: entry.info.size });
    }

    if (project.source === 'git') {
      const { stdout } = await execute('git', [
        '--no-optional-locks', 'ls-files', '--cached', '--others', '--exclude-standard', '--stage', '-z', '--', '.',
      ], { cwd: root, env: gitEnvironment(), encoding: 'buffer', windowsHide: true,
        timeout: budget.gitTimeoutMs, maxBuffer: budget.maxGitOutputBytes });
      let listing: string;
      try { listing = new TextDecoder('utf-8', { fatal: true }).decode(stdout); }
      catch { throw new RepositoryScanError('unsafe_path', 'Git returned paths that are not valid UTF-8.'); }
      if (listing && !listing.endsWith('\0')) throw new RepositoryScanError('scan_failed', 'Git returned an incomplete path list.');
      const records = listing ? listing.slice(0, -1).split('\0') : [];
      if (records.length > budget.maxEntries) failLimit('maxEntries');
      const paths: string[] = [];
      for (const record of records) {
        // --stage adds mode/hash/stage to tracked records; untracked paths remain
        // plain. Exclude symlinks and gitlinks even on Windows checkouts where
        // Git may materialize a symlink as a regular text file.
        const tracked = /^(\d{6}) [a-f0-9]+ [0-3]\t([\s\S]+)$/.exec(record);
        if (tracked && tracked[1] !== '100644' && tracked[1] !== '100755') continue;
        const path = tracked ? tracked[2]! : record;
        // Untracked nested repositories may be directory markers ending in '/'.
        paths.push(path.endsWith('/') ? path.slice(0, -1) : path);
      }
      for (const path of [...new Set(paths)].sort()) await addFile(path);
    } else {
      function ignored(path: string, directory: boolean, scopes: IgnoreScope[]): boolean {
        let excluded = false;
        for (const scope of scopes) {
          const local = scope.base ? path.slice(scope.base.length + 1) : path;
          const result = scope.rules.test(local + (directory ? '/' : ''));
          if (result.ignored) excluded = true;
          else if (result.unignored) excluded = false;
        }
        return excluded;
      }

      async function walk(base: string, inherited: IgnoreScope[]): Promise<void> {
        const ignorePath = base ? `${base}/.gitignore` : '.gitignore';
        const ignoreEntry = await inspectPath(ignorePath);
        let scopes = inherited;
        if (ignoreEntry?.info.isFile()) {
          if (ignoreEntry.info.size > 65_536) failLimit('.gitignore size');
          const patterns = new TextDecoder('utf-8', { fatal: true }).decode(await readPrefix(ignorePath, 65_536, ignoreEntry.info));
          scopes = [...inherited, { base, rules: ignore({ ignorecase: process.platform === 'win32' }).add(patterns) }];
        }
        const directory = await opendir(base ? join(root, ...pathParts(base)) : root);
        const names: string[] = [];
        for await (const entry of directory) {
          if (++entries > budget.maxEntries) failLimit('maxEntries');
          names.push(entry.name);
        }
        for (const name of names.sort()) {
          const path = base ? `${base}/${name}` : name;
          const parts = pathParts(path);
          if (hardExcluded(parts)) continue;
          const entry = await inspectPath(path);
          if (!entry || ignored(path, entry.info.isDirectory(), scopes)) continue;
          if (entry.info.isDirectory()) await walk(path, scopes);
          else if (entry.info.isFile()) await addFile(path);
        }
      }
      await walk('', []);
    }
    files.sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
    return validateRepositoryManifest({ root, source: project.source, files });
  } catch (error) {
    if (error instanceof RepositoryScanError) throw error;
    const failure = error as NodeJS.ErrnoException;
    if (failure.code === 'ERR_CHILD_PROCESS_STDIO_MAXBUFFER') failLimit('maxGitOutputBytes');
    throw new RepositoryScanError('scan_failed', 'Repository enumeration failed; check paths, permissions, and Git availability.');
  }
}
