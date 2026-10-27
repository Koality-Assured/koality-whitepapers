import fnmatch
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .finding import Finding
from .rules import Ruleset

# Extensions we always skip (binary/media/compiled)
BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".svg",
    ".mp3",
    ".mp4",
    ".wav",
    ".ogg",
    ".webm",
    ".ttf",
    ".woff",
    ".woff2",
    ".eot",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".bz2",
    ".7z",
    ".rar",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".class",
    ".jar",
    ".pyc",
    ".pyo",
    ".map",  # source maps
}

DEFAULT_EXCLUDE_DIRS = frozenset(
    {
        ".git",
        ".svn",
        ".hg",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "venv",
        ".mypy_cache",
        ".tox",
    }
)

# Zip bomb limits
MAX_ZIP_FILES = 5_000
MAX_ZIP_BYTES = 200 * 1024 * 1024  # 200 MB

MAX_FILE_BYTES = 10 * 1024 * 1024  # skip files larger than 10 MB

# Lines longer than this are almost always minified JS/CSS or generated data
# blobs — the primary source of regex catastrophic backtracking. Files with any
# such line are skipped with a MINIFIED_SKIP annotation rather than scanned.
MAX_LINE_LENGTH = 10_000

# Per-file wall-clock guard against pathological regex backtracking. Linux-only
# (signal.alarm); a no-op on platforms without SIGALRM.
PER_FILE_TIMEOUT_SECONDS = 15

INLINE_IGNORE_PATTERN = re.compile(
    r"(?:#|//|<!--|/\*)\s*(?:piiscan|pii):ignore(?:\s*\[(?P<rule>[^\]]+)\])?(?:\s*-->|\s*\*/|\s*$)",
    re.IGNORECASE,
)


@dataclass
class Config:
    source: str  # directory, file, or .zip path
    ruleset: Ruleset
    redact: bool = True
    max_file_bytes: int = MAX_FILE_BYTES
    exclude_dirs: set[str] = field(default_factory=lambda: set(DEFAULT_EXCLUDE_DIRS))


@dataclass
class Result:
    findings: list[Finding] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    files_scanned: int = 0


def _parse_ignore_file(
    ignore_path: Path,
) -> list[tuple[Optional[str], Optional[str]]]:
    """
    Parse a .piiscan-ignore file if present.
    Each line can be:
      - rule_id (e.g. 'ssn-us' or 'pii-scan:ssn-us')
      - file_pattern (e.g. 'testdata/*' or '*.csv')
      - rule_id:file_pattern (e.g. 'ssn-us:testdata/dirty/ssn.csv')
    """
    entries: list[tuple[Optional[str], Optional[str]]] = []
    if not ignore_path.is_file():
        return entries
    try:
        content = ignore_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return entries

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line and not line.startswith("pii-scan:"):
            r, p = line.split(":", 1)
            entries.append((r.strip(), p.strip()))
        elif line.startswith("pii-scan:") and ":" in line[9:]:
            idx = line.find(":", 9)
            r, p = line[:idx], line[idx + 1 :]
            entries.append((r.strip(), p.strip()))
        elif any(ch in line for ch in ("*", "/", "\\", ".")):
            entries.append((None, line))
        else:
            entries.append((line, None))
    return entries


def _is_suppressed(
    rule_id: str,
    rel_path: str,
    line: str,
    ignore_entries: list[tuple[Optional[str], Optional[str]]],
) -> bool:
    """Check if finding on this line/file is suppressed via inline comments or ignore file."""
    # 1. Inline comment check
    m = INLINE_IGNORE_PATTERN.search(line)
    if m:
        target_rule = m.group("rule")
        if not target_rule:
            return True
        target_rule = target_rule.strip()
        bare_id = rule_id.removeprefix("pii-scan:")
        if target_rule in (rule_id, bare_id, "*"):
            return True

    # 2. Ignore file check
    bare_id = rule_id.removeprefix("pii-scan:")
    for rule_pattern, file_pattern in ignore_entries:
        rule_match = (
            rule_pattern is None
            or rule_pattern == "*"
            or rule_pattern in (rule_id, bare_id)
        )
        file_match = (
            file_pattern is None
            or fnmatch.fnmatch(rel_path, file_pattern)
            or fnmatch.fnmatch(Path(rel_path).name, file_pattern)
        )
        if rule_match and file_match:
            return True

    return False


