import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { resolveSafeExportPath } from './exporter.mjs';

test('allows normal relative export path', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'export-ok-'));
  const baseDir = path.join(tmp, 'exports');
  fs.mkdirSync(baseDir, { recursive: true });
  const resolved = resolveSafeExportPath(baseDir, 'report.json');
  assert.equal(resolved, path.join(baseDir, 'report.json'));
});

test('repro sibling-prefix directory escape bypasses startsWith check', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'export-esc-'));
  const baseDir = path.join(tmp, 'exports');
  const siblingSecretDir = path.join(tmp, 'exports-secrets');
  fs.mkdirSync(baseDir, { recursive: true });
  fs.mkdirSync(siblingSecretDir, { recursive: true });
  fs.writeFileSync(path.join(siblingSecretDir, 'token.txt'), 'secret-fixture', 'utf8');

  assert.throws(() => {
    resolveSafeExportPath(baseDir, '../exports-secrets/token.txt');
  }, /escapes/i);
});
