# ASGP MVP Architecture

## 1. System context

```text
                    +---------------------+
                    | React Dashboard     |
                    | status + approvals  |
                    +----------+----------+
                               |
                               v
+---------+     +---------+   +----------------------+   +------------+
| User    +---->| AI Agent+-->| Python ASGP SDK      +-->| Demo Tools |
+---------+     +----+----+   | intercepts execution |   +------------+
                    |        +-----------+----------+
                    | retrieved content  |
                    v                    v
              +-----------+     +----------------------+
              | Content   |     | FastAPI ASGP Backend |
              | sources   |     | security pipeline    |
              +-----------+     +-----+------------+---+
                                      |            |
                                      v            v
                                +----------+   +-----------+
                                |PostgreSQL|   |AI Provider|
                                +----------+   +-----------+
```

The content scanner is initially a bounded detector used by the demo. A future ingress gateway may scan and label content before it reaches the agent.

## 2. Verification flow

```text
Tool-call request
      |
      v
Session and request validation
      |
      v
Deterministic policy engine -------- hard deny ------> BLOCK
      |
      v
Intent alignment signal
      |
      v
Injection/content evidence
      |
      v
Behavioral rules
      |
      v
Risk calculation
      |
      v
Decision engine ------> ALLOW / BLOCK / ESCALATE
      |
      v
Hash-chained audit event + timing metrics
```

## 3. Main components

### Backend

- **Session service:** lifecycle, intent anchor, permissions, and revocation.
- **Tool registry:** tool schemas and sensitivity metadata.
- **Request validator:** canonicalization, expiry, nonce, and optional signatures.
- **Policy engine:** deterministic evaluation of validated structured rules.
- **Signal services:** intent, injection, and behavioral findings.
- **Risk engine:** deterministic bounded score with a trace of changes.
- **Decision engine:** explicit precedence and decision reason codes.
- **Approval service:** exact-action, expiring approval requests.
- **Audit service:** redaction, hash chaining, and chain verification.
- **Metrics service:** per-stage and total latency.

### SDK

- Session client.
- Tool decorator/wrapper.
- Parameter normalization.
- Verification request client.
- Approval polling for the MVP.
- Fail-closed error behavior.

### Dashboard

- System overview.
- Session details and intent permissions.
- Action timeline and technical findings.
- Pending approval queue.
- Risk-score history.
- Audit-chain verification status.
- Evaluation results.

## 4. Initial domain model

| Entity | Purpose |
|---|---|
| `Session` | Active security context and status |
| `IntentAnchor` | Original intent, permission set, canonical hash, version |
| `AgentIdentity` | Integrated agent identity and optional public key |
| `ToolDefinition` | Tool name, schema, sensitivity, execution metadata |
| `Policy` | Validated structured security rule |
| `ActionRequest` | Exact normalized action awaiting a decision |
| `SecurityFinding` | Evidence produced by one pipeline stage |
| `RiskChange` | Explainable score transition |
| `Decision` | Result, reason codes, and pipeline timing |
| `ApprovalRequest` | Human decision bound to one action digest |
| `AuditEvent` | Redacted hash-chained event |

## 5. Suggested repository structure

```text
asgp/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   └── tests/
├── sdk/
│   ├── asgp_sdk/
│   └── tests/
├── frontend/
├── demo/
│   ├── agent/
│   ├── tools/
│   └── scenarios/
├── evaluation/
├── docs/
├── docker-compose.yml
└── README.md
```

## 6. Technology choices

- FastAPI, Pydantic, and SQLAlchemy.
- PostgreSQL for durable state.
- React for the dashboard.
- `pytest` for backend, SDK, and security scenario tests.
- Docker Compose for the final local deployment.
- Redis is deferred until a demonstrated need exists, such as multi-instance transient state or real-time delivery.
- The AI interface starts with a deterministic mock. A single real provider is optional.

## 7. Initial API surface

```text
POST   /api/v1/sessions
GET    /api/v1/sessions/{session_id}
POST   /api/v1/sessions/{session_id}/revoke
POST   /api/v1/actions/verify
GET    /api/v1/actions/{action_id}
GET    /api/v1/approvals
POST   /api/v1/approvals/{approval_id}/resolve
GET    /api/v1/audit/{session_id}
POST   /api/v1/audit/{session_id}/verify
GET    /api/v1/metrics/evaluation
```

The detailed request/response contract will be frozen during the core-domain phase rather than guessed prematurely.

## 8. Key architectural decisions

- A modular monolith is preferred over microservices.
- Policies are data, not executable expressions.
- Risk and trust are not separate hidden concepts; the MVP exposes one explainable `risk_score`.
- PostgreSQL is the source of truth.
- Approval does not expand general session scope; it authorizes one exact action.
- Content safety and action authorization remain distinct layers.