def run(cfg: Config) -> Result:
    """Run the scanner. Returns Result. Never raises — errors go into result.errors."""
    source = Path(cfg.source)
    tmp_dir: Optional[str] = None

    try:
        if source.suffix.lower() == ".zip":
            tmp_dir = tempfile.mkdtemp(prefix="piiscan_")
            scan_dir, error = _extract_zip(source, tmp_dir)
            if error:
                return Result(errors=[error])
            return _scan_directory(scan_dir, cfg)
        elif source.is_file():
            result = Result()
            if source.suffix.lower() in BINARY_EXTENSIONS:
                return result
            if source.stat().st_size > cfg.max_file_bytes:
                result.errors.append(
                    f"skipped {source} (exceeds {cfg.max_file_bytes} bytes)"
                )
                return result

            # Parse potential .piiscan-ignore in parent directory or cwd
            ignore_entries = _parse_ignore_file(source.parent / ".piiscan-ignore")
            if not ignore_entries:
                ignore_entries = _parse_ignore_file(Path.cwd() / ".piiscan-ignore")

            rel_name = source.as_posix() if not source.is_absolute() else source.name
            findings, err = _scan_file(
                source,
                source.parent,
                cfg,
                ignore_entries=ignore_entries,
                force_rel_path=rel_name,
            )
            if err:
                result.errors.append(err)
            else:
                result.findings.extend(findings)
                result.files_scanned = 1
            return result
        else:
            scan_dir = source
            return _scan_directory(scan_dir, cfg)
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def _extract_zip(zip_path: Path, dest: str) -> tuple[Path, Optional[str]]:
    """Extract zip with bomb defense. Returns (dest_path, error_or_None)."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            entries = zf.infolist()
            if len(entries) > MAX_ZIP_FILES:
                return (
                    Path(dest),
                    f"zip has {len(entries)} files, exceeds limit of {MAX_ZIP_FILES}",
                )
            total = sum(e.file_size for e in entries)
            if total > MAX_ZIP_BYTES:
                return (
                    Path(dest),
                    f"zip uncompressed size {total} exceeds limit of {MAX_ZIP_BYTES}",
                )
            for entry in entries:
                # path traversal protection
                target = Path(dest) / entry.filename
                try:
                    target.resolve().relative_to(Path(dest).resolve())
                except ValueError:
                    return (
                        Path(dest),
                        f"zip contains path traversal entry: {entry.filename}",
                    )
            zf.extractall(dest)
    except zipfile.BadZipFile as e:
        return Path(dest), f"bad zip file: {e}"
    return Path(dest), None


def _scan_directory(scan_dir: Path, cfg: Config) -> Result:
    result = Result()
    if not scan_dir.exists():
        result.errors.append(f"source path does not exist: {scan_dir}")
        return result

    ignore_entries = _parse_ignore_file(scan_dir / ".piiscan-ignore")
    if not ignore_entries:
        ignore_entries = _parse_ignore_file(Path.cwd() / ".piiscan-ignore")

    for path in sorted(scan_dir.rglob("*")):
        if not path.is_file():
            continue

        # Skip excluded directory paths (.git, node_modules, etc.)
        rel_parts = set(path.relative_to(scan_dir).parts[:-1])
        if rel_parts & cfg.exclude_dirs:
            continue

        if path.suffix.lower() in BINARY_EXTENSIONS:
            continue
        if path.stat().st_size > cfg.max_file_bytes:
            result.errors.append(f"skipped {path} (exceeds {cfg.max_file_bytes} bytes)")
            continue
        findings, err = _scan_file(path, scan_dir, cfg, ignore_entries=ignore_entries)
        if err:
            result.errors.append(err)
        else:
            result.findings.extend(findings)
            result.files_scanned += 1
    return result


def _scan_file(
    path: Path,
    base_dir: Path,
    cfg: Config,
    ignore_entries: Optional[list[tuple[Optional[str], Optional[str]]]] = None,
    force_rel_path: Optional[str] = None,
) -> tuple[list[Finding], Optional[str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return [], f"could not read {path}: {e}"

    # quick binary sniff: null bytes in first 1024 chars
    if "\x00" in text[:1024]:
        return [], None

    if force_rel_path:
        rel_path = force_rel_path.replace("\\", "/")
    else:
        rel_path = str(path.relative_to(base_dir)).replace("\\", "/")

    # Skip minified/generated blobs — a single very long line is the usual cause
    # of regex catastrophic backtracking, and such files are not human-authored
    # source worth line-level PII review.
    lines = text.splitlines()
    if lines and max(len(line) for line in lines) > MAX_LINE_LENGTH:
        return [], f"MINIFIED_SKIP:{rel_path} (line length > {MAX_LINE_LENGTH})"

    allowlist = cfg.ruleset.allowlist
    findings = []
    file_ext = path.suffix.lower()
    active_ignore_entries = ignore_entries or []

    # Per-file timeout guard (Linux-only). Prevents one pathological file from
    # hanging the whole scan; the partial result for the file is discarded.
    import signal

    def _timeout(_signum, _frame):
        raise TimeoutError(rel_path)

    old_handler = None
    try:
        if hasattr(signal, "SIGALRM"):
            old_handler = signal.signal(signal.SIGALRM, _timeout)
            signal.alarm(PER_FILE_TIMEOUT_SECONDS)

        for lineno, line in enumerate(lines, start=1):
            for rule in cfg.ruleset.rules:
                # Honor rule-level file extension constraints if specified
                if rule.file_extensions:
                    valid_exts = {
                        e.lower() if e.startswith(".") else f".{e.lower()}"
                        for e in rule.file_extensions
                    }
                    if file_ext not in valid_exts:
                        continue

                matches = rule.find_all(line)
                if not matches:
                    continue

                seen_matches_on_line = set()
                rule_id = f"pii-scan:{rule.id}"
                for matched in matches:
                    if matched in seen_matches_on_line:
                        continue
                    seen_matches_on_line.add(matched)

                    # Suppress known-safe values (doc examples, vendor canonical
                    # placeholders, standard payment-network test fixtures).
                    if allowlist.suppresses(matched):
                        continue

                    is_supp = _is_suppressed(
                        rule_id, rel_path, line, active_ignore_entries
                    )
                    redacted = "[REDACTED]" if cfg.redact else matched
                    findings.append(
                        Finding(
                            rule_id=rule_id,
                            source="pii-scan",
                            severity=rule.severity,
                            category=rule.category,
                            cwe=rule.cwe,
                            file=rel_path,
                            line=lineno,
                            summary=rule.summary or rule.description,
                            remediation=rule.remediation,
                            redacted_match=redacted,
                            suppressed=is_supp,
                        )
                    )
    except TimeoutError:
        return [], f"SCAN_TIMEOUT:{rel_path} (exceeded {PER_FILE_TIMEOUT_SECONDS}s)"
    finally:
        if hasattr(signal, "SIGALRM"):
            signal.alarm(0)
            if old_handler is not None:
                signal.signal(signal.SIGALRM, old_handler)

    return findings, None
