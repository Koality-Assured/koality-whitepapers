"""Deterministic synthetic fixtures and sentinel canary generators for Zero-Plaintext Agent Context benchmark.

All keys, tokens, credentials, connection strings, and certificates are strictly synthetic.
Zero live secrets, production database dumps, or private paths are included.
"""

from __future__ import annotations

import base64
import hashlib
import urllib.parse
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SyntheticSecretFixture:
    secret_id: str
    secret_type: str
    raw_plaintext: str
    sentinel_token: str
    description: str

    def get_variants(self) -> list[str]:
        """Generate common encoding variants that an adversary or bug might cause to bleed."""
        variants: set[str] = set()
        # Raw
        variants.add(self.raw_plaintext)
        # Trimmed
        trimmed = self.raw_plaintext.strip()
        if len(trimmed) >= 4:
            variants.add(trimmed)
        # URL Encoded
        url_enc = urllib.parse.quote(self.raw_plaintext)
        if url_enc:
            variants.add(url_enc)
        # Base64
        b64 = base64.b64encode(self.raw_plaintext.encode("utf-8")).decode("ascii")
        if len(b64) >= 4:
            variants.add(b64)
            variants.add(b64.rstrip("="))
        # URL-safe Base64
        b64url = base64.urlsafe_b64encode(self.raw_plaintext.encode("utf-8")).decode("ascii")
        if len(b64url) >= 4:
            variants.add(b64url.rstrip("="))

        return sorted(variants, key=len, reverse=True)


def generate_synthetic_fixtures() -> list[SyntheticSecretFixture]:
    """Generates 5 distinct architectural secret archetypes with embedded canary sentinels."""
    fixtures = [
        SyntheticSecretFixture(
            secret_id="sec_example_01",
            secret_type="api_key",
            raw_plaintext="synthetic_api_key_SENTINEL_CANARY_a1b2c3d4e5f6789012345678abcdef01",
            sentinel_token="SENTINEL_CANARY_a1b2c3d4e5f6789012345678abcdef01",
            description="Inert SaaS-style API key with a fixed 32-character hex marker",
        ),
        SyntheticSecretFixture(
            secret_id="sec_db_conn_02",
            secret_type="connection_string",
            raw_plaintext="postgresql://synthetic_user:SENTINEL_CANARY_b2c3d4e5f6a1789012345678abcdef02@db.example.invalid:5432/tenant_example",
            sentinel_token="SENTINEL_CANARY_b2c3d4e5f6a1789012345678abcdef02",
            description="Synthetic PostgreSQL connection URI with embedded password",
        ),
        SyntheticSecretFixture(
            secret_id="sec_jwt_token_03",
            secret_type="jwt_token",
            raw_plaintext="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZ2VudF8wMSIsImNhbmFyeSI6IlNFTlRJTkVMX0NBTkFSWV9jM2Q0ZTVmNmExYjI3ODkwMTIzNDU2NzhhYmNkZWYwMyJ9.SIGNATURE_PLACEHOLDER_4567890",
            sentinel_token="SENTINEL_CANARY_c3d4e5f6a1b2789012345678abcdef03",
            description="Inert JWT-shaped placeholder, not a signed token",
        ),
        SyntheticSecretFixture(
            secret_id="sec_ssh_key_04",
            secret_type="private_key",
            raw_plaintext=(
                "-----BEGIN OPENSSH PRIVATE KEY-----\n"
                "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW\n"
                "QyNTUxOQAAACCSENTINEL_CANARY_d4e5f6a1b2c3789012345678abcdef04AAAAAAAA\n"
                "-----END OPENSSH PRIVATE KEY-----"
            ),
            sentinel_token="SENTINEL_CANARY_d4e5f6a1b2c3789012345678abcdef04",
            description="Inert multiline SSH-key-shaped placeholder, not a usable key",
        ),
        SyntheticSecretFixture(
            secret_id="sec_webhook_secret_05",
            secret_type="hmac_signing_secret",
            raw_plaintext="whsec_SENTINEL_CANARY_e5f6a1b2c3d4789012345678abcdef05",
            sentinel_token="SENTINEL_CANARY_e5f6a1b2c3d4789012345678abcdef05",
            description="Synthetic webhook endpoint signature verification secret",
        ),
    ]
    return fixtures


def simulate_vault_api_reveal(secret: SyntheticSecretFixture) -> dict[str, Any]:
    """Simulates POST /api/v1/secrets/:id/reveal returning AES-256-GCM envelope."""
    # Deterministic mock ciphertext (hex)
    iv = "0102030405060708090a0b0c"
    auth_tag = "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d"
    aad = f"tenant_example:vlt_example_01:{secret.secret_id}:1:1"
    # A digest is an opaque stand-in, not AES-GCM encryption or a valid envelope.
    mock_ciphertext = hashlib.sha256(secret.raw_plaintext.encode()).hexdigest() + "00112233"

    return {
        "id": secret.secret_id,
        "vaultId": "vlt_example_01",
        "version": 1,
        "keyVersion": 1,
        "encryptedPayload": {
            "algorithm": "AES-256-GCM",
            "ciphertext": mock_ciphertext,
            "iv": iv,
            "authTag": auth_tag,
            "aad": aad,
            "keyVersion": 1,
        },
        "encryptedVaultKey": {
            "ciphertext": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "iv": "0f0e0d0c0b0a090807060504",
            "authTag": "9876543210abcdef0123456789abcdef",
            "aad": "agent_wrap_aad_test",
            "keyVersion": 1,
        },
        "auditEventId": "evt_audit_reveal_test_01",
    }


def simulate_mcp_execute_with_secret(
    secret: SyntheticSecretFixture,
    command: str,
    simulated_stdout: str,
    simulated_stderr: str,
) -> dict[str, Any]:
    """Models a tool result with Python replacement of full-secret variants."""
    # Build replacement rules
    variants = secret.get_variants()
    replacement = f"[REDACTED:{secret.secret_id}]"

    scrubbed_stdout = simulated_stdout
    for v in variants:
        if v in scrubbed_stdout:
            scrubbed_stdout = scrubbed_stdout.replace(v, replacement)

    scrubbed_stderr = simulated_stderr
    for v in variants:
        if v in scrubbed_stderr:
            scrubbed_stderr = scrubbed_stderr.replace(v, replacement)

    return {
        "exitCode": 0,
        "stdout": scrubbed_stdout,
        "stderr": scrubbed_stderr,
        "injectedEnvKeys": ["DB_PASSWORD", "API_KEY"],
    }
