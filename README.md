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

1. Session and Intent Anchor validation.
2. Tool registration and request-schema validation.
3. Ed25519 signature, nonce, expiry, and replay checks.
4. Deterministic tool, path, destination, and structured-policy enforcement.
5. Provider-independent intent-alignment signal.
6. Prompt-injection and behavioral findings.
7. Explainable bounded risk calculation.
8. `ALLOW`, `BLOCK`, or `ESCALATE` decision precedence.
9. Secret-redacted, hash-chained audit and timing metrics.

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
.\.venv\Scripts\python.exe -m pytest backend\tests sdk\tests
.\.venv\Scripts\python.exe -m ruff check backend sdk demo
```

From the `frontend` directory:

```powershell
pnpm build
pnpm lint
```

At the documented delivery point, all **63 automated tests** and frontend production checks pass.

## Reproducible evaluation

```powershell
.\.venv\Scripts\python.exe -m demo.evaluate
```

The controlled evaluation uses 12 reviewable seeds exercised as 60 deterministic traceable cases:

| Metric | Result |
|---|---:|
| Exact decision accuracy | 91.7% |
| Macro precision | 95.2% |
| Macro recall | 91.7% |
| Macro F1 | 92.7% |
| Malicious detection rate | 100% |
| Ambiguous escalation rate | 100% |
| Legitimate false-positive rate | 25% |

These values apply only to the included controlled dataset. The retained false positive and policy-only ablation failures are documented rather than hidden. See the [latest evaluation report](evaluation/latest/REPORT.md).

## Repository structure

```text
backend/      FastAPI governance API, persistence, and security pipeline
sdk/          Python integration SDK and protected-tool wrappers
frontend/     React and TypeScript operations dashboard
demo/         Controlled tools, attack lab, and labeled scenarios
evaluation/   Generated JSON, CSV, and Markdown results
docs/         Architecture, phases, defense material, and deployment guides
```

## Documentation

### Core design

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

All roadmap phases from foundation through the integrated demo agent, ingress quarantine, expanded evaluation, research dashboard, and delivery are complete. High-value future work includes MCP/framework-specific adapters, centralized credential-isolated tool execution, independent real-world datasets, and production identity and access controls.
