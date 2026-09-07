# Phase 4 — Request Integrity and Replay Defense

## Status

**Complete — 2026-09-07.**

Verification environment: Python 3.13.2 on Windows.

- Tests: `42 passed`.
- Ruff lint: passed.
- Ruff format check: passed.
- Full Alembic chain through revision `0003_phase4` executed successfully on SQLite.
- Full migration chain compiled successfully with the PostgreSQL dialect.

## Delivered

- Registered agent identities containing Ed25519 public keys only.
- Agent revocation and durable monotonic sequence state.
- SDK Ed25519 key-pair generation and thread-safe action signer.
- Canonical signed action serialization shared by equivalent backend and SDK algorithms.
- Versioned intent-anchor SHA-256 hashes.
- Signed binding of action ID, session ID, agent ID, tool, parameters, intent-anchor hash, scope, timestamp, expiry, nonce, and sequence.
- Signature verification before semantic policy and risk evaluation.
- Timestamp timezone, future skew, expiry, and maximum-lifetime validation.
- Scope non-escalation check using exact `tool:<tool_name>` scopes.
- Durable `(agent_id, nonce)` replay uniqueness and monotonic sequence enforcement.
- Database row locking for sequence updates on databases that support it.
- Fail-closed handling for missing fields, bad signatures, stale anchors, revoked agents, expired requests, and replay.
- Audit handling for repeated action IDs without violating the unique original decision record.

## Integration model

Tools opt into cryptographic enforcement through:

```json
{
  "name": "read_message",
  "sensitivity": "low",
  "requires_signature": true
}
```

This opt-in preserves the unsigned Phase 1 demo path while allowing protected tools to fail closed. The final demonstration should mark all security-relevant tools as requiring signatures.

## Agent setup

The SDK generates a key pair locally. Only the base64-encoded 32-byte public key is registered with ASGP. The private key remains in the agent process and is never sent to or stored by the backend.

Conceptual flow:

```text
SDK generates Ed25519 key pair
→ POST public key to /api/v1/agents
→ construct signer with returned agent_id
→ configure ASGPClient with signer + current intent_anchor_hash
→ each verification request receives a fresh nonce and increasing sequence
```

## API additions

```text
POST /api/v1/agents
GET  /api/v1/agents/{agent_id}
POST /api/v1/agents/{agent_id}/revoke
```

## Cryptographic decision precedence

For a signature-protected tool:

1. Session and tool must exist.
2. Every signed-envelope field must be present.
3. Intent-anchor hash and exact tool scope must match.
4. Timestamps and lifetime must be valid.
5. Agent must exist and remain active.
6. Ed25519 signature must verify.
7. Nonce must be unused and sequence must increase.
8. Only then do deterministic policies and the risk engine run.

Any failure in steps 2–7 produces `BLOCK` and cannot be overridden by later signals.

## Attacks covered by automated tests

- Missing signature fields.
- Parameter modification after signing.
- Exact signed-request replay.
- Old/out-of-order sequence submission.
- Expired request.
- Scope escalation/mismatch.
- Signature against an obsolete intent anchor.
- Request from a revoked agent.
- Invalid public-key registration.
- Valid integrated Ed25519 request.

## Migration behavior

Online migration computes correct hashes for existing intent anchors. Offline SQL generation cannot inspect existing rows, so it emits a zero-hash sentinel for pre-Phase-4 anchors. This is deliberately fail-closed: such old sessions must create a new intent-anchor version before using signed tools. Newly created anchors always receive their actual canonical hash.

## Known limitations

- Agent registration and revocation endpoints do not yet have administrator authentication.
- The SDK private key is memory-managed; production HSM/keychain integration is out of MVP scope.
- Nonce cleanup/retention is not implemented yet, so the table grows with signed requests.
- A compromised legitimate agent can produce valid signatures; signatures prove origin and integrity, not semantic safety.
- Real PostgreSQL concurrency behavior remains a deployment verification item.
