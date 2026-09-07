# ASGP Complete Project Guide

## 1. Project definition

**ASGP — Agent Security Governance Platform** is a security layer placed between an AI agent and the tools it can use. It intercepts security-relevant tool calls before execution and returns one of three decisions:

- `ALLOW`: execute the requested tool.
- `BLOCK`: prevent execution.
- `ESCALATE`: pause and request a human decision.

ASGP does not claim to secure every possible agent action. Its enforcement boundary covers registered tools routed through the ASGP SDK or gateway.

## 2. Problem statement

Modern AI agents can read files and messages, call APIs, send email, upload data, and execute multi-step workflows. A user may provide a legitimate objective, while an untrusted document contains an indirect prompt injection asking the agent to ignore that objective and leak data. An LLM is probabilistic and should not be the final authorization authority.

ASGP moves action authorization into an independent, inspectable layer that runs before the tool.

## 3. End-to-end flow

```text
User Intent
    ↓
Intent Anchor + Permissions
    ↓
Integrated AI Agent
    ↓
ASGP SDK / Tool Wrapper
    ↓
Signed Action Request
    ↓
Session → Integrity → Policy → Alignment → Injection → Behavior → Risk
    ↓
ALLOW / BLOCK / ESCALATE
    ↓
Tool Execution or Human Approval
    ↓
Tamper-Evident Audit + Dashboard
```

## 4. Completed implementation phases

### Phase 0 — Foundation

- Backend, SDK, demo, and documentation structure.
- FastAPI and Pydantic contracts.
- `ALLOW`, `BLOCK`, and `ESCALATE` domain decisions.
- Threat model, MVP scope, architecture decisions, safe logging, and configuration.

### Phase 1 — First security vertical slice

- Session creation with intent permissions.
- Tool registry and Python tool wrapper.
- Pre-execution allow and block decisions.
- Fail-closed SDK behavior.
- Counted demo tools proving that blocked tools never execute.
- Explainable audit events.

### Phase 2 — Persistence and policy

- PostgreSQL, SQLAlchemy, and Alembic migrations.
- Persistent sessions, anchors, policies, actions, decisions, and audit events.
- Versioned Intent Anchors.
- Validated structured JSON policies without executable expressions.
- File-path and destination boundaries.
- Sensitive-field redaction.

### Phase 3 — Risk and human approval

- Bounded risk score from 0 to 100.
- Explainable previous score, delta, new score, and reason.
- Expiring approval workflow.
- Approval binding to one exact action digest.
- Protection against modified-action and cross-action approval reuse.
- Session revocation as the realistic MVP termination control.

### Phase 4 — Request integrity and replay defense

- Canonical serialization and SHA-256 action digests.
- Ed25519 agent signatures.
- Agent registration and revocation.
- Nonces, timestamps, expiry, and monotonic sequence numbers.
- Blocking of modified, duplicate, expired, or incorrectly signed requests.

### Phase 5 — Semantic and behavioral signals

- Provider-independent `AIProvider` interface.
- Deterministic local `MockProvider` for reproducible tests.
- Intent alignment scores and risk factors.
- Prompt-injection heuristics with confidence and evidence.
- Repeated-denial, data-staging, and reconnaissance rules.
- Integration of findings into the risk engine.

### Phase 6 — Audit and observability

- Per-session SHA-256 hash chains.
- Sequence, previous hash, and entry hash verification.
- Detection of interior modification or deletion where continuity permits.
- Per-stage and total pipeline latency.
- Error and decision metrics.
- Tests preventing secrets from reaching events or logs.

### Phase 7 — Dashboard

- Responsive React, TypeScript, and Vite dashboard.
- Command center, connectivity state, sessions, and intent boundaries.
- Risk history and decision stream.
- Human approval and rejection controls.
- Visible audit-chain verification.
- Plain-language and technical event explanations.
- Findings, safe parameters, and stage timings.
- Five-second polling and restricted local CORS.
- Dockerfiles and Docker Compose configuration.

### Phase 8 — Attack lab and evaluation

- Controlled local inbox, file area, mail sender, and upload sink.
- Containment preventing access outside the lab or to real destinations.
- Twelve labeled cases: four legitimate, two ambiguous, and six malicious.
- Reproducible evaluation runner.
- Full-pipeline and policy-only ablation modes.
- JSON, CSV, and Markdown reports.
- Deployment guide, demo script, limitations, presentation outline, and thesis figures.

## 5. Current protection layers

### Session and intent validation

The platform verifies that a session exists, remains active, and uses a versioned Intent Anchor containing the original objective and permission boundaries.

### Tool registry

