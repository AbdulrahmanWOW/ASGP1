# ASGP Implementation Roadmap

The realistic implementation is divided into **13 phases**. Each phase finishes with working tests and documentation before the next phase begins.

## Phase 0 — Foundation and contracts

**Status:** Complete (2026-09-07)

**Goal:** establish a runnable repository and freeze the core terminology and interfaces.

**Work**

- Initialize repository structure and developer tooling.
- Create the FastAPI and SDK package skeletons.
- Add configuration and safe logging conventions.
- Define initial Pydantic domain schemas and decision enums.
- Record architecture decisions.

**Acceptance criteria**

- Backend health endpoint runs locally.
- Backend and SDK tests run with one command each.
- `ALLOW`, `BLOCK`, and `ESCALATE` domain objects are validated.
- No database, AI service, or frontend is required to pass the tests.

## Phase 1 — First end-to-end security slice

**Status:** Complete (2026-09-07)

**Goal:** prove that ASGP can stop a tool before execution.

**Work**

- In-memory session and intent permissions.
- Tool registry and Python wrapper.
- One deterministic allow/deny policy.
- Verification endpoint and audit event.
- Demo tools with execution counters.

**Acceptance criteria**

- An allowed wrapped tool executes once.
- A blocked wrapped tool never executes.
- Both attempts produce explainable audit events.
- API or network failure causes protected execution to fail closed.

## Phase 2 — Persistence, sessions, and policies

**Status:** Complete (2026-09-07)

**Goal:** replace temporary state with the durable core model.

**Work**

- PostgreSQL and migrations.
- Session lifecycle and immutable/versioned intent anchor.
- Validated JSON policy format and operators.
- Resource/path/destination boundary policies.
- Parameter redaction rules.

**Acceptance criteria**

- Sessions, policies, actions, decisions, and audit events survive restart.
- Invalid policies are rejected.
- Permission expansion requires an explicit new anchor version.
- Path traversal and forbidden external destination tests pass.

## Phase 3 — Decision, risk, and approval

**Status:** Complete (2026-09-07)

**Goal:** support uncertain actions without silently executing them.

**Work**

- Decision precedence rules.
- Deterministic risk calculation with reasoned deltas.
- Expiring approval workflow bound to an action digest.
- Session revocation as the MVP form of termination.

**Acceptance criteria**

- Medium/uncertain risk creates `ESCALATE`.
- The tool waits and only executes after valid approval.
- Rejection or expiry prevents execution.
- Approval cannot be reused for modified parameters or another action.

## Phase 4 — Request integrity and replay defense

**Status:** Complete (2026-09-07)

**Goal:** protect action-request integrity within the integration boundary.

**Work**

- Canonical serialization and action digests.
- Nonces, timestamps, expiry, and sequence checks.
- Optional Ed25519 identity for the integrated demo agent.
- Public-key registration and key-status handling.

**Acceptance criteria**

- Modified, expired, duplicate, and incorrectly signed requests are blocked.
- Cryptographic failures override all semantic scores.
- Documentation states that signatures prove origin/integrity, not safety.

## Phase 5 — Semantic and behavioral signals

**Status:** Complete (2026-09-07)

**Goal:** detect risky intent drift and multi-step behavior.

**Work**

- `AIProvider` interface and deterministic `MockProvider`.
- Structured intent-alignment result.
- Injection heuristics with evidence and confidence.
- Stateful rules for scope creep, repeated denials, data staging, and exfiltration sequences.
- Integration of findings into the risk engine.

**Acceptance criteria**

- Automated tests never require a paid API.
- Malformed provider output is rejected safely.
- A valid signature cannot override a policy or high-risk sequence.
- At least one false-positive legitimate workflow test passes.

## Phase 6 — Tamper-evident audit and observability

**Status:** Complete (2026-09-07)

**Goal:** make every decision inspectable and verify audit continuity.

**Work**

