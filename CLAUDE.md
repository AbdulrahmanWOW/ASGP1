# ASGP — instructions for Claude Code

ASGP (Agent Security Governance Platform) is a graduation project: middleware that intercepts AI-agent tool calls **before execution**, checks each one against a human-confirmed, signed user intent, and returns ALLOW / BLOCK / ESCALATE (human approval). Every decision is audited. Everything runs locally.

## Read before working

- `docs/context/DESIGN.md` — final design, literature, known errors in older docs. **The design in §5–11 is settled.**
- `docs/plan/IMPLEMENTATION_PLAN.md` — phases, acceptance criteria, current status. Pick the next unchecked item.
- `docs/context/IMPLEMENTATION_REVIEW.md`, `docs/context/DESIGN_DOC_REVIEW.md` — known gaps.
- `docs/context/papers/` — paper summaries (read the banner on each; some contain known errors).

## Layout

- `backend/app` — FastAPI gateway. `services/governance.py` is the pipeline orchestrator.
- `sdk/asgp_sdk` — Python SDK (`protect_tool`, `ToolGuard`, adapters in `asgp_sdk/adapters/`).
- `gateway/asgp_gateway` — MCP gateway proxy.
- `demo/` — demo agent, attack lab, `evaluate.py`. `frontend/` — React dashboard.

## Commands

```bash
python -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
python -m pytest -q                 # all tests (backend, sdk, gateway)
ruff check .                        # lint
python -m demo.evaluate             # regenerate evaluation/latest/*
```

## Rules (do not break)

- **Fail closed** everywhere: errors/timeouts/invalid output → BLOCK or ESCALATE, never ALLOW.
- Hard rules beat scores; automation can only tighten; the LLM judge never approves high/critical actions alone and **never sees untrusted content**.
- Adapters never edit tool arguments.
- Local models only — never add external AI API calls.
- **Never fabricate results.** Numbers only from real runs; report the false-positive rate next to accuracy.
- Don't call ASGP "the first" anything (see DESIGN.md §13 for safe novelty wording).
- New DB columns need an Alembic migration in `backend/migrations/versions/`.
- One phase/item per commit, with tests. Update the plan's status when an item lands.
- This repo is public: no personal data, keys or emails in commits.