Every governed tool has a name, description, sensitivity level, and optional signature requirement. Unknown tools fail closed.

### Cryptographic integrity

Ed25519 signatures, canonical payloads, action digests, nonces, timestamps, expiry, and sequences establish origin and integrity and defend against replay. A valid signature never proves semantic safety.

### Deterministic policy enforcement

Allow lists, deny lists, path boundaries, destination boundaries, and validated deny policies are evaluated without AI. A hard policy denial cannot be overridden by an AI score.

### Intent alignment

The provider interface compares the user's intent with the requested tool and returns structured alignment evidence. The evaluated prototype uses a deterministic local provider for reproducibility.

### Prompt-injection detection

Explainable heuristics identify instruction overrides, authority impersonation, exfiltration requests, hidden actions, and selected encoded payloads. This is a useful signal, not a claim of perfect detection.

### Behavioral analysis

Stateful rules inspect recent activity for repeated denials, multiple reads followed by an external action, data staging, and reconnaissance-like sequences.

### Risk and decision engine

Tool sensitivity and all findings modify one visible risk score. Low risk permits execution, medium risk escalates, and high risk blocks. Hard security failures block directly.

### Active response

A protected tool cannot run before `ALLOW` or a valid approval. Approvals can be rejected and sessions revoked. ASGP does not claim to terminate an operating-system process it does not own.

### Audit and observability

Every decision is redacted, timed, explained, hash-chained, and available for continuity verification.

## 6. Core data model

- `Session`: active security context and state.
- `IntentAnchor`: objective, permissions, version, and canonical hash.
- `AgentIdentity`: registered agent, public key, and status.
- `ToolDefinition`: registered tool and sensitivity.
- `Policy`: validated structured security rule.
- `ActionRequest`: exact proposed action before execution.
- `SecurityFinding`: evidence and confidence from a security layer.
- `RiskChange`: explainable score transition.
- `Decision`: outcome, reason codes, and timings.
- `Approval`: expiring human decision bound to an action.
- `AuditEvent`: redacted hash-chained decision record.

## 7. Secret handling

Fields such as `password`, `secret`, `token`, `api_key`, and `authorization` are redacted before persistence and appear as `[REDACTED]` in logs, events, reports, and the dashboard.

## 8. Current evaluation results

These results apply only to the controlled ASGP dataset:

| Metric | Result |
|---|---:|
| Scenarios | 12 |
| Exact decision accuracy | 91.7% |
| Malicious detection rate | 100% |
| Ambiguous escalation rate | 100% |
| Legitimate false-positive rate | 25% |
| Median pipeline latency | Approximately 10.8 ms on the test host |
| P95 pipeline latency | Approximately 13.3 ms on the test host |

The dataset deliberately retains a legitimate quotation containing attack language. The full pipeline blocks it, exposing a real false positive. The policy-only ablation avoids that false positive but misses two semantic attacks, reducing malicious detection to 66.7%.

## 9. Simplified or excluded capabilities

| Research vision | Current implementation |
|---|---|
| Universal agent protection | Registered tools routed through SDK/gateway |
| Production AI classifier | Replaceable provider interface with deterministic mock |
| ML behavioral IDS | Explainable stateful rules |
| Separate trust and risk engines | One explainable risk score |
| Generic `TERMINATE` | Session revocation |
| Tamper-proof storage | Tamper-evident hash chain |
| Multi-agent delegation chain | One registered agent identity per request |
| Redis and distributed deployment | PostgreSQL and single-machine Compose |
| WebSockets | Five-second polling |
| 100–200 evaluation cases | Twelve cases proving the methodology |
| Arbitrary-code sandbox | Explicitly out of scope |
| Enterprise KMS, SSO, and RBAC | Explicitly outside the MVP |

## 10. Differentiation

The market includes prompt shields, cloud guardrails, and broad guardrail frameworks. ASGP's graduation-project contribution is a complete and inspectable action-governance path combining intent anchoring, pre-execution enforcement, policy, signatures, behavioral state, human approval, audit continuity, and reproducible evaluation. It does not claim production superiority over major commercial platforms.

## 11. Value proposition

> Route AI-agent tools through ASGP to enforce user intent, policy, risk, human approval, and auditability before every sensitive action.

## 12. Project status

- Core architecture, backend, SDK, dashboard, attack lab, and evaluation are complete.
- 57 automated tests passed at the documented delivery point.
- Frontend production build and lint pass.
- The system is a strong, defensible graduation prototype.
- The highest-value next additions are a fully orchestrated demo agent, MCP/framework adapters, and centralized credential-isolated tool execution.
