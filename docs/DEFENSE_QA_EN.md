# ASGP Defense Questions and Answers

This document collects the project-defense questions beginning with the request to present ASGP as if speaking to the examination committee, followed by the detection, missing-layer, and universal-integration questions.

## 1. What is ASGP?

ASGP is a security-governance platform for tool-using AI agents. It records the user's intent and permissions, intercepts each integrated tool call before execution, validates integrity and policy, evaluates semantic and behavioral signals, calculates risk, and returns `ALLOW`, `BLOCK`, or `ESCALATE`. Every decision is redacted, explained, hash-chained, and displayed on a dashboard.

## 2. What problem does it solve?

An AI agent can receive a legitimate task but encounter malicious instructions inside email, files, web content, or retrieved documents. If the agent follows those instructions, it may call a dangerous tool. ASGP places an independent enforcement layer at the tool boundary so that the LLM is not its own final security authority.

## 3. Is the project complete and ready for examination?

It is complete as a graduation security prototype. Its backend, SDK, dashboard, controlled lab, evaluation, and tests work. A deterministic demo agent using the real SDK would make the live presentation more convincing, because the evaluation runner currently invokes the gateway directly. A paid LLM is not required for that demonstration.

## 4. Must ASGP be connected to one particular agent?

No. It is model-agnostic and framework-agnostic but integration-dependent. Any agent can integrate through REST, an SDK, a framework adapter, or an MCP proxy. Tools that bypass the integration boundary remain outside ASGP's protection.

## 5. How does detection work, and where is AI used?

ASGP uses a hybrid pipeline:

```text
Hard deterministic checks
→ Intent alignment
→ Prompt-injection analysis
→ Behavioral analysis
→ Risk aggregation
→ Decision
```

Session state, tool permissions, paths, destinations, signatures, expiry, and replay have deterministic answers and do not require AI. They take precedence over semantic scoring.

Intent alignment is exposed through an `AIProvider` contract returning a score, reason, and risk factors. The prototype uses a deterministic local provider so tests require no API key and remain reproducible. A production provider can be added without changing the decision pipeline.

The injection detector currently uses explainable patterns. The behavioral analyzer uses session history. These components create findings and risk deltas; no AI provider directly authorizes execution.

## 6. What happens if the AI provider fails?

Malformed or failed provider output is rejected by schema validation and converted into an `AI_PROVIDER_FAILURE` finding and additional risk. The system does not treat detector failure as evidence that an action is safe.

## 7. Why not let the agent decide whether an action is malicious?

The agent is part of the attack surface. LLMs are probabilistic, may be redirected by untrusted content, and can lose track of constraints during long workflows. Authorization therefore belongs to an independent deterministic layer. AI is an advisory security signal, not the final authority.

## 8. Are regular expressions enough for prompt-injection detection?

No. They are fast and explainable but can miss paraphrases, obfuscation, and other languages, and can flag a benign quotation. The evaluation intentionally demonstrates this false positive. A production design would combine fast heuristics with a context-aware classifier for uncertain cases while retaining hard-policy precedence.

## 9. Which layers are implemented?

1. Session validation.
2. Versioned Intent Anchor and permissions.
3. Tool registry.
4. Ed25519 integrity and replay defense.
5. Deterministic policy engine.
6. Intent-alignment provider interface and deterministic mock.
7. Prompt-injection heuristics.
8. Stateful behavioral rules.
9. Explainable risk engine.
10. `ALLOW/BLOCK/ESCALATE` decision precedence.
11. Human approval and session revocation.
12. Redaction and tamper-evident audit.
13. Metrics and per-stage latency.
14. Dashboard, controlled attack lab, and reproducible evaluation.

## 10. Which layers were simplified or excluded?

- Redis was unnecessary for the single-machine MVP.
- Polling replaces WebSockets.
- The provider contract is implemented, but no production LLM provider is enabled.
- Heuristics replace an advanced ML injection classifier.
- The scanner is not yet a universal ingress proxy for every email, PDF, or RAG result.
- Explainable stateful rules replace a trained behavioral IDS.
- Trust and risk were combined into one visible risk score.
- Session revocation replaces generic process termination.
- Signed multi-agent delegation is not implemented.
- Arbitrary-code sandboxing is outside scope.
- Enterprise KMS, SSO, RBAC, and multi-tenancy are outside the MVP.
- The audit is tamper-evident rather than externally immutable.
- The evaluation contains 12 cases rather than the research target of 100–200.
- A fully orchestrated live demo agent is the highest-priority presentation improvement.

## 11. Why combine trust and risk?

Two separate scores can conflict and obscure the decision. ASGP exposes one bounded risk score. Every change records its previous value, delta, new value, and reason, making the result easier to test and explain.

## 12. Why replace `TERMINATE` with session revocation?

ASGP may not own the agent process or container. Claiming generic process termination would be misleading. It can guarantee that a revoked security session cannot submit another governed action.

## 13. Is the audit immutable?

No. The accurate term is tamper-evident. Hash chaining reveals continuity violations, but it does not prevent a database administrator from deleting the entire database and does not supply an external trusted timestamp. Production hardening would require append-only storage or external anchoring.

## 14. How should the evaluation be interpreted?

On the controlled 12-case dataset, malicious detection is 100%, ambiguous escalation is 100%, exact decision accuracy is 91.7%, and the legitimate false-positive rate is 25%. The policy-only ablation reduces malicious detection to 66.7%. These numbers describe only the included lab and must not be generalized to production traffic.

## 15. Who are the competitors?

The category includes prompt shields, managed cloud guardrails, and frameworks such as NeMo Guardrails and LlamaFirewall. Many are broader or more production-ready. ASGP's focus is action governance: intent, permission boundaries, request signatures, pre-execution decisions, human approval, stateful risk, and hash-chained audit in one inspectable prototype. The claim is a coherent research implementation, not universal commercial superiority.

## 16. How can ASGP become a product that connects to any agent?

The core API remains stable while multiple integration paths are provided:

1. Generic REST API for any language.
2. Existing Python SDK and a future JavaScript SDK.
3. LangChain, OpenAI Agents, CrewAI, and AutoGen adapters.
4. An MCP security proxy in front of real MCP servers.
5. A central tool-execution gateway that owns credentials and invokes real services.

```text
Agent
  ↓
SDK / Framework Adapter / MCP Proxy
  ↓
ASGP Enforcement Gateway
  ↓
Policy + Detection + Approval + Audit
  ↓
ASGP-managed Tool Connector
  ↓
Real Service
```

## 17. How can SDK bypass be prevented?

An SDK wrapper can be bypassed if the agent can still access the original tool or credentials. Strong product enforcement keeps credentials outside the agent and restricts the network or tool endpoint so that only ASGP can invoke it. A central execution gateway or controlled MCP proxy is therefore stronger than an optional wrapper.

## 18. What is a realistic product roadmap?

### Integration proof

Build a demo agent, one-command reset/seed flow, and live allow, block, and escalate scenarios.

### Universal integration

Add REST documentation, Python and JavaScript SDKs, MCP proxy, framework adapters, API authentication, and idempotency.

### Product enforcement

Add credential isolation, tool connectors, multi-tenancy, RBAC, SSO, secret management, rate limits, and audit export.

### Production detection

Add real or local model providers, multilingual and context-aware classifiers, larger datasets, threshold calibration, and detector version monitoring.

## 19. What is the best closing statement for the committee?

> ASGP does not claim to make every AI agent universally safe. It provides an independent, explainable, and testable layer that prevents integrated tools from executing actions outside the user's intent and permissions before harm occurs.
