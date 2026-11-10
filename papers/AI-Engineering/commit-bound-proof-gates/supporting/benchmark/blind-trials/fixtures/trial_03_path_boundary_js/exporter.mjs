import fs from 'node:fs';
import path from 'node:path';

export function resolveSafeExportPath(baseDir, requestedPath) {
  const root = path.resolve(baseDir);
  const candidate = path.resolve(root, requestedPath);

  if (!candidate.startsWith(root)) {
    throw new Error(`Path escapes export directory: ${requestedPath}`);
  }
  return candidate;
}

export function readExportArtifact(baseDir, requestedPath) {
  const safePath = resolveSafeExportPath(baseDir, requestedPath);
  return fs.readFileSync(safePath, 'utf8');
}
