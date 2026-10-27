# Precision-first context scrubbing: measuring synthetic format-marker detection and finding-output size

## Abstract

Autonomous artificial intelligence agents may inspect source files, logs, and configuration through tools that return content to a model context. A broad, unvalidated pattern can flag benign test or documentation values as sensitive; this paper evaluates that possibility using reserved and documented synthetic fixtures rather than live personal data.

In an autonomous agent toolchain, a false-positive finding may consume context and could prompt unnecessary changes. This paper treats those as possible workflow costs; the benchmark measures scanner findings and serialized output, not human or agent behavior.

This paper evaluates **precision-first context scrubbing** implemented in `koality-pii-scanner` using a synthetic format-test corpus and a separate all-negative developer-file workload. The benchmark compares deterministic validation with simple regex baselines, reports serialized finding sizes, and records scan-call timings and overlength-line skip behavior. It does not measure detection of actual personal data, agent task quality, or ReDoS resistance.

Across 101 labeled format-test and negative-control cases, the deterministic scanner produced 8 true-positive format-marker findings, 1 false positive, and 8 false negatives (aggregate precision 0.8889; recall 0.5000). The simple regex baseline produced 16 true positives and 46 false positives (precision 0.2581; recall 1.0000). The positives are documented fake payment-card test values and documentation-range MAC addresses, not live personal data; no positive email, SSN, IPv4, or IPv6 cases were included. In a separate five-file all-negative workload, the baseline emitted 17 findings (912 JSON tokens) while the deterministic scanner emitted none (1 JSON token). One run on a host reported as `Windows-10-10.0.26200-SP0` measured 6,253.6 lines/second across 10,000 synthetic lines, a 7.48 ms scan call for a 100-line input, and a 46.656 ms call that skipped an overlength line. These timings are environment-specific observations, not latency guarantees or evidence about ReDoS behavior.

---

## 1. Thesis, research questions, audience, and structure

**Thesis.** False-positive findings can add irrelevant material to an agent's tool context. This benchmark measures findings and serialized output on synthetic inputs; it does not establish an effect on agent behavior. Its results show a trade-off on the tested format markers: the deterministic scanner has higher aggregate precision and lower recall than the simple regex baseline.

**Research questions.**
1. What is the empirical error rate of standard heuristic regular expressions when applied to developer source code, mock fixtures, and configuration files?
2. How do structural validators affect precision and recall on the documented synthetic format markers and negative controls?
3. How does the serialized JSON finding size differ on one synthetic all-negative file workload, using `tiktoken` `o200k_base`?
4. What scan-call timings and line-length skip behavior are observed in one local run, and what limits do those measurements have?

**Audience.** Systems architects, security engineers, AI platform teams, and developers building autonomous coding harnesses, pre-commit security gates, and Model Context Protocol (MCP) data-protection layers.

---

## 2. The false-positive asymmetry in autonomous AI agents

In a human-reviewed workflow, a developer can inspect a suspected sensitive-data finding and decide whether it represents a real issue. For example, `127.0.0.1` is a loopback address, while Stripe documents its test-card values as fake. The time and cost of human review are not measured here.

In autonomous agent systems, findings from a pre-commit check or automated scan may be serialized into a tool response. The example below is an illustrative scenario, not a measured agent interaction or benchmark result.

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Illustrative false-positive scenario (not measured by this benchmark)  │
│                                                                        │
│ 1. Naive Scanner scans codebase containing:                            │
│    const host = "127.0.0.1"; const ssn = "000-12-3456";               │
│                                                                        │
│ 2. Scanner fires 2 Critical False Positives:                           │
│    - "Public IPv4 leak detected: 127.0.0.1"                            │
│    - "US SSN leak detected: 000-12-3456"                               │
│                                                                        │
│ 3. Tool result adds an illustrative amount of output to context        │
│                                                                        │
│ 4. Agent attempts remediation:                                         │
│    - Replaces "127.0.0.1" with "[REDACTED]" (breaks local test server) │
│    - Replaces testOrder with "[REDACTED]" (causes TypeScript error)    │
│                                                                        │
│ 5. Test Suite fails ──► Agent enters hallucinatory repair loop         │
└────────────────────────────────────────────────────────────────────────┘
```

This scenario illustrates potential workflow costs; the benchmark does not measure these effects:

1. **Context Window Use:** A finding's serialized representation consumes tokens. The size depends on the finding format and count; this release measures one all-negative workload and does not extrapolate to larger repositories.
2. **Potential remediation errors:** An agent could act on a false finding and alter a valid test value or configuration. This release does not test whether an agent does so.
3. **Potential workflow interruption:** If an agent's changes are based on a false finding, later checks could fail and require additional work. This release does not measure task completion or repair loops.
4. **Regex runtime risk:** Some regexes can have problematic runtime on crafted inputs. This release does not run an unbounded regex or measure ReDoS behavior; the line-length skip observation below is not a ReDoS test.

These possible workflow costs motivate measuring both precision and recall; neither metric alone establishes that a scanner is suitable for a particular workflow.

---

## 3. Deterministic architecture: structural validation and contextual anchoring

The pinned `koality-pii-scanner` source combines regular-expression candidate matching with structural checks, contextual rules, and token-scoped allowlists. The benchmark below measures outcomes on its stated synthetic fixtures; it does not establish that the architecture eliminates all false alarms or preserves detection of live data.

```text
Input Source Line
       │
       ▼ Pre-Scan Boundary Check (line length <= 10,000 chars?)
  [ > 10,000 chars: Emit MINIFIED_SKIP and halt backtracking ]
       │
       ▼ Pattern Candidate Match (Regex finditer)
