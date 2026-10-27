#!/usr/bin/env python3
"""Synthetic test fixtures and corpus loader for Precision-First Context Scrubbing.

Provides:
- Labeled ground-truth corpus loader (101 synthetic cases across 6 evaluated categories).
- Naive regex baseline definitions representing unvalidated heuristic scanners.
- Synthetic developer codebase fixtures (code, config, mock tests, and minified bundles).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS_FILE = HERE / "corpus" / "labeled.jsonl"


@dataclass
class CorpusCase:
    case_id: str
    text: str
    rules: list[str]


def load_corpus() -> list[CorpusCase]:
    """Load the 101 synthetic ground-truth cases."""
    if not CORPUS_FILE.exists():
        raise FileNotFoundError(f"Corpus file not found: {CORPUS_FILE}")
    cases = []
    for line in CORPUS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        data = json.loads(line)
        cases.append(CorpusCase(case_id=data["case_id"], text=data["text"], rules=data.get("rules", [])))
    return cases


def get_naive_regex_rules() -> dict[str, re.Pattern]:
    """Common naive regexes used by unvalidated pre-commit hooks and basic scanners."""
    return {
        "credit-card": re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
        "ssn-us": re.compile(r"\b\d{3}[- ]?\d{2}[- ]?\d{4}\b"),
        "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
        "ipv4": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
        "ipv6": re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"),
        "mac-address": re.compile(r"\b(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}\b"),
    }


def generate_synthetic_code_workload() -> dict[str, str]:
    """Generate a benign five-file workload from reserved examples and documented test values."""
    files = {}

    # File 1: Server Config (contains local IPs, test emails, and port numbers)
    files["src/config.ts"] = """
export const serverConfig = {
  host: "127.0.0.1",
  port: 8080,
  internalGateway: "10.0.0.1",
  adminNotificationEmail: "dev-null@example.com",
  metricsCollector: "192.168.1.254",
  dnsFallback: "203.0.113.53", // RFC 5737 TEST-NET documentation address
  debugFlag: 123456789,
};
""".strip()

    # File 2: Payment Gateway Test Fixture (contains Luhn test cards and documentation samples)
    files["tests/payment.test.ts"] = """
import { processPayment } from "../src/payment";

describe("Payment Gateway", () => {
  it("rejects documentation test cards", async () => {
    // Stripe documents test cards as fake; see the source log.
    await expect(processPayment({ card: "4242424242424242" })).rejects.toThrow();
  });

  it("handles test order references", () => {
    const orderId = 472301234;
    expect(orderId).toBeGreaterThan(0);
  });
});
""".strip()

    # File 3: Network Utilities (contains loopback, documentation IP ranges, and version constants)
    files["src/utils/network.ts"] = """
export const ROUTE_MAP = {
  loopback: "127.0.0.1",
  testNet1: "192.0.2.1",
  testNet2: "198.51.100.9",
  testNet3: "203.0.113.9",
  versionString: "203.0.113.9", // RFC 5737 documentation address; no global-IP collision is tested
};
""".strip()

    # File 4: Minified Webpack Asset (>10,000 character single line)
    minified_chunk = "var _0x1a=['log','init','env'];" + "(function(_0x2b,_0x3c){return _0x2b[_0x3c];})('test',0);" * 400
    files["dist/bundle.min.js"] = f"/* bundle v1.0.0 */\n{minified_chunk}\n// end of bundle\n"

    # File 5: Benign log stream (uses only reserved domains, invalid SSNs, and Stripe test cards)
    files["logs/auth_failure.log"] = """
[2026-10-27T10:14:01Z] [ERROR] User auth failure for email qa@example.net
[2026-10-27T10:14:02Z] [DEBUG] Verified ssn 000-12-3456 failed identity verification check
[2026-10-27T10:14:03Z] [WARN] Billing card 4242424242424242 declined by issuing bank
[2026-10-27T10:14:04Z] [INFO] Originating public IP address was 203.0.113.7
""".strip()

    return files


def get_workload_ground_truth() -> set[tuple[str, int, str]]:
    """The generated workload contains no real identifiers; no findings are expected."""
    return set()
