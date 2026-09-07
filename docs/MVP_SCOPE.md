# ASGP MVP Scope

## 1. Objective

Build a working and measurable security gateway for tool-using AI agents. ASGP must intercept an action before a wrapped tool executes, evaluate independent security signals, produce an explainable decision, and store a tamper-evident audit event.

The MVP prioritizes a complete vertical system over broad framework or provider support.

## 2. In scope

### Core platform

- Session creation with original user intent.
- Structured session permissions and resource boundaries.
- A Python SDK for wrapping registered Python tools.
- Canonical tool-call requests.
- Deterministic policy evaluation.
- Replay and request-expiry protection.
- Simple intent-alignment scoring through a provider interface.
- Explainable stateful behavioral rules.
- A deterministic session risk score from `0` to `100`.
- A decision engine producing `ALLOW`, `BLOCK`, or `ESCALATE`.
- Human approval and rejection of escalated actions.
- Tamper-evident hash-chained audit events.
- A web dashboard for sessions, calls, approvals, findings, and audit status.
- Timing measurements for each pipeline stage.

### Demo environment

The demonstration uses controlled or mocked tools so no real data is exposed:

- `read_message(message_id)`
- `list_demo_files(path)`
- `read_demo_file(path)`
- `write_summary(path, content)`
- `send_demo_email(recipient, subject, body)`
- `upload_demo_file(path, destination)`

The last two tools simulate external communication and are useful for exfiltration scenarios.

### Evaluation

- A labeled dataset of approximately 100–200 reproducible scenarios.
- Legitimate, malicious, and ambiguous cases.
- Precision, recall, F1, true-positive rate, and false-positive rate.
- Average, median, and P95 verification latency.
- Per-stage pipeline latency.
- Ablation comparison for selected security layers.

## 3. Simplified implementations

| Research vision | MVP implementation |
|---|---|
| Universal agent protection | One demo agent and documented SDK integration contract |
| All tool interception | Registered tools routed through the SDK only |
| Complex multi-agent chain | One agent; optional two-agent delegation extension |
| ML behavioral IDS | Explainable stateful rules |
| Perfect injection detection | Heuristics plus optional model signal, with confidence and evidence |
| Natural-language policy engine | Validated structured JSON policies |
| Many AI providers | Deterministic mock plus one optional real provider |
| Tamper-proof storage | Tamper-evident hash chain |
| Process termination | Session revocation and rejection of later calls |
| Distributed deployment | Docker Compose deployment on one machine |

## 4. Explicitly out of scope

- Intercepting tools that bypass the SDK or gateway.
- Sandboxing arbitrary untrusted Python code.
- Guaranteeing complete prompt-injection detection.
- Proving that a validly signed action is semantically safe.
- Training a production behavioral ML model.
- Supporting every agent framework or LLM provider.
- Enterprise high availability, Kubernetes, or multi-region deployment.
- Production key-management infrastructure.
- Claiming the audit log is immutable or tamper-proof.

## 5. MVP security invariants

1. A wrapped tool never executes before an `ALLOW` decision or an approved `ESCALATE` decision.
2. A hard policy denial cannot be overridden by an AI score.
3. Invalid, expired, or replayed protected requests fail closed.
4. Permission expansion cannot happen silently during a session.
5. Audit parameters are redacted or summarized before persistence.
6. Every risk-score change records its previous value, delta, new value, and reason.
7. An approval is bound to one exact action and expires.
8. A revoked session cannot submit new actions.

## 6. Graduation deliverables

- Backend source code and automated tests.
- Python integration SDK and example agent.
- React dashboard.
- Docker Compose environment.
- Seeded demo data and attack scenarios.
- Evaluation runner and generated metrics/charts.
- Architecture, threat-model, API, and deployment documentation.
- Short demonstration script and final presentation material.

## 7. Stretch goals

- Ed25519 agent identity and signed delegation.
- A two-agent orchestration demonstration.
- Content-ingress scanning before retrieved text reaches the agent.
- Live WebSocket event updates.
- One real hosted or local LLM provider.
- Exportable session security report.
