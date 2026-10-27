import re
from dataclasses import dataclass, field
from importlib.resources import files
from typing import Optional

import yaml

from .validators import validate


@dataclass
class Rule:
    id: str
    description: str
    pattern: str
    confidence: str  # high/medium/low
    severity: str
    category: str
    cwe: list[str] = field(default_factory=list)
    summary: str = ""
    remediation: str = ""
    file_extensions: list[str] = field(default_factory=list)  # empty = all text files
    _compiled: Optional[re.Pattern] = field(default=None, repr=False, compare=False)

    def compile(self) -> None:
        self._compiled = re.compile(self.pattern)

    def _matches(self, line: str):
        """Yield the full text of each match that passes the rule's validator.

        A rule may capture the value to validate in group 1 (for example the nine
        digits of a contiguous SSN that is only recognised next to a keyword);
        otherwise the whole match is validated.
        """
        if self._compiled is None:
            self.compile()
        for m in self._compiled.finditer(line):
            candidate = m.group(1) if m.re.groups and m.group(1) is not None else None
            if validate(self.id, candidate if candidate is not None else m.group(0)):
                yield m.group(0)

    def match(self, line: str) -> Optional[str]:
        """Returns the first validated matched string or None."""
        return next(self._matches(line), None)

    def find_all(self, line: str) -> list[str]:
        """Returns all validated matched substrings in the line."""
        return list(self._matches(line))


@dataclass
class Allowlist:
    """
    Known-safe matched values that should never be reported as findings:
    documentation examples, vendor canonical placeholders, and standard
    payment-network test fixtures. Suppression is applied to a rule's matched
    text (not the whole line), so it reduces false positives without weakening
    detection of real values that merely appear nearby.

    A matched value is suppressed when it equals a `literals` entry (exact) or
    is fully/partially matched by an allowlist `patterns` regex.
    """

    literals: frozenset[str] = field(default_factory=frozenset)
    patterns: list[re.Pattern] = field(default_factory=list)

    def suppresses(self, matched: str) -> bool:
        if matched in self.literals:
            return True
        # Formatted card numbers (4111-1111-1111-1111) match their contiguous form.
        digits = re.sub(r"[-\s]", "", matched)
        if digits != matched and digits.isdigit() and digits in self.literals:
            return True
        return any(p.search(matched) for p in self.patterns)


@dataclass
class Ruleset:
    version: str
    rules: list[Rule]
    allowlist: Allowlist = field(default_factory=Allowlist)


def load(data: bytes | str) -> Ruleset:
    """Parse YAML bytes/str and return a compiled Ruleset. Raises ValueError on bad regex."""
    raw = yaml.safe_load(data)
    rules = []
    for r in raw.get("rules", []):
        rule = Rule(
            id=r["id"],
            description=r.get("description", ""),
            pattern=r["pattern"],
            confidence=r.get("confidence", "medium"),
            severity=r.get("severity", "medium"),
            category=r.get("category", "pii"),
            cwe=r.get("cwe", []),
            summary=r.get("summary", r.get("description", "")),
            remediation=r.get("remediation", ""),
            file_extensions=r.get("file_extensions", []),
        )
        try:
            rule.compile()
        except re.error as e:
            raise ValueError(
                f"Rule '{rule.id}' has invalid regex '{rule.pattern}': {e}"
            ) from e
        rules.append(rule)
    return Ruleset(
        version=raw.get("version", "0"),
        rules=rules,
        allowlist=_load_allowlist(raw.get("allowlist", {}) or {}),
    )


def _load_allowlist(raw: dict) -> Allowlist:
    """Parse the optional `allowlist:` YAML block. Raises ValueError on bad regex."""
    literals = frozenset(raw.get("literals", []) or [])
    patterns = []
    for p in raw.get("patterns", []) or []:
        try:
            patterns.append(re.compile(p))
        except re.error as e:
            raise ValueError(f"Allowlist pattern '{p}' is invalid regex: {e}") from e
    return Allowlist(literals=literals, patterns=patterns)


def default_ruleset() -> Ruleset:
    """Load the embedded default ruleset."""
    data = files("pii_scan.data").joinpath("default.yaml").read_bytes()
    return load(data)
