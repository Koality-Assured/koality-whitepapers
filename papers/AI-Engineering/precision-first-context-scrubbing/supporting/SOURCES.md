# Primary-source access log and bibliography

Primary source pages and code used for fixture provenance or implementation descriptions were checked on 2026-10-27. These sources do not independently validate benchmark labels or metrics.

| ID | Title / Source | Canonical URL | Use and limitation |
| :--- | :--- | :--- | :--- |
| **S1** | RFC 2606 and RFC 6761, reserved example and test domains | `https://www.rfc-editor.org/rfc/rfc2606.html`; `https://www.rfc-editor.org/rfc/rfc6761.html` | Provenance for reserved domains in negative controls; reservation does not define scanner behavior. |
| **S2** | RFC 5737, IPv4 documentation ranges; RFC 3849, IPv6 documentation prefix | `https://www.rfc-editor.org/rfc/rfc5737.html`; `https://www.rfc-editor.org/rfc/rfc3849.html` | Provenance for documentation IP values in negative controls; does not establish how Python classifies every address. |
| **S3** | RFC 1918 and RFC 6598, private and shared address space | `https://www.rfc-editor.org/rfc/rfc1918.html`; `https://www.rfc-editor.org/rfc/rfc6598.html` | Provenance for private/shared network values used as negative controls. |
| **S4** | SSA, SSN Randomization and POMS SSN validity rules | `https://www.ssa.gov/employer/randomization.html`; `https://secure.ssa.gov/poms.nsf/lnx/0110201035`; `https://www.ssa.gov/employer/randomizationfaqs.html` | Supports use of area 000 and group 00 / serial 0000 values as invalid-format negative controls. Does not validate any real SSN. |
| **S5** | Stripe, Testing: Cards | `https://docs.stripe.com/testing#cards` | Stripe documents the included card values as fake test cards. They are labeled positive only for card-format recognition, not as live accounts or personal data. |
| **S6** | RFC 9542 §2.1.4, 48-Bit MAC Documentation Values | `https://www.rfc-editor.org/rfc/rfc9542.html#section-2.1.4` | The three positive MAC markers fall in the documented unicast range `00-00-5E-00-53-00` through `00-00-5E-00-53-FF`. They are format-positive markers, not device identifiers. |
| **S7** | `koality-pii-scanner`, pinned source commit `514f708e8890add75a963ff771245c1256394323` | `https://github.com/Koality-Assured/koality-pii-scanner/tree/514f708e8890add75a963ff771245c1256394323` | Implementation facts and scanner snapshot. The benchmark vendors `src/pii_scan/` from this commit with its `LICENSE`; copyright: © 2026 Koality Assured; MIT License. This package-build snapshot is a bounded reproduction mitigation and is not a claim that upstream installation succeeds. |
| **S8** | ISO/IEC 7812-1, Identification cards — Identification of issuers | `https://www.iso.org/standard/70484.html` | Background for card-number/IIN terminology; the benchmark does not verify active accounts or issuer allocation against live networks. |

## Dependency build observation

The following exact command was run in the isolated benchmark virtual environment against the pinned public source commit:

```text
python -m pip install --no-cache-dir git+https://github.com/Koality-Assured/koality-pii-scanner.git@514f708e8890add75a963ff771245c1256394323
```

It failed while preparing wheel metadata with Hatchling. The terminal error was:

```text
ValueError: A second file is being added to the wheel archive at the same path: `pii_scan/data/__init__.py`.
```

The benchmark therefore imports the byte-for-byte `src/pii_scan/` source snapshot at that commit from `benchmark/vendor/koality-pii-scanner/`, and includes the upstream MIT license. This is a bounded reproduction mitigation for the measured benchmark only. It does not modify the scanner repository, repair its package build, or claim that the upstream `pip install` works. The snapshot may become stale if upstream changes; its commit and normalized hashes are recorded in the run and SHA-256 manifests.
