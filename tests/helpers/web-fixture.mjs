import { createHash } from 'node:crypto';
import { readFile, readdir } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const webFixture = fileURLToPath(new URL('../../fixtures/simple-web-project/', import.meta.url));

// Test-only snapshot helper; this is not the production repository scanner.
export async function hashFixture(directory = webFixture) {
  const entries = await readdir(directory, { withFileTypes: true });
  const hashes = {};
  for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name, 'en'))) {
    if (!entry.isFile()) throw new Error(`Unexpected fixture entry: ${entry.name}`);
    const bytes = await readFile(join(directory, entry.name));
    hashes[entry.name] = createHash('sha256').update(bytes).digest('hex');
  }
  return hashes;
}
