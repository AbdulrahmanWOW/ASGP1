# Phase 7 — Dashboard and live demonstration

Phase 7 adds a responsive React operations dashboard backed by the real ASGP API. It deliberately uses five-second polling; WebSockets remain optional because they add operational complexity without improving the graduation-demo claim.

## Delivered

- Command-center overview with live session, approval, block, posture, and audit-integrity indicators.
- Session explorer with intent anchor, permission boundaries, risk history, decisions, and chain status.
- Event drawer with plain-language outcomes, technical reason codes, contributing findings, safe parameters, hashes, and stage timings.
- Human approval queue with one-time approve and reject controls.
- Empty, loading, unavailable-backend, and responsive mobile states.
- Backend session-list endpoint and restricted local-development CORS configuration.
- Docker definitions for the PostgreSQL, API, and dashboard stack.

## Run locally

### One command with Docker

```powershell
docker compose up --build
```

Open `http://127.0.0.1:4173`. The API is available at `http://127.0.0.1:8000/api/v1`.

### Developer mode

Start the API from the repository root:

```powershell
$env:ASGP_DATABASE_URL = "sqlite+pysqlite:///./asgp.db"
python -m uvicorn app.main:app --app-dir backend --reload
```

Then start the dashboard:

```powershell
cd frontend
pnpm install
pnpm dev
```

The frontend reads `VITE_API_URL` when supplied and otherwise uses `http://127.0.0.1:8000/api/v1`.

## Security boundaries

- The dashboard only displays `safe_parameters` already redacted by the backend; it never requests original tool secrets.
- Approval buttons resolve a server-side approval bound to the original action digest. They do not execute arbitrary tools from the browser.
- A dashboard or network failure does not weaken enforcement. Integrated SDK calls continue to fail closed at the gateway.
- The posture score is a presentation summary derived from current session risk. It is not a security guarantee or a learned threat score.

## Verification

- Backend tests cover session listing and the exact allowed local CORS origin.
- Frontend TypeScript production build and static lint both pass.
- The previous governance, replay-defense, semantic-signal, audit-chain, and redaction test suites remain unchanged and passing.
