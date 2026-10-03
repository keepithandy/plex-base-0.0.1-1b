#!/usr/bin/env node
import { parseArgs } from 'node:util';
import { detectProjectRoot, ProjectDetectionError } from '../repo/detect.js';

const help = `Plex v0.1.0

Usage:
  plex --help
  plex --version
  plex [--repo <directory>] "<implementation request>"

Options:
  -h, --help      Show this help
  -v, --version   Show the version
  --repo <path>   Use this directory as the project boundary

Development status: P1-10 proposed buffers and unified diffs.
Implementation requests are not available yet.
`;

async function main(): Promise<number> {
  let args: ReturnType<typeof parseArgs>;
  try {
    args = parseArgs({
      options: {
        help: { type: 'boolean', short: 'h' },
        version: { type: 'boolean', short: 'v' },
        repo: { type: 'string' },
      },
      allowPositionals: true,
      strict: true,
    });
  } catch (error) {
    console.error(`Plex: ${error instanceof Error ? error.message : 'Invalid arguments'}`);
    console.error('Run plex --help for usage.');
    return 2;
  }

  if (args.values.help) {
    console.log(help);
    return 0;
  }
  if (args.values.version) {
    console.log('Plex v0.1.0');
    return 0;
  }
  if (args.positionals.length === 0) {
    console.log(help);
    return 0;
  }
  if (args.positionals.length !== 1 || !args.positionals[0]?.trim()) {
    console.error('Plex: provide one nonempty implementation request in quotes.');
    return 2;
  }

  try {
    const repo = args.values.repo as string | undefined;
    const project = await detectProjectRoot({ cwd: process.cwd(), ...(repo !== undefined ? { repo } : {}) });
    console.log(`Repository: ${project.root}`);
    console.log(`Detection: ${project.source}; ${project.selection}`);
    if (project.note) console.log(project.note);
    // Keep help/version startup independent of scanner dependencies.
    const { scanProject } = await import('../repo/scan.js');
    const manifest = await scanProject(project);
    console.log(`Source files: ${manifest.files.length}`);
    for (const file of manifest.files) console.log(`  ${file.path} (${file.sizeBytes} bytes)`);
    const { rankCandidates } = await import('../repo/rank.js');
    const ranking = await rankCandidates(args.positionals[0]!, manifest);
    console.log('Candidate ranking:');
    for (const [index, candidate] of ranking.candidates.slice(0, 10).entries()) {
      console.log(`  ${index + 1}. ${candidate.path} — ${candidate.score} points`);
      for (const reason of candidate.reasons) console.log(`     +${reason.points} ${reason.detail}`);
    }
    if (ranking.status === 'insufficient_context') {
      console.error(`Plex: INSUFFICIENT CONTEXT — ${ranking.reason}`);
      return 1;
    }
    console.log(`Selected: ${ranking.selectedPaths.join(', ')}`);
    const { buildContext } = await import('../context/build.js');
    const context = await buildContext(args.positionals[0]!, manifest, ranking);
    console.log(`Context: ${context.snapshots.length} file; estimated input ${context.budget.inputTokens}/${context.budget.inputLimitTokens} tokens`);
    console.log('Runtime token verification: pending');
    for (const snapshot of context.snapshots) console.log(`Snapshot: ${snapshot.path}; SHA-256 ${snapshot.sha256}`);
  } catch (error) {
    if (error instanceof Error && error.name === 'ContextError'
      && ['budget_exceeded', 'insufficient_context'].includes((error as Error & { code: string }).code)) {
      console.error(`Plex: INSUFFICIENT CONTEXT — ${error.message}`);
      return 1;
    }
    const scannerError = error instanceof Error && ['RepositoryScanError', 'RankingError', 'ContextError'].includes(error.name);
    console.error(`Plex: ${error instanceof ProjectDetectionError || scannerError ? error.message : 'Project discovery failed.'}`);
    return 1;
  }

  console.error('Plex: implementation requests are not available yet.');
  return 1;
}

process.exitCode = await main();
