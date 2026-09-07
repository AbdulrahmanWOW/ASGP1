# Phase 6 — Tamper-Evident Audit and Observability

## Status

**Complete — 2026-09-07.**

Verification environment: Python 3.13.2 on Windows.

- Tests: `54 passed`.
- Ruff lint: passed.
- Ruff format check: passed.
- Full Alembic chain through revision `0005_phase6` executed successfully on SQLite.
- Full migration chain compiled successfully with the PostgreSQL dialect.

## Delivered

- Per-session SHA-256 audit hash chains over canonical redacted event data.
- Monotonic per-session audit sequence with a database uniqueness constraint.
- Separate locked Audit Head containing the expected last sequence, hash, and event count.
- Verification of each event hash, previous-hash link, sequence continuity, and Audit Head.
- Detection of modified events, deleted interior events, and deleted final events.
- Risk state, finding codes, reason codes, and stage timings bound into each event hash.
- Timings for session, registry, cryptographic, policy, intent, injection, behavior, and risk stages.
- Total pipeline latency persisted with decisions and returned to SDK clients.
- Aggregated decision count, average total latency, and per-stage averages.
- Existing bounded parameter redaction remains active before hashing and persistence.

## Audit entry structure

Each event binds at minimum:

```text
event_id
action_id
session_id
sequence
tool_name
safe_parameters
outcome
reason_codes
risk_before / risk_after
finding_codes
stage_timings_ms
previous_hash
created_at
```

Canonical JSON is hashed with SHA-256 to produce `entry_hash`. The next event stores that value as `previous_hash`.

## Audit Head

Hash chaining alone cannot detect deletion of the final row because no following row references it. ASGP therefore stores an independent per-session head:

```text
session_id
last_sequence
last_hash
event_count
```

Deleting the final event without updating the head produces count and hash mismatches. Audit events and the head are updated within the same database transaction. PostgreSQL-capable row locking protects concurrent head updates.

## API additions

```text
POST /api/v1/audit/{session_id}/verify
GET  /api/v1/metrics/pipeline
```

Example verification response:

```json
{
  "session_id": "...",
  "valid": false,
  "event_count": 2,
  "verified_hash": "...",
  "errors": [
    "Audit head event count mismatch",
    "Audit head hash mismatch"
  ]
}
```

## Automated tamper scenarios

- Untouched three-event chain verifies successfully.
- Editing the parameters of an interior event causes an entry-hash mismatch.
- Deleting an interior event causes a sequence gap and link mismatch.
- Deleting the final event is detected by the Audit Head.
- Redacted secret fields, not their original values, are stored and hashed.
- Timing stages appear in the response, audit event, and aggregated metrics.

## Migration behavior

Online migration reconstructs valid chains for existing audit rows and creates the corresponding heads. PostgreSQL offline SQL generation cannot calculate application SHA-256 hashes from fetched rows. It assigns ordered per-session sequences and explicit sentinel hashes so the schema migration remains applicable, but verification intentionally fails closed until those legacy rows are re-baselined through an approved online migration procedure. New events always use real hashes.

## Honest security boundary

The audit log is **tamper-evident**, not tamper-proof. It detects inconsistent changes relative to its Audit Head. An attacker who controls all database rows and can coherently recompute both the full chain and its head can replace history. Stronger deployment options include periodically signing/exporting heads to independent storage, but that is outside the graduation MVP.

## Known limitations

- PostgreSQL concurrency behavior still needs a real service integration run.
- Metrics are process/database aggregates and currently have no time-window filters.
- P95 and experiment-specific latency statistics belong to Phase 8 evaluation.
- Audit retention, archival, and independently signed checkpoints are not implemented.
- Two upstream FastAPI/Starlette test-client deprecation warnings remain non-blocking.
