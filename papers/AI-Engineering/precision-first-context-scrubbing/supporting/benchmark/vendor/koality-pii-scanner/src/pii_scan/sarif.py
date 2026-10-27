import json
from typing import Any

from . import __version__
from .finding import Finding
from .rules import Ruleset

_SEVERITY_TO_SARIF_LEVEL = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
    "info": "note",
}


def _map_severity(sev: str) -> str:
    return _SEVERITY_TO_SARIF_LEVEL.get(sev.lower(), "warning")


def render_sarif(findings: list[Finding], ruleset: Ruleset) -> str:
    """Render findings as a valid SARIF v2.1.0 JSON string."""
    sarif_rules: list[dict[str, Any]] = []
    seen_rules = set()

    for r in ruleset.rules:
        rule_id = f"pii-scan:{r.id}"
        if rule_id in seen_rules:
            continue
        seen_rules.add(rule_id)
        rule_def: dict[str, Any] = {
            "id": rule_id,
            "name": r.id,
            "shortDescription": {"text": r.summary or r.description},
            "defaultConfiguration": {"level": _map_severity(r.severity)},
            "properties": {
                "category": r.category,
                "confidence": r.confidence,
                "cwe": r.cwe,
            },
        }
        if r.remediation:
            rule_def["help"] = {"text": r.remediation}
        sarif_rules.append(rule_def)

    results: list[dict[str, Any]] = []
    for f in findings:
        res: dict[str, Any] = {
            "ruleId": f.rule_id,
            "level": _map_severity(f.severity),
            "message": {"text": f.summary or f.rule_id},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": f.file, "uriBaseId": "%SRCROOT%"},
                        "region": {"startLine": max(1, f.line)},
                    }
                }
            ],
        }
        if f.suppressed:
            res["suppressions"] = [{"kind": "inSource"}]
        results.append(res)

    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "koality-pii-scanner",
                        "semanticVersion": __version__,
                        "informationUri": "https://github.com/Koality-Assured/koality-pii-scanner",
                        "rules": sarif_rules,
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(sarif, indent=2)
