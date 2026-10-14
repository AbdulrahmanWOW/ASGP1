<p align="center">
  <img src="Logo.png" alt="ASGP — Agent Security Governance Platform" width="620" />
</p>

<h1 align="center">ASGP — Agent Security Governance Platform</h1>

<p align="center">
  Pre-execution security governance for tool-using AI agents.
</p>

<p align="center">
  <strong>Intent-aware policies · Request integrity · Risk analysis · Human approval · Tamper-evident audit</strong>
</p>

## Overview

ASGP is a graduation-project security prototype placed between an integrated AI agent and its tools. Every security-relevant tool call is intercepted before execution and evaluated as:

- `ALLOW` — execute the wrapped tool.
- `BLOCK` — prevent execution.
- `ESCALATE` — pause and request an action-bound human approval.

ASGP governs registered tools routed through its SDK or gateway. It does not claim to intercept arbitrary code or tools that bypass that integration boundary.

## What this branch adds

Branch `new-test-branch-with-newer-sdks-and-proxy` moves the MVP to the final hybrid design in [`docs/context/DESIGN.md`](docs/context/DESIGN.md). Status and acceptance criteria: [`docs/plan/IMPLEMENTATION_PLAN.md`](docs/plan/IMPLEMENTATION_PLAN.md).

- **API authentication with roles** (`admin`, `user`, `agent`): an agent can no longer approve its own escalation, change its scope or administer the gateway.
- **Human-confirmed, signed intent**: the agent drafts a least-privilege scope (`POST /intents/drafts`), a human confirms it, and ASGP issues an Ed25519-signed intent token that every call must carry.
- **Fail-closed boundaries**: path/destination parameters are checked under many names (or as declared per tool), empty allow-lists deny, URLs are matched by host.
- **Risk rework**: per-action scoring, no risk washing, high-impact tools go to a human instead of being blocked, suspicious sessions force review, repeated blocks end the run.
- **Hybrid pipeline**: embedding alignment over the whole call (arguments included) and an optional **local Ollama judge** for the gray zone that fails closed and never sees ingested content.
- **Framework adapters**: LangChain/LangGraph middleware (interrupt/resume), raw API loop (OpenAI/Anthropic/Ollama formats), Claude Agent SDK callback + hook.
- **MCP gateway** (`gateway/`): govern MCP tools for agents you don't own (Claude Desktop, Cursor) with a config change.
- **Traceability**: decisions record the intent version, deciding layer and actor; approvals record who resolved them.

## Why ASGP?

An agent may begin with a legitimate user objective, then encounter malicious instructions in email, files, web content, or retrieved documents. ASGP keeps authorization outside the probabilistic model and combines deterministic controls with explainable semantic and behavioral signals.

```text
User Intent → AI Agent → ASGP SDK → Security Pipeline
                                  ↓
                    ALLOW / BLOCK / ESCALATE
                                  ↓
                   Tool + Audit + Dashboard
```

## Security pipeline

0. Caller authenticated by API key and role.
1. Session validation and **signed intent token** (for human-confirmed sessions).
2. Tool registration and request-schema validation.
3. Ed25519 agent-request signature, nonce, expiry, and replay checks (tools that require it).
4. Deterministic tool, path, destination, and structured-policy enforcement (fail closed).
5. Intent-alignment signal (lexical, hashing or local sentence-transformers embeddings).
6. Prompt-injection and category-based behavioral findings.
7. Per-action risk score; high-impact and suspicious-session floors.
8. Optional local LLM judge for the gray zone (can tighten; may relax only plain gray-zone calls).
9. `ALLOW`, `BLOCK`, or `ESCALATE` (human approval bound to one exact action).
10. Secret-redacted, hash-chained audit with intent version, deciding layer and actor.

## Features

- Versioned Intent Anchors and explicit permission boundaries.
- Python SDK with fail-closed protected-tool wrappers.
- PostgreSQL persistence and Alembic migrations.
- Safe structured policy language without `eval` or executable rules.
- Ed25519 identities, canonical action digests, and replay defense.
- Expiring human approvals bound to one exact action.
- Explainable prompt-injection and multi-step behavioral signals.
- Responsive React dashboard for sessions, risk, approvals, events, and audit status.
- Controlled attack lab with reproducible labeled evaluation and ablation.
- SDK-integrated demo agent proving `ALLOW`, `BLOCK`, and `ESCALATE` before execution.
- Content-ingress quarantine before untrusted text reaches agent context.
- Research dashboard with confusion matrix, F1 metrics, and ablation evidence.
- Docker Compose local deployment.

## Quick start with Docker

### Requirements

- Docker Desktop
- Docker Compose
- Ports `4173`, `8000`, and `5432` available

```powershell
git clone https://github.com/HazemOraby/ASGP.git
cd ASGP
docker-compose up --build
```

The compose file ships **development** API keys (`dev-admin-key-change-me`, `dev-user-key-change-me`, `dev-agent-key-change-me`); set `ASGP_API_KEYS` to your own for anything shared. Paste the user or admin key into the dashboard's "Dashboard API key" box. Optional local judge: `docker compose --profile judge up`, pull a model into the `ollama` service and set `ASGP_JUDGE=ollama`.

