import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { hashFixture, webFixture } from '../helpers/web-fixture.mjs';

test('web fixture contains exactly three files matching the recorded SHA-256 baseline', async () => {
  const hashes = await hashFixture();
  assert.deepEqual(Object.keys(hashes), ['app.js', 'index.html', 'style.css']);
  const baseline = JSON.parse(await readFile(new URL('../fixtures/simple-web-project.sha256.json', import.meta.url), 'utf8'));
  assert.deepEqual(hashes, baseline);
});

test('web fixture starts with one Example title in the head and local CSS/JS references', async () => {
  const html = await readFile(join(webFixture, 'index.html'), 'utf8');
  // Exact assertions for this controlled fixture. General HTML validation is P1-11.
  const titles = [...html.matchAll(/<title>([^<]*)<\/title>/g)];
  assert.equal(titles.length, 1);
  assert.equal(titles[0][1], 'Example');
  const head = html.match(/<head>([\s\S]*?)<\/head>/)?.[1];
  assert.ok(head);
  assert.ok(head.includes('<title>Example</title>'));
  assert.ok(head.includes('<link rel="stylesheet" href="style.css">'));
  assert.ok(head.includes('<script src="app.js" defer></script>'));
});
