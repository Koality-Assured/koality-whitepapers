# Encrypted reveal envelopes and local secret use in agent tool harnesses

## Abstract

Autonomous agents often need credentials to access databases, repositories, and cloud services. When a tool returns a credential as text, that value can enter the conversation history and may be included in later model requests or logs, depending on the harness and provider [I1].

This paper describes the envelope returned by the `llm-vault` reveal route and local secret handling implemented by `llm-vault-mcp` [P1, P5, P6]. The MCP process decrypts secrets in process memory and provides tools designed to use them without placing the secret in the tool result. A stream scrubber attempts to remove selected credential forms from subprocess output [P6]. These implementation properties do not establish that plaintext is absent from all host memory, outputs, or provider systems [U1–U3].

The accompanying offline Python simulation evaluates five synthetic secret examples in constructed response, tool-result, log, and prompt-history values. It does not execute either product, a subprocess, or an LLM, and it refuses network access during execution [M1, M5]. The naive prompt histories contain eight literal sentinel appearances and ten raw credential appearances, counted separately because some sentinels are substrings of their credentials. The modeled three-turn histories average 326.6 input tokens for the naive case and 193.8 for the sandbox-shaped case. The unweighted mean of per-fixture reductions is 35.26%; the reduction between those displayed means is 40.66%. A separate Python `str.replace` timing uses an exactly 50 KiB synthetic UTF-8 string and does not measure the MCP scrubber [M1–M3].

The paper also records implementation history: an early internal design note names Argon2id, while the inspected Slice 2 and Slice 3 commits use HMAC-SHA256 and Node.js `scryptSync`, respectively [P3]. This history is not a standards-compliance assessment. NIST SP 800-63B-4 describes salted password hashing with a cost factor without naming Argon2id or scrypt; OWASP's parameter guidance addresses password storage and does not directly establish the security of this client-key verifier [S3, S4].

---

## 1. Scope and thesis

**Thesis.** Returning credentials in tool results can expose them to conversation histories and later model requests. An encrypted API envelope and local secret-use tools provide a design for keeping credentials out of ordinary tool results, subject to the host, tool, and output boundaries described here.

**Scope.** This paper documents the reveal response contract, local secret-use flow, historical changes to password verification, and outcomes of a small Python simulation. It does not measure provider caches, runtime API or MCP behavior, or production scrubber performance [U1–U3].

**Audience.** Systems architects, security engineers, and AI infrastructure teams building autonomous agent tool harnesses, MCP servers, and credential isolation boundaries.

---

## 2. The threat model of agent credential handling

When an autonomous coding agent performs deployment, debugging, or database migration tasks, it must authenticate against external systems. Naive harness integrations treat credentials as standard tool return values:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Pattern A: Plaintext tool result                                      │
│                                                                        │
│ Agent ──► Tool Call: get_api_key(service="example.invalid")           │
│                                                                        │
│ Tool Server ──► Returns JSON: {"key": "SENTINEL_CANARY_API_KEY"}      │
│                                                                        │
│ Later context may include the returned sentinel, depending on harness  │
│                                                                        │
│ Possible exposure; retention depends on the harness and provider       │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│ Pattern B: Encrypted envelope with local tool use                      │
│                                                                        │
│ Agent ──► Tool Call: vault_run_command(secret_id="sec_example_01", ...)│
│                                                                        │
│ Vault API ──► Returns Encrypted Envelope (Ciphertext + Wrapped Key)    │
│ MCP Server ──► Decrypts locally in memory via WebCrypto               │
│               ──► Injects secret into child process environment        │
│               ──► Scrubs stdout/stderr via regex stream filter         │
│                                                                        │
│ Tool Return ──► Constructed result: {"exitCode": 0, "stdout": "OK"}   │
│                                                                        │
│ This example result omits the secret; other boundaries remain          │
└────────────────────────────────────────────────────────────────────────┘
```

All values and identifiers in this diagram are synthetic examples. The second result describes one constructed tool response, not a system-wide guarantee.

Returning a credential in a model-facing tool result creates possible exposure paths:

1. **Conversation history:** A harness may include a tool result in later model requests. Transcript behavior depends on the harness and provider.
2. **Delegated work:** A child agent that inherits a transcript containing a credential can receive that credential too. This paper does not measure delegation systems or quantify their exposure.
3. **Untrusted instructions:** If an agent receives a credential in its context, malicious instructions in inspected content may try to induce disclosure. The outcome depends on the model and surrounding controls [I1].

The design goal is to let tools use credentials while keeping secret values out of model-facing tool results and prompt histories.

---

## 3. Key derivation and authentication

The inspected client code derives separate master-encryption and client-authentication material from passphrase-derived key material. Agent wrapping keys are derived from a separate agent decryption key. The server stores a verifier derived from the client-authentication key.

```text
Passphrase + Salt
       │
       ▼ PBKDF2-HMAC-SHA256 (minimum 600,000 iterations)
