# Phase 5 — Semantic and Behavioral Security Signals

## Status

**Complete — 2026-09-07.**

Verification environment: Python 3.13.2 on Windows.

- Tests: `49 passed`.
- Ruff lint: passed.
- Ruff format check: passed.
- Full Alembic chain through revision `0004_phase5` executed successfully on SQLite.
- Full migration chain compiled successfully with the PostgreSQL dialect.

## Delivered

- Model-independent `AIProvider` protocol.
- Deterministic local `MockProvider` used by default and in automated tests.
- Strict structured intent-alignment output with score, reason, and risk factors.
- Safe handling of provider exceptions and malformed/out-of-range responses.
- Prompt-injection heuristic detector with confidence, severity, evidence, and risk delta.
- Standalone content-ingress scanning endpoint for use before content reaches an agent.
- Bounded recursive scanning of text-bearing action parameters.
- Stateful behavioral analysis based on durable action/decision history.
- Detection of repeated blocked actions, data-staging sequences, and reconnaissance patterns.
- Durable security findings linked to action and session IDs.
- Session findings endpoint for dashboard and research use.
- Integration of semantic and behavioral deltas into the deterministic Risk Engine.
- SDK response contracts for intent score and structured findings.

## Security-signal flow

```text
Hard session / crypto / policy controls
                |
                | pass
                v
Intent Alignment ----+
Injection Evidence ---+--> Explainable Risk Engine --> ALLOW / ESCALATE / BLOCK
Behavior History -----+
                |
                v
      Durable Security Findings
```

Hard failures still return immediately. An AI score or behavioral finding cannot override an explicit policy denial, invalid signature, replay, revoked identity, or expired request.

## Intent alignment

The provider receives a bounded context containing the original intent, allowed tools, current tool, and current parameters. It returns:

```json
{
  "score": 0.25,
  "reason": "External action is not evident in the original intent.",
  "risk_factors": ["external_action_not_stated"]
}
```

Initial interpretation:

- Score below `0.30` → high finding, `+45` risk.
- Score from `0.30` to below `0.60` → medium finding, `+20` risk.
- Score `0.60` or above → no alignment finding.
- Provider/schema failure → medium finding, `+40` risk and normally `ESCALATE`.

The provider never returns the authorization decision.

## Injection detection

The MVP detector recognizes signals for:

- Instruction override.
- Authority impersonation.
- Data-exfiltration instructions.
- Requests to conceal actions from the user.
- Long encoded payloads.

High-confidence matches add enough risk to block a low-sensitivity action. Evidence records the detector category rather than copying raw malicious or sensitive content.

The endpoint is:

```text
POST /api/v1/content/scan
```

This allows a demo content gateway to scan retrieved email or document text before exposing it to the agent.

## Behavioral detection

The analyzer reads recent durable activity and can emit:

- `REPEATED_BLOCKED_ACTIONS`
- `DATA_STAGING_SEQUENCE`
- `RECONNAISSANCE_SEQUENCE`

For example, three recent read/list actions followed by an upload or send action produce a high-severity data-staging finding.

Findings are available through:

```text
GET /api/v1/findings/{session_id}
```

## Risk aggregation rule

The action delta is the tool-sensitivity delta plus all finding deltas, bounded to the `0–100` session range. A low-sensitivity decay is applied only when no security finding exists, so it cannot cancel a warning in the same action.

## Scenarios demonstrated by tests

- Legitimate workflow remains allowed without a finding.
- Unstated external communication escalates due to low alignment.
- High-confidence injected instructions block an otherwise allowed read.
- Content is scanned independently before agent use.
- Multiple reads followed by upload trigger data-staging escalation.
- Malformed provider output fails safely to escalation.
- Hard policy denial precedes semantic analysis.
- Findings persist for later inspection.

## Known limitations

- `MockProvider` is a deterministic baseline, not a semantic LLM.
- Lexical intent alignment is intentionally simple and language-dependent.
- Heuristic injection detection has both false-positive and false-negative risk.
- Action-parameter scanning cannot protect content fetched outside the ASGP integration path.
- Behavioral thresholds are initial research values and require evaluation/calibration.
- The current history model uses tool/outcome sequences, not trained user-specific baselines.
- No external paid AI API is required or called by automated tests.
