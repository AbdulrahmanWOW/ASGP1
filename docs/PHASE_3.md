# Phase 3 — Decision, Risk, and Approval

## Status

**Complete — 2026-09-07.**

Verification environment: Python 3.13.2 on Windows.

- Tests: `35 passed`.
- Ruff lint: passed.
- Ruff format check: passed.
- Full Alembic chain through revision `0002_phase3` executed successfully on SQLite.
- Full migration chain compiled successfully with the PostgreSQL dialect.

## Delivered

- Deterministic bounded session risk score from `0` to `100`.
- Explainable risk transitions with previous score, delta, new score, reason, and action ID.
- Tool sensitivity levels: `low`, `medium`, `high`, and `critical`.
- Decision thresholds for `ALLOW`, `ESCALATE`, and `BLOCK`.
- Explicit precedence: invalid session state, unregistered tools, permission boundaries, and deterministic deny policies block before risk-based escalation.
- Durable approval requests for escalated actions.
- SHA-256 action digest binding over session, action, tool, and canonical parameters.
- Expiring approval lifecycle: pending, approved/rejected, expired, and consumed.
- Database row locking for approval resolution and consumption on databases that support it.
- One-time approval consumption bound to the exact action ID.
- SDK polling support and fail-closed behavior for rejection, expiry, reuse, mismatch, timeout, or transport failure.
- SDK parameter snapshot check preventing changed mutable parameters from executing after approval.
- Session revocation remains the MVP `TERMINATE` behavior.

## Risk rules in this phase

The Phase 3 rules are deliberately simple and explainable:

| Tool sensitivity | Risk delta |
|---|---:|
| Low | -5, bounded at zero |
| Medium | +40 |
| High | +70 |
| Critical | +100 |
| Hard-control failure | +20 and immediate block |

Decision thresholds after applying the delta:

- `0–39` → `ALLOW`
- `40–69` → `ESCALATE`
- `70–100` → `BLOCK`

These are prototype values intended for later evaluation and calibration, not universal security constants.

## API additions

```text
GET  /api/v1/approvals
GET  /api/v1/approvals/{approval_id}
POST /api/v1/approvals/{approval_id}/resolve
POST /api/v1/approvals/{approval_id}/consume
GET  /api/v1/risk/{session_id}
```

## Security invariants demonstrated

- A medium-risk action does not execute without approval.
- An approval cannot authorize another action ID.
- Approved permission is consumed once.
- Rejected or expired approval cannot be consumed.
- Hard policy denial never becomes an approval request.
- Mutable parameters changed during the wait do not execute.
- Repeated risk accumulates and can change a later decision from escalation to block.

## Known limitations

- Approval endpoints do not have user authentication yet; this remains mandatory before any non-demo deployment.
- The synchronous SDK polling model occupies the caller while waiting.
- Risk deltas and thresholds are initial research parameters and require evaluation.
- Risk currently decays only through allowed low-sensitivity calls; administrative reset is intentionally absent.
- Real PostgreSQL concurrency behavior remains to be verified on a PostgreSQL service.
