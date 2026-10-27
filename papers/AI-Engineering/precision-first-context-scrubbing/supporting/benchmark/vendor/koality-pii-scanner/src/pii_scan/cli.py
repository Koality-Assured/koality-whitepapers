import json
import sys
from pathlib import Path

import click

from . import __version__
from .exit_codes import CLEAN, ERROR
from .finding import Finding
from .rules import default_ruleset, load
from .sarif import render_sarif
from .scanner import Config, run


def _render_table(findings: list[Finding]) -> str:
    if not findings:
        return "No findings."
    rows = [f"  {'FILE':<40} {'LINE':>5}  {'SEVERITY':<10}  RULE ID"]
    rows.append("  " + "-" * 80)
    for f in findings:
        sev = f.severity.upper()
        if f.suppressed:
            sev = f"{sev} (SUPPRESSED)"
        rows.append(f"  {f.file:<40} {f.line:>5}  {sev:<18}  {f.rule_id}")
        rows.append(f"    {f.summary}")
        if f.redacted_match:
            rows.append(f"    Match: {f.redacted_match}")
        rows.append("")
    return "\n".join(rows)


@click.group()
@click.version_option(__version__, prog_name="koality-pii-scan")
def main():
    """Koality PII Scanner -- deterministic PII and credential detection."""


@main.command()
@click.option("--source", required=True, help="Directory, file, or .zip path to scan.")
@click.option(
    "--report-format",
    default="json",
    type=click.Choice(["json", "table", "sarif"]),
    show_default=True,
    help="Output format: json, table, or sarif.",
)
@click.option(
    "--report-path",
    default="-",
    show_default=True,
    help="Output file path. Use '-' for stdout.",
)
@click.option(
    "--redact/--no-redact",
    default=True,
    show_default=True,
    help="Redact matched values in output.",
)
@click.option(
    "--exit-code",
    default=1,
    type=click.IntRange(0, 2),
    show_default=True,
    help="Exit code to return when unsuppressed findings are found. 0 disables exit-on-findings.",
)
@click.option(
    "--rules",
    default=None,
    type=click.Path(exists=True),
    help="Path to custom rules YAML. Defaults to embedded ruleset.",
)
def detect(source, report_format, report_path, redact, exit_code, rules):
    """Scan a directory, file, or zip archive for PII and credential patterns."""
    # Load ruleset
    try:
        if rules:
            ruleset = load(Path(rules).read_bytes())
        else:
            ruleset = default_ruleset()
    except Exception as e:
        click.echo(f"error: failed to load rules: {e}", err=True)
        sys.exit(ERROR)

    # Run scanner
    try:
        result = run(Config(source=source, ruleset=ruleset, redact=redact))
    except Exception as e:
        click.echo(f"error: scanner failed: {e}", err=True)
        sys.exit(ERROR)

    for err in result.errors:
        click.echo(f"warning: {err}", err=True)

    # Render output
    if report_format == "json":
        output = json.dumps([f.to_dict() for f in result.findings], indent=2)
    elif report_format == "sarif":
        output = render_sarif(result.findings, ruleset)
    else:
        output = _render_table(result.findings)

    if report_path == "-":
        click.echo(output)
    else:
        Path(report_path).write_text(output, encoding="utf-8")
        click.echo(f"Report written to {report_path}", err=True)

    active_findings = [f for f in result.findings if not f.suppressed]
    suppressed_count = len(result.findings) - len(active_findings)

    summary_msg = (
        f"Scanned {result.files_scanned} file(s). "
        f"Found {len(result.findings)} finding(s)"
    )
    if suppressed_count > 0:
        summary_msg += (
            f" ({len(active_findings)} active, {suppressed_count} suppressed)."
        )
    else:
        summary_msg += "."

    click.echo(summary_msg, err=True)

    if active_findings and exit_code != CLEAN:
        sys.exit(exit_code)
    sys.exit(CLEAN)
