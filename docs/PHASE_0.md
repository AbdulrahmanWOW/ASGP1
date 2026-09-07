# Phase 0 — Foundation and Contracts

## Status

**Complete — 2026-09-07.**

Verification environment: Python 3.13.2 on Windows.

- Tests: `13 passed`.
- Ruff lint: passed.
- Ruff format check: passed.
- Health route: covered through the FastAPI test client.

The temporary empty Git repository created during this phase was removed before Phase 1 because its sandbox-specific ownership prevented project commands from starting. No commits or project history were removed; Git should be initialized later from the normal development account.

## Delivered

- FastAPI application factory and versioned health endpoint.
- Environment-driven validated settings without secret values in source control.
- Recursive sensitive-field redaction utility.
- Immutable backend decision contracts for `ALLOW`, `BLOCK`, and `ESCALATE`.
- A separate Python SDK package with its initial verification-result contract.
- Automated tests for health, configuration, decisions, SDK contracts, and redaction.
- Architecture decision records for the modular monolith and authorization precedence.

## Intentionally deferred

- Database and migrations.
- Sessions and policies.
- Tool wrapping and execution.
- Security pipeline implementation.
- HTTP client behavior in the SDK.
- Frontend and container deployment.

These belong to later phases and are not represented by placeholders in the runtime code.

## Known non-blocking issue

The installed FastAPI/Starlette test stack emits two upstream deprecation warnings about its current test-client dependencies. They do not affect the application contract or test results. Dependency versions should be reviewed during routine maintenance rather than suppressing these warnings globally.

## Developer commands

From the repository root on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m ruff check backend sdk
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend
```

The health endpoint is `GET http://127.0.0.1:8000/api/v1/health`.