Candidate Extracted Token
       │
       ├───────────────────────────────────────────────────────┐
       ▼                                                       ▼
Payment Card Detector                                   IPv4/IPv6 Detector
  1. Length check (13-19 digits)                          1. Parse with ipaddress module
  2. IIN network prefix check                             2. Enforce addr.is_global
  3. Modulus-10 Luhn checksum                             3. Filter multicast, loopback, CGNAT
       │                                                  4. Filter RFC 5737 / 3849 documentation
       ├───────────────────────────────────────────────────────┘
       ▼
Allowlist Filter (Literals & Pattern Match)
  - Matches test card fixtures (4111-1111-1111-1111)
  - Matches RFC 2606 reserved domains (example.com)
  - Matches vendor documentation sample keys
       │
       ▼
Emitted Finding (Clean, Actionable, Validated)
```

### 3.1 Credit Card Validation (`is_valid_credit_card`)

A naive payment card regex matching `\b(?:\d[ -]*?){13,19}\b` fires on arbitrary numeric sequences, such as internal serial numbers, git commit hashes composed of digits, and tracking numbers.

The deterministic validator enforces a three-stage filter:
1. **Length Boundaries:** Strips spaces and hyphens, verifying that the contiguous digit count is strictly between 13 and 19 characters ($13 \le \text{len} \le 19$).
2. **Issuer Identification Number (IIN / BIN) Verification:** Validates that the leading prefix corresponds to an allocated payment network per ISO/IEC 7812:
   - Visa: `4`
   - Mastercard: `51–55` or `2221–2720`
   - American Express: `34` or `37`
   - Diners Club: `300–305`, `36`, `38`, `39`
   - JCB: `3528–3589`
   - Discover: `6011`, `65`, `644–649`, or UnionPay co-brand `622126–622925`
3. **Modulus-10 Luhn Checksum:** Enforces the standard Luhn algorithm over the reversed digit sequence $d_0, d_1, \dots, d_{n-1}$:
   $$S = \sum_{i=0}^{n-1} f(d_i, i), \quad \text{where } f(d, i) = \begin{cases} d & \text{if } i \equiv 0 \pmod 2 \\ 2d - 9 & \text{if } i \equiv 1 \pmod 2 \text{ and } 2d > 9 \\ 2d & \text{if } i \equiv 1 \pmod 2 \text{ and } 2d \le 9 \end{cases}$$
   The candidate is accepted if and only if $S \equiv 0 \pmod{10}$.

### 3.2 US Social Security Number Validation (`is_valid_ssn`)

US Social Security Numbers consist of nine digits divided into Area (3 digits), Group (2 digits), and Serial (4 digits). Following the Social Security Administration's 2011 randomization standard, valid numbers must satisfy strict structural constraints:
- $\text{Area} \notin \{000, 666, 900\dots999\}$
- $\text{Group} \ne 00$
- $\text{Serial} \ne 0000$

Hyphenated (`000-12-3456`) or space-delimited (`000 12 3456`) formats provide layout signals, while unformatted nine-digit sequences can also be identifiers, timestamps, or hash fragments. The rule specification in `rules.py` applies **contextual keyword anchoring** to unformatted candidates: `ssn` or `social security` must appear within 20 non-digit characters. The example values use SSA-invalid area 000, as documented in `supporting/SOURCES.md`.

### 3.3 Network Address Validation (`is_valid_ipv4` and `is_valid_ipv6`)

In developer codebases, IP addresses appear primarily as configuration targets, loopback bindings, local subnet definitions, and documentation examples. Reporting `127.0.0.1` or `192.168.1.1` as a sensitive security leak is actively harmful.

The validator uses Python's `ipaddress` module to enforce **globally routable unicast verification**:
$$\text{Valid}(\text{IP}) \iff \text{IP.is\_global} \land \neg \text{IP.is\_multicast} \land \text{IP} \notin \mathcal{S}_{\text{ignored}}$$

This automatically and mathematically filters:
- RFC 1918 Private subnets: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
- Loopback addresses: `127.0.0.0/8` and `::1`
- Link-local addresses: `169.254.0.0/16` and `fe80::/10`
- Shared address space (CGNAT): `100.64.0.0/10`
- Documentation prefixes: RFC 5737 IPv4 (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) and RFC 3849 IPv6 (`2001:db8::/32`)
- Common public DNS resolvers and placeholders: `8.8.8.8`, `8.8.4.4`, `1.1.1.1`, `1.0.0.1`, `9.9.9.9`, `1.2.3.4`

### 3.4 Email & Reserved Domain Suppression

Email addresses are validated to match standard RFC 5322 structure, but the rule excludes:
- RFC 2606 / RFC 6761 reserved top-level and second-level domains: `.test`, `.example`, `.invalid`, `.localhost`, `example.com`, `example.org`, `example.net`.
- Scp-style git remotes (e.g. `git@github.com:...`).

### 3.5 Token-Scoped Allowlisting vs. Whole-Line Suppression

Common security tools suppress findings by skipping entire lines or ignoring whole files. This creates a critical blind spot: if an attacker or developer places a real credential on the same line as a test fixture, line-level suppression blinds the scanner.

`koality-pii-scanner` implements `Allowlist.suppresses(matched: str)`, which checks whether the **specific extracted token** matches an allowlisted literal or pattern. If a test card `4111-1111-1111-1111` appears alongside a real Visa PAN, the test fixture is suppressed while the legitimate leak is reported.

### 3.6 Minified Asset Boundary and ReDoS Limits

The scanner enforces `MAX_LINE_LENGTH = 10_000`; an overlength line is skipped and recorded with a `MINIFIED_SKIP` diagnostic before rule evaluation. The benchmark confirms this behavior for one 24 KB test line. It does not test a vulnerable regex without this boundary, establish an asymptotic runtime bound, or prove that ReDoS is eliminated.

---

## 4. Empirical evaluation: labeled corpus confusion matrix

To evaluate format-marker detection, we executed an offline benchmark comparing the pinned `koality-pii-scanner` snapshot against simple regex baselines across the 101 cases in `supporting/benchmark/corpus/labeled.jsonl`.

The corpus contains **101 cases: 85 negative controls and 16 positive format-test markers**. The positives are 13 fake test-card values documented by Stripe and 3 MAC addresses from the IANA documentation range described by RFC 9542. Negative controls include invalid card/SSN forms, reserved example domains, and private or documentation IP/MAC values. No positive email, SSN, IPv4, or IPv6 case is present. Labels mean only that the documented marker has the tested format; they do not mean that the value represents a live person or account.

### 4.1 Comparative Results Table

The table reports per-detector True Positives (TP), False Positives (FP), False Negatives (FN), Precision ($P$), and Recall ($R$). Precision or recall is marked `n/a` when the fixture set does not provide the positive or predicted-positive cases needed to define it.

| Detector (`rule_id`) | Positive cases | Det. TP | Det. FP | Det. FN | Det. Precision | Det. Recall | Naive TP | Naive FP | Naive FN | Naive Precision | Naive Recall |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `credit-card` | 13 | 5 | 0 | 8 | 1.0000 | 0.3846 | 13 | 10 | 0 | 0.5652 | 1.0000 |
| `ssn-us` | 0 | 0 | 0 | 0 | n/a | n/a | 0 | 8 | 0 | 0.0000 | n/a |
| `email` | 0 | 0 | 0 | 0 | n/a | n/a | 0 | 8 | 0 | 0.0000 | n/a |
| `ipv4` | 0 | 0 | 0 | 0 | n/a | n/a | 0 | 15 | 0 | 0.0000 | n/a |
| `ipv6` | 0 | 0 | 0 | 0 | n/a | n/a | 0 | 2 | 0 | 0.0000 | n/a |
| `mac-address` | 3 | 3 | 1 | 0 | 0.7500 | 1.0000 | 3 | 3 | 0 | 0.5000 | 1.0000 |
| **OVERALL AGGREGATE** | **16** | **8** | **1** | **8** | **0.8889** | **0.5000** | **16** | **46** | **0** | **0.2581** | **1.0000** |

```text
Aggregate Precision Comparison (synthetic corpus)
Deterministic scanner: 0.8889
Naive regex baseline:  0.2581
```

### 4.2 Error Analysis of Naive Regular Expressions

On this fixture set, the naive baseline produced 46 false positives: 10 card-shaped matches, 8 SSN-shaped matches, 8 email matches, 15 IPv4 matches, 2 IPv6 matches, and 3 MAC matches. The deterministic scanner produced 1 false positive (a MAC-address case) and missed 8 of the 13 positive card-format markers. Because four categories have no positive cases, their recall is undefined; their negative-only results do not establish recall for those detectors. These counts characterize only the included fixtures and these particular regex patterns.

---

## 5. Context window efficiency and multi-file workload analysis

To compare finding-output size, we constructed a five-file synthetic developer workload containing reserved example domains, private and documentation IP addresses, invalid SSN-shaped text, a documented fake Stripe card, test order numbers, and one generated overlength asset. Its ground truth is all-negative: no findings are expected. It contains no live personal data or credentials.

### 5.1 Token Consumption Measurements

When scanner results are serialized into tool response payloads for agent consumption, false positives directly inflate token counts. We measured the token footprint using `tiktoken` with OpenAI's `o200k_base` tokenizer:

| Metric | Naive Regex Engine | Deterministic Scanner | Delta / Savings |
| :--- | :---: | :---: | :---: |
| **Findings emitted** | 17 | 0 | 17 fewer findings |
| **False-positive findings** | 17 | 0 | 17 fewer on this all-negative workload |
| **Serialized finding JSON tokens** | 912 | 1 | 911 fewer tokens (99.89%) |

On this one all-negative workload, the deterministic scanner emitted no findings and its serialized JSON output used 1 token, compared with 17 false-positive findings and 912 tokens for the baseline. This is a finding-payload size comparison on synthetic fixtures; it does not measure total prompt use, agent behavior, or task performance and should not be extrapolated to enterprise repositories.

---

## 6. Performance, throughput, and ReDoS boundary

The benchmark records local scan timings as observations, not service-level latency guarantees. They depend on the host, runtime, and fixture composition.

### 6.1 Scanning Throughput

We evaluated scanning performance across 50 synthetic files totaling 10,000 lines:
- **Total Lines Scanned:** 10,000 lines
- **Total Files:** 50 files
- **Total Wall-Clock Scan Duration:** 1.599 seconds
- **Throughput:** **6,253.6 lines/second**
- **100-line Scan Call:** **7.48 milliseconds**

This is one run on a host reported as `Windows-10-10.0.26200-SP0` with Python 3.11.9; it is not a cross-platform performance study. The timing record and environment are in `supporting/benchmark/metrics/summary.json`.

### 6.2 Minified Line Skip Behavior & ReDoS Limits

The benchmark passed a 24 KB single-line input to the scanner and observed it being skipped by the 10,000-character limit. The scan call took **46.656 milliseconds** in the recorded run. No unprotected or adversarial regex comparison was run, so this result demonstrates only the configured skip behavior; it does not establish ReDoS resistance or a bound on worst-case runtime.

---

## 7. Limitations, failure modes, and security trade-offs

A transparent engineering analysis requires documenting the known trade-offs and operational boundaries of precision-first scanning:

1. **The Four-Part Version Number Collision:**
   A dotted version string that coincides with an address the validator classifies as global may be reported as an IP. The benchmark includes no positive IPv4 cases and does not assess this collision.
2. **Corporate vs. Public Webmail Domains:**
   The base `email` detector flags all syntactically valid email addresses, including internal corporate domains (e.g. `employee@company.internal`). In repositories where corporate addresses are standard, organizations must configure domain allowlists or leverage the medium-confidence companion detector `email-public-service`, which restricts alerts strictly to consumer webmail providers (Gmail, Yahoo, Proton, Outlook).
3. **Adversarial Steganography & Split Strings:**
   The scanner is optimized for plain source code, configuration files, and structured execution logs. It evaluates text line by line. It does not perform multi-stage deobfuscation for steganographic payloads (e.g. Base64 strings split across variable concatenations or XOR-encoded memory buffers).
4. **Natural Language PII:**
   This benchmark covers structured format markers and negative controls. It does not evaluate free-form personal disclosures or compare against natural-language detection systems.

---

## 8. Conclusion and reproducibility

False-positive findings increase serialized scan output. Whether and how they affect an autonomous agent's decisions is an important question that this benchmark does not test.

On the 101 synthetic cases, the deterministic scanner achieved aggregate precision **0.8889** and recall **0.5000**, compared with **0.2581** precision and **1.0000** recall for the simple regex baseline. On the separate all-negative five-file workload, its findings JSON used **1 token**, compared with **912 tokens** for the baseline. These are fixture-specific measurements; the labels are format-test markers and not live PII, and the benchmark does not measure agent reasoning, real-world detection effectiveness, or ReDoS resistance.

The package in [`supporting/benchmark/`](supporting/benchmark/) contains the fixtures, runner, pinned dependencies, a vendored scanner source snapshot, and SHA-256 manifests. The runner makes no live provider API calls. Installing dependencies and the tokenizer's first encoding lookup may require network access; timings vary between runs. See the reproducibility guide for the pinned source and a documented upstream package-build failure.