- SHA-256 hash chaining using canonical audit entries.
- Chain verification and broken-chain reporting.
- Per-stage timing and error metrics.
- Secret and sensitive-parameter redaction tests.

**Acceptance criteria**

- Editing or deleting an interior event is detected where continuity permits.
- Each decision exposes stage timings and reason codes.
- Known secret fields never appear in stored events or application logs.

## Phase 7 — Dashboard and live demonstration

**Status:** Complete (2026-09-07)

**Goal:** make the security behavior understandable to users and the committee.

**Work**

- React dashboard and API integration.
- Overview, sessions, event detail, approvals, risk history, and audit status.
- Polling first; WebSocket is optional.
- Plain-language and technical explanations.

**Acceptance criteria**

- A reviewer can run the complete stack locally.
- Pending approvals can be accepted or rejected from the UI.
- Blocked actions show all contributing findings without exposing secrets.
- Audit verification is visible.

## Phase 8 — Attack lab, evaluation, and delivery

**Status:** Complete (2026-09-07)

**Goal:** turn the implementation into a defensible graduation project.

**Work**

- Controlled demo inbox, file area, mail sender, and upload destination.
- Labeled legitimate, malicious, and ambiguous scenarios.
- Reproducible evaluation runner.
- Detection and latency reports plus selected ablation studies.
- Deployment guide, limitations, demo script, thesis figures, and presentation material.

**Acceptance criteria**

- The full demo runs from a clean documented setup.
- Dataset labels and metric calculations are reviewable.
- Results include false positives and failures, not only successful detections.
- No result depends on real private user data.

## Phase 9 — SDK-integrated demo agent

**Status:** Complete (2026-09-08)

Connect controlled tools to the real Python SDK and provide a one-command Docker profile that demonstrates `ALLOW`, `ESCALATE`, and `BLOCK` before execution.

## Phase 10 — Expanded evaluation metrics

**Status:** Complete (2026-09-08)

Expand the controlled evaluation to 60 traceable cases and publish three-class confusion, per-class and macro precision/recall/F1, security metrics, latency, and ablation results.

## Phase 11 — Content-ingress quarantine

**Status:** Complete (2026-09-08)

Scan tool-returned text before agent consumption. Release clean content and fail closed with `ContentQuarantined` while omitting suspicious raw content from the response.

## Phase 12 — Research dashboard

**Status:** Complete (2026-09-08)

Expose the generated evaluation artifact in the existing dashboard with metrics, confusion matrix, ablation comparisons, and honest limitations.

## Phase dependencies

```text
Phase 0 Foundation
   ↓
Phase 1 Vertical Slice
   ↓
Phase 2 Persistence
   ↓
Phase 3 Decisions & Approval
   ↓
Phase 4 Request Integrity
   ↓
Phase 5 Security Signals
   ↓
Phase 6 Audit & Metrics
   ↓
Phase 7 Dashboard
   ↓
Phase 8 Evaluation & Delivery
   ↓
Phase 9 Integrated Demo Agent
   ↓
Phase 10 Expanded Evaluation
   ↓
Phase 11 Content Ingress
   ↓
Phase 12 Research Dashboard
```

## Suggested ownership for a four-person team

| Track | Primary responsibility |
|---|---|
| Backend/security | Sessions, policies, decisions, integrity |
| SDK/demo | Tool wrapper, example agent, controlled tools |
| Frontend | Dashboard, approvals, event explanations |
| Research/testing | Threat scenarios, dataset, metrics, documentation |

Ownership does not remove code review or integration responsibility. Phase 1 should be completed collaboratively because it establishes the contract used by every track.

## Definition of done for every phase

- Acceptance criteria are demonstrated by automated tests where possible.
- Security-sensitive failure paths are tested.
- Changed interfaces and limitations are documented.
- No placeholder is presented as a completed security control.
- The previous end-to-end flow remains working.
