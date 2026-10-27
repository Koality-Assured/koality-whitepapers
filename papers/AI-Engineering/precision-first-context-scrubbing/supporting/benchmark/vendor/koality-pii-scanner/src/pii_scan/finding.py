from dataclasses import asdict, dataclass, field


@dataclass
class Finding:
    rule_id: str  # e.g. "pii-scan:ssn-us"
    source: str = "pii-scan"
    severity: str = "critical"
    category: str = "pii"
    cwe: list[str] = field(default_factory=list)
    file: str = ""
    line: int = 0
    summary: str = ""
    remediation: str = ""
    redacted_match: str = ""  # "[REDACTED]" when --redact; actual value otherwise
    suppressed: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        # omit empty optional fields to keep output clean
        return {
            k: v
            for k, v in d.items()
            if v not in (False, "", [], 0) or k in ("line", "source")
        }


def is_pii_finding(f: Finding) -> bool:
    """Returns True if the finding is PII-related by category or CWE."""
    return f.category == "pii" or "CWE-359" in f.cwe
