import { execFile } from 'node:child_process';
import { lstat, realpath, stat } from 'node:fs/promises';
import { dirname, isAbsolute, join, relative, resolve, sep } from 'node:path';
import { promisify } from 'node:util';
import type { TaskRequest } from '../core/contracts.js';
import { gitEnvironment } from './git.js';

const execute = promisify(execFile);

export interface ProjectRoot {
  root: string;
  source: 'git' | 'directory';
  selection: 'explicit' | 'git' | 'cwd';
  gitRoot?: string;
  note?: string;
}

export type GitProbe =
  | { status: 'found'; root: string }
  | { status: 'not_repository' }
  | { status: 'unavailable' };

export class ProjectDetectionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ProjectDetectionError';
  }
}

async function canonicalDirectory(path: string): Promise<string> {
  try {
    const canonical = await realpath(path);
    if (!(await stat(canonical)).isDirectory()) {
      throw new ProjectDetectionError(`Project path is not a directory: ${path}`);
    }
    return canonical;
  } catch (error) {
    if (error instanceof ProjectDetectionError) throw error;
    throw new ProjectDetectionError(`Cannot access project directory: ${path}`);
  }
}

async function hasGitMarker(directory: string): Promise<boolean> {
  let current = directory;
  for (;;) {
    try {
      await lstat(join(current, '.git'));
      return true;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') {
        throw new ProjectDetectionError(`Cannot inspect Git metadata in: ${current}`);
      }
    }
    const parent = dirname(current);
    if (parent === current) return false;
    current = parent;
  }
}

export async function probeGit(directory: string): Promise<GitProbe> {
  // Ignore inherited Git location overrides so the current project wins.
  // Retain normal configuration, including the host's safe.directory policy.
  // Commands use fixed argument arrays, no shell, no optional locks, and no prompts.
  try {
    const { stdout } = await execute('git', ['--no-optional-locks', 'rev-parse', '--show-toplevel'], {
      cwd: directory, env: gitEnvironment(), encoding: 'utf8', windowsHide: true,
      timeout: 5_000, maxBuffer: 16_384,
    });
    // Remove only the final newline: spaces in directory names are meaningful.
    const root = stdout.replace(/\r?\n$/, '');
    if (!root || /[\r\n\0]/.test(root)) {
      throw new ProjectDetectionError('Git returned an invalid project root.');
    }
    return { status: 'found', root };
  } catch (error) {
    if (error instanceof ProjectDetectionError) throw error;
    const failure = error as NodeJS.ErrnoException & { stderr?: string; killed?: boolean };
    if (failure.code === 'ENOENT') return { status: 'unavailable' };
    if (!failure.killed && /^fatal: not a git repository\b/m.test(failure.stderr ?? '')
      && !(await hasGitMarker(directory))) {
      return { status: 'not_repository' };
    }
    // Corrupt metadata, bare repositories, permission problems, and timeouts
    // must not masquerade as ordinary directories or expose raw Git output.
    throw new ProjectDetectionError('Git project detection failed; check repository metadata and permissions.');
  }
}

export async function detectProjectRoot(
  request: Pick<TaskRequest, 'cwd' | 'repo'>,
  gitProbe: (directory: string) => Promise<GitProbe> = probeGit,
): Promise<ProjectRoot> {
  if (!request.cwd?.trim() || !isAbsolute(request.cwd)) {
    throw new ProjectDetectionError('Working directory must be a nonempty absolute path.');
  }
  if (request.repo !== undefined && !request.repo.trim()) {
    throw new ProjectDetectionError('Explicit repository path must not be empty.');
  }
  const cwd = await canonicalDirectory(request.cwd);
  const explicit = request.repo !== undefined;
  const selected = explicit ? await canonicalDirectory(resolve(cwd, request.repo!)) : cwd;
  const git = await gitProbe(selected);

  if (git.status === 'found') {
    if (!isAbsolute(git.root)) throw new ProjectDetectionError('Git returned a relative project root.');
    const gitRoot = await canonicalDirectory(git.root);
    const child = relative(gitRoot, selected);
    if (child === '..' || child.startsWith(`..${sep}`) || isAbsolute(child)) {
      throw new ProjectDetectionError('Git returned a root outside the current project ancestry.');
    }
    return { root: explicit ? selected : gitRoot, source: 'git', selection: explicit ? 'explicit' : 'git', gitRoot };
  }
  return {
    root: selected, source: 'directory', selection: explicit ? 'explicit' : 'cwd',
    ...(git.status === 'unavailable' ? { note: 'Git is unavailable; using the selected directory as the project root.' } : {}),
  };
}
