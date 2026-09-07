# Phase 1 — First End-to-End Security Slice

## Status

**Complete — 2026-09-07.**

Verification environment: Python 3.13.2 on Windows.

- Tests: `20 passed`.
- Ruff lint: passed.
- Ruff format check: passed.
- Covered execution outcomes: allowed executes once; blocked and unavailable execute zero times.

## Delivered

- In-memory session creation with intent, allowed tools, and forbidden tools.
- In-memory tool registry.
- Deterministic tool-permission policy.
- `POST /api/v1/actions/verify` before-execution decision endpoint.
- Audit events for allowed and blocked attempts with sensitive-field redaction.
- Python HTTP client that fails closed on transport, HTTP, or response-validation errors.
- Python `protect_tool` wrapper that only invokes the original callable after `ALLOW`.
- Harmless counted demo tools proving whether execution occurred.

## API flow

```text
POST /api/v1/tools/register
POST /api/v1/sessions
POST /api/v1/actions/verify
GET  /api/v1/audit/{session_id}
```

## Security behavior

- Unknown session → `BLOCK`.
- Inactive session → `BLOCK`.
- Unregistered tool → `BLOCK`.
- Explicitly forbidden tool → `BLOCK`.
- Tool outside the allowlist → `BLOCK`.
- Registered and allowed tool → `ALLOW`.
- Gateway/client failure → exception before tool execution.

## Deferred by design

- Persistence and database constraints (Phase 2).
- Risk score and approval workflow (Phase 3).
- Request signing, expiry, and replay defense (Phase 4).
- Semantic and behavioral signals (Phase 5).
- Hash-chained audit integrity (Phase 6).

## Known limitations

- State is intentionally lost when the backend restarts.
- Tool registration has no authentication in this internal Phase 1 prototype.
- Audit events are redacted but not hash chained yet.
- The SDK is synchronous and raises on `ESCALATE`; waiting for approval belongs to Phase 3.
- The upstream FastAPI/Starlette test stack emits two non-blocking deprecation warnings.

Phase 2 has since replaced the in-memory state described in this historical delivery report with durable SQLAlchemy repositories.
