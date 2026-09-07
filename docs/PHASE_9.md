# Phase 9 — SDK-integrated demo agent

Phase 9 replaces API-only demonstrations with a small deterministic agent that invokes controlled tools through the real ASGP Python SDK.

## What the run proves

- `read_file` receives `ALLOW` and the underlying lab tool executes.
- forbidden `send_mail` receives `BLOCK`; an execution counter proves the underlying function was never reached.
- medium-sensitivity `upload` receives `ESCALATE` and creates a pending, action-bound approval visible in the dashboard.
- all destinations and files remain inside the harmless controlled attack lab.

## Run with the complete stack

```powershell
docker-compose --profile demo up --build
```

The one-shot `demo-agent` container waits for the API, registers the demonstration tools, creates a fresh governed session, then prints a JSON evidence record. Keep the stack running to inspect the session, risk, audit events, and pending approval at `http://127.0.0.1:4173`.

## Run against an existing local backend

```powershell
.\.venv\Scripts\python.exe -m demo.run_agent
```

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_phase9_demo_agent.py
.\.venv\Scripts\python.exe -m ruff check demo backend\tests\test_phase9_demo_agent.py
```