Derived key material
       ├── HKDF info: llm-vault/v1/master-encryption-key
       │      └── Master encryption key
       └── HKDF info: llm-vault/v1/client-auth-key
              └── ClientAuthKey ──TLS──► server verifier

AgentDecryptionKey + agent/vault/version context
       └── HKDF info: llm-vault/v1/agent-vault-key:...
              └── Agent wrapping key
```

### 3.1 Client-Side Derivation (`@llm-vault/crypto`)

The client derives key material with PBKDF2-HMAC-SHA256 using a minimum iteration count of 600,000, then uses HKDF-SHA256 with distinct info labels for the master-encryption key and `ClientAuthKey`. The agent wrapping key is derived separately from `AgentDecryptionKey`; it is not derived from the passphrase-derived key material [P2].

### 3.2 Server verification and implementation history

An early internal design note specified server-side Argon2id. The inspected public Git commits show a different implementation history:

1. **Slice 2 (commit `8ad53ce`, PR #3):** In `apps/api/src/auth.ts`, `hashServerPassword` was implemented using `HMAC-SHA256`:
   ```typescript
   export function hashServerPassword(clientAuthKeyHex: string, serverSalt: string): string {
     return crypto.createHmac("sha256", serverSalt).update(clientAuthKeyHex).digest("hex");
   }
   ```
2. **Slice 3 (commit `e01259d`, PR #4):** During the enterprise database and SSO merge, `hashServerPassword` transitioned to Node.js `scryptSync`:
   ```typescript
   export function hashServerPassword(clientAuthKeyHex: string, serverSalt: string): string {
     return crypto.scryptSync(clientAuthKeyHex, serverSalt, 32).toString("hex");
   }
   ```

The inspected Slice 3 call uses Node.js `scryptSync` defaults (`N=16384`, `r=8`, `p=1`). NIST SP 800-63B-4 calls for salted password hashing with a cost factor but does not name Argon2id or scrypt. OWASP lists password-storage parameter sets that include `N=2^14`, `r=8`, `p=5`; the implementation's `p=1` differs. Those recommendations address stored human passwords. Their applicability to a derived client-authentication key requires a separate security analysis, which this paper does not provide. The included Python timing is an implementation analog, not a measurement of Node.js or the deployed service [P3, M4, S3, S4, S9].

---

## 4. Standalone reveal route response

Inspection of the API server source shows the standalone reveal route returning an encrypted payload and caller key envelope:

```typescript
app.post("/api/v1/secrets/:id/reveal", async (request, reply) => {
  const caller = requireAuth(request, reply);
  requireScope(caller, "secrets:reveal", reply);
  // ... database lookups and role checks ...

  return reply.send({
    id: secret.id,
    vaultId: secret.vaultId,
    version: secret.currentVersion,
    keyVersion: secret.keyVersion,
    encryptedPayload: {
      algorithm: "AES-256-GCM",
      ciphertext: currentVersion.encryptedPayload,
      iv: currentVersion.payloadIv,
      authTag: currentVersion.payloadAuthTag,
      aad: currentVersion.payloadAad,
      keyVersion: currentVersion.keyVersion,
    },
    encryptedVaultKey: callerVaultKeyEnvelope,
    auditEventId,
  });
});
```

### Key Security Invariants of the Route
- **Response contract:** The route response contains AES-256-GCM ciphertext, IV, authentication tag, AAD, and the caller's wrapped vault key; the handler does not return the decrypted secret value [P1].
- **Canonical AAD Binding:** The canonical AAD string binds tenant ID, vault ID, secret ID, secret version, and key version as five colon-delimited fields. Authentication fails if the client supplies mismatched AAD [P4].
- **Raw reveal policy:** `allowRawContextReveal` does not change this Fastify route's envelope response. In the MCP implementation, it gates a separate `getSecret` raw reveal and still requires out-of-band human confirmation [P5].

---

## 5. Client-side MCP tool sandboxing and execution scrubbing

The `llm-vault-mcp` source includes local tools for using secrets without returning their values as ordinary tool results [S1, P5, P6]:

### 5.1 Local Decryption via WebCrypto
When a secret-backed operation is run:
1. It requests the encrypted envelope through the configured vault API client.
2. It unwraps `encryptedVaultKey` in memory using the local agent wrapping key.
3. It decrypts `encryptedPayload` within the MCP process using W3C `SubtleCrypto.decrypt()` [S2, P6].
4. The operation may retain decrypted secret material in MCP process memory while it prepares or runs the action. This paper does not verify memory zeroization at runtime.

### 5.2 Subprocess Execution and Stream Scrubbing
The MCP server can pass credentials to an action and scrub selected secret variants from captured `stdout` and `stderr`. The scrubber is a pattern-based output filter; the Python benchmark below does not execute this TypeScript implementation.

```typescript
export function scrubSecretsFromText(
  text: string,
  activeSecrets: ReadonlyArray<ActiveSecretDescriptor>,
): string {
  // Generates candidate variants: UTF-8, trimmed, Base64 (padded/unpadded), URL-encoded
  // Replaces occurrences with [REDACTED:${secret.id}]
  // Sorts replacement rules longest-needle first to prevent partial shadowing
}
```

The tool returns its result after the configured output handling. Scrubbing is limited to recognized forms and does not guarantee that arbitrary transformations or side channels cannot expose a credential.

---

## 6. Offline Python simulation

The benchmark is a deterministic Python model of selected values at four constructed boundaries. It does not call `llm-vault`, `llm-vault-mcp`, an HTTP server, a subprocess, an LLM, or an external API. Passing these checks demonstrates only that the fixtures produce the expected modeled values.

### 6.1 Fixtures and modeled checks
- **Fixtures:** Five inert examples: an API-key-shaped string, PostgreSQL URI, JWT-shaped placeholder, SSH-key-shaped placeholder, and webhook secret. The fixed sentinel markers are patterned 32-character hex strings; they are synthetic labels, not random 256-bit tokens.
- **Constructed checks:**
  1. *API-shaped response:* A Python dictionary contains deterministic mock ciphertext and is checked for raw fixture text.
  2. *MCP-shaped result:* Python replacement is applied to constructed stdout and stderr before the mock result is serialized.
  3. *Variant replacement:* Python `str.replace` is applied to a generated text buffer containing selected secret variants.
  4. *Prompt history:* Two authored JSON histories are compared over three simulated turns. The histories are not generated by an agent runtime.

### 6.2 Simulation results

All five fixtures pass each constructed check. These rates describe the Python model only:

| **Constructed check** | **Naive fixture** | **Sandbox-shaped fixture** | **Modeled result** |
| :--- | :--- | :--- | :--- |
| API-shaped JSON contains raw fixture value | Not applicable | 0 / 5 | 5 / 5 pass |
| MCP-shaped result contains raw fixture value | Not applicable | 0 / 5 | 5 / 5 pass |
| Python variant replacement leaves a tested variant | 10 constructed variants | 0 / 5 | 5 / 5 pass |
| Prompt-history literal sentinel appearances | 8 | 0 | 8 fewer appearances |
| Prompt-history raw credential appearances | 10 | 0 | 10 fewer appearances |
| Mean cumulative tokens across modeled turns | 326.6 | 193.8 | 35.26% unweighted mean per-fixture reduction; 40.66% reduction between means |
| Python `str.replace` over 50 KiB UTF-8 | Not applicable | See `metrics/summary.json` | Host-dependent Python timing |

```text
Constructed Python checks (not runtime containment tests):
API-shaped JSON:          5/5 pass
MCP-shaped tool result:   5/5 pass
Python variant replace:   5/5 pass
Prompt-history model:     5/5 pass
```

### 6.3 Python analog timings

The runner reports Python standard-library timings for PBKDF2, scrypt, HMAC, and string replacement [M4]. They do not measure the TypeScript WebCrypto client, Node.js `scryptSync`, the MCP scrubber, or end-to-end tool latency. The reproducibility guide and metrics file contain the current host-specific timing values.

---

## 7. Security invariants, failure modes, and limitations

The envelope and local-use design addresses one model-facing path. Systems engineers must account for these additional boundaries:

1. **Process memory:** Decrypted values are available to the local MCP process while an operation uses them. This work does not test memory dumps, process isolation, zeroization, or kernel compromise.
2. **Output scrubbing:** Pattern-based replacement covers only the tested variants. It does not establish coverage for arbitrary encodings, transformations, partial disclosure, or other side channels.
3. **Raw reveal:** The MCP `getSecret` operation has a separate raw-plaintext path gated by `allowRawContextReveal` and out-of-band human confirmation. The API reveal route still returns an envelope; the flag does not change that route's response.
4. **External systems:** The simulation does not inspect provider caches, logs, telemetry, or retention behavior.

---

## 8. Conclusion and supporting material

Returning credentials as model-facing tool output can expose them to later conversation turns. An envelope response and local secret-use tools can reduce that exposure by design, while host memory and output handling remain separate boundaries.

The Python simulation found no raw fixture values in its constructed sandbox history. It does not prove complete credential containment in a deployed system. The source code and limits are documented in the [claim-to-evidence ledger](supporting/CLAIM-TO-EVIDENCE.md) and [source log](supporting/SOURCES.md). Run the [reproducibility steps](supporting/REPRODUCIBILITY.md) and inspect the [benchmark code and metrics](supporting/benchmark/).
