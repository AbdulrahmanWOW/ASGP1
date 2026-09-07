# Phase 2 — Persistence, Sessions, and Policies

## Status

**Complete — 2026-09-07.**

Verification environment: Python 3.13.2 on Windows.

- Tests: `27 passed`.
- Ruff lint: passed.
- Ruff format check: passed.
- Alembic upgrade executed successfully on SQLite.
- The complete migration compiled successfully using Alembic's PostgreSQL dialect.

## Delivered

- SQLAlchemy 2 database layer with PostgreSQL (`psycopg`) support.
- SQLite integration-test configuration using the same ORM models.
- Alembic baseline migration for sessions, intent anchors, tools, policies, actions, decisions, and audit events.
- Durable repositories and atomic action/decision/audit persistence.
- Versioned intent anchors with optimistic version checks.
- Durable session revocation.
- Validated structured deny policies; arbitrary executable policy expressions are not accepted.
- Operators: `equals`, `not_equals`, `contains`, `in`, `not_in`, `matches`, `greater_than`, and `less_than`.
- Conservative validation for regex length and nested quantifiers.
- Path containment and external destination boundaries.
- Bounded recursive audit redaction for secret-like keys, long strings, collections, and nesting depth.
- A minimal PostgreSQL Compose service definition.

## API additions

```text
GET  /api/v1/sessions/{session_id}
PUT  /api/v1/sessions/{session_id}/intent
POST /api/v1/sessions/{session_id}/revoke
POST /api/v1/policies
GET  /api/v1/policies
```

## Database workflow

Set `ASGP_DATABASE_URL` and run from `backend/`:

```powershell
..\.venv\Scripts\python -m alembic -c alembic.ini upgrade head
```

The application does not silently create production tables. `initialize_schema=True` exists for isolated automated tests; deployed environments use Alembic.

## Honest environment limitation

The implementation and PostgreSQL driver are present, but PostgreSQL integration was not run on this machine during Phase 2 because `psql` and the Docker Compose plugin were unavailable. Migration SQL was compiled successfully for the PostgreSQL dialect, while persistence behavior is integration-tested against SQLite. A real PostgreSQL run remains a deployment verification item.

## Deferred by design

- Authentication and authorization for policy/tool administration.
- Human approval for general permission expansion (Phase 3).
- Nonces, signatures, timestamps, and replay defense (Phase 4).
- Hash chaining for audit rows (Phase 6).
