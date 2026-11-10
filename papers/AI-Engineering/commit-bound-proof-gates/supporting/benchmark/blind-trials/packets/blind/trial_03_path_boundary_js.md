# Blind Review Packet: trial_03_path_boundary_js

**Arm:** `blind` (specification + raw diff only; author rationale withheld)

## Specification
1. `resolveSafeExportPath(baseDir, requestedPath)` must strictly confine the resolved target inside `baseDir`.
2. Any attempt to escape `baseDir` via relative traversal (`..`), sibling directory prefixes (e.g., `../exports-secrets/...`), or absolute paths outside `baseDir` must throw an Error.

## Diff Under Review

```diff
--- /dev/null
+++ b/exporter.mjs
@@ -0,0 +1,16 @@
+import fs from 'node:fs';
+import path from 'node:path';
+
+export function resolveSafeExportPath(baseDir, requestedPath) {
+  const root = path.resolve(baseDir);
+  const candidate = path.resolve(root, requestedPath);
+
+  if (!candidate.startsWith(root)) {
+    throw new Error(`Path escapes export directory: ${requestedPath}`);
+  }
+  return candidate;
+}
+
+export function readExportArtifact(baseDir, requestedPath) {
+  const safePath = resolveSafeExportPath(baseDir, requestedPath);
+  return fs.readFileSync(safePath, 'utf8');
+}
--- /dev/null
+++ b/exporter.test.mjs
@@ -0,0 +1,12 @@
+import test from 'node:test';
+import assert from 'node:assert/strict';
+import path from 'node:path';
+import { resolveSafeExportPath } from './exporter.mjs';
+
+test('allows normal relative export path and rejects parent traversal', () => {
+  const baseDir = path.resolve('/tmp/exports');
+  assert.equal(resolveSafeExportPath(baseDir, 'report.json'), path.join(baseDir, 'report.json'));
+  assert.throws(() => resolveSafeExportPath(baseDir, '../../etc/passwd'), /escapes/);
+});
```

## Review Prompt
Audit the diff strictly against the specification. Return:
1. `VERDICT`: `PASS` or `BLOCK`
2. Concrete defects (if any) with file/line, failure trace, and required fix.