Open:

- Dashboard: [http://127.0.0.1:4173](http://127.0.0.1:4173)
- API documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

To run the one-shot SDK-integrated demonstration as part of the stack:

```powershell
docker-compose --profile demo up --build
```

For native Python and Node.js setup, see the [deployment guide](docs/DEPLOYMENT.md).

## Development verification

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check backend sdk gateway demo tests_support
```

From the `frontend` directory:

```powershell
pnpm build
pnpm lint
```

On this branch all **118 automated tests** (backend, SDK adapters against real LangChain/LangGraph/Claude Agent SDK packages, MCP gateway including an end-to-end stdio run) and the frontend production checks pass.

## Reproducible evaluation

```powershell
.\.venv\Scripts\python.exe -m demo.evaluate
```

The controlled evaluation now uses 19 reviewable seeds exercised as 95 deterministic traceable cases (lexical provider, no LLM judge). Seven seeds were added on this branch **after** the hardening to exercise the gaps it closes, so they are not an independent test set. Same seeds, both pipelines:

| Metric | `main` | this branch |
|---|---:|---:|
| Exact decision accuracy | 68.4% | 89.5% |
| Malicious detection rate | 66.7% | 100% |
| Ambiguous escalation rate | 50.0% | 100% |
| Legitimate false-positive rate | 16.7% | 33.3% |

The branch's extra false positive is deliberate evidence: a contact lookup by `email` is blocked by the fail-closed default destination-parameter list (fixable per tool). On the original 12 seeds the branch reproduces `main`'s results exactly (91.7%, 25% false positives). These values apply only to the included controlled dataset. See the [latest evaluation report](evaluation/latest/REPORT.md) and the [per-seed comparison](evaluation/BRANCH_COMPARISON.md).

## Repository structure

```text
backend/      FastAPI governance API, persistence, and security pipeline
sdk/          Python SDK: ToolGuard core + LangChain/LangGraph, raw-loop, Claude Agent SDK adapters
gateway/      MCP gateway (asgp-gateway) for MCP clients you don't own
tests_support/ Shared in-process gateway harness for adapter and gateway tests
frontend/     React and TypeScript operations dashboard
demo/         Controlled tools, attack lab, and labeled scenarios
evaluation/   Generated JSON, CSV, and Markdown results
docs/         Architecture, phases, defense material, deployment guides,
              context/ (design source of truth, reviews, paper summaries) and plan/
```

## Documentation

### Core design

- [Design source of truth (final hybrid design, literature, known errors)](docs/context/DESIGN.md)
- [Branch implementation plan and status](docs/plan/IMPLEMENTATION_PLAN.md)
- [MCP gateway guide](gateway/README.md)
- [Original vision](Plan.txt)
- [MVP scope](docs/MVP_SCOPE.md)
- [Threat model](docs/THREAT_MODEL.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Implementation roadmap](docs/ROADMAP.md)
- [Limitations and honest security claims](docs/LIMITATIONS.md)

### Delivery and presentation

- [Phase 0–12 delivery documents](docs/ROADMAP.md)
- [Local deployment](docs/DEPLOYMENT.md)
- [Committee demo script](docs/DEMO_SCRIPT.md)
- [Presentation outline](docs/PRESENTATION_OUTLINE.md)
- [Thesis figures](docs/THESIS_FIGURES.md)

### Arabic and English guides

- [الدليل العربي الكامل](docs/PROJECT_COMPLETE_GUIDE_AR.md)
- [أسئلة وأجوبة المناقشة](docs/DEFENSE_QA_AR.md)
- [دليل مشاركة المشروع](docs/SHARING_GUIDE_AR.md)
- [Complete project guide — English](docs/PROJECT_COMPLETE_GUIDE_EN.md)
- [Defense questions and answers — English](docs/DEFENSE_QA_EN.md)
- [Project sharing guide — English](docs/SHARING_GUIDE_EN.md)

## Technology stack

- Backend: Python, FastAPI, Pydantic, SQLAlchemy, Alembic
- Database: PostgreSQL; SQLite for isolated tests and local evaluation
- Cryptography: Ed25519 and SHA-256
- Frontend: React, TypeScript, Vite
- Deployment: Docker and Docker Compose
- Testing: pytest, Ruff, TypeScript build, Oxlint

## Security boundary

ASGP is an integration-boundary control, not a universal agent sandbox. A valid signature proves request origin and integrity, not semantic safety. The current injection and behavioral detectors are explainable prototype signals, and the audit is tamper-evident rather than externally immutable. Review [LIMITATIONS.md](docs/LIMITATIONS.md) before making security claims.

## Project status

All roadmap phases from foundation through delivery are complete in `main`. This branch adds the hybrid pipeline, framework adapters and the MCP gateway (see the implementation plan). Future work: an AgentDojo run and an independent dataset, tuning embedding thresholds and evaluating the local judge, rate limiting, exporting audit heads outside the database, a streamable-HTTP gateway transport, and dashboard pages for drafts and policies.
