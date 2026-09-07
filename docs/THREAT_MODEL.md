# ASGP Threat Model

## 1. Protected assets

- User intent and approved permissions.
- Files, messages, and other resources exposed through wrapped tools.
- External communication destinations.
- Session state, decisions, policies, and approvals.
- Agent identity material and request nonces.
- Audit history and evaluation evidence.

## 2. Trust boundaries

```text
User / Dashboard
       |
       | authenticated API boundary
       v
ASGP Backend -------- AI Provider (untrusted security signal)
       |
       | verification boundary
       v
Python SDK / Agent -------- Retrieved content (untrusted)
       |
       | execution boundary
       v
Registered Demo Tools -------- External destinations (untrusted)
```

The AI provider is not an authorization authority. Its output is parsed, bounded, and treated as one fallible signal.

## 3. Assumed attackers and failures

- Malicious instructions embedded in email, web, or document content.
- An agent that drifts from the user's original objective.
- A legitimate agent attempting an excessive or dangerous sequence of actions.
- A caller replaying a previously valid request.
- Modification of action parameters between verification steps.
- A user or process attempting to expand session permissions.
- Tampering with stored audit history.
- Accidental leakage of secrets through logs or dashboard fields.
- Failure, timeout, or malformed output from an AI provider.

## 4. Threats and MVP mitigations

| Threat | Primary mitigation | Residual limitation |
|---|---|---|
| Tool call outside user scope | Intent permissions and hard policy rules | Semantic scope can be ambiguous |
| External data exfiltration | Resource/destination rules and behavioral sequences | Unregistered tools remain outside control |
| Prompt injection | Content heuristics, intent comparison, and action policy | Detection is probabilistic and incomplete |
| Replay | Nonce, timestamp, sequence, and request store | Depends on shared backend state |
| Payload modification | Canonical digest; optional Ed25519 signature | Endpoint compromise is not solved |
| Silent permission expansion | Immutable anchor version and explicit approval | Authorized users may approve unsafe scope |
| Audit deletion/modification | Hash-chain verification | An attacker controlling storage can replace all history and checkpoints |
| Malicious/incorrect AI result | Schema validation and deterministic policy priority | Semantic quality may still vary |
| Approval reuse | Bind approval to action digest, user, and expiry | Stolen authenticated user session remains a risk |
| Backend unavailable | Fail closed for protected tool execution | Availability is sacrificed for safety |

## 5. Non-goals and honest security boundary

ASGP does not protect direct tool execution outside its integration layer. It does not secure a fully compromised host, prove the truthfulness of an LLM, or guarantee detection of novel prompt injections. Ed25519, when implemented, establishes origin and integrity for an integrated identity; it does not establish that an action is safe.

## 6. Decision precedence

Hard failures take priority:

1. Revoked or unknown session → `BLOCK`.
2. Invalid/expired/replayed protected request → `BLOCK`.
3. Explicit deterministic deny policy → `BLOCK`.
4. High-risk but uncertain conditions → `ESCALATE`.
5. Remaining signals are aggregated into an explainable risk result.
6. Only a sufficiently safe result → `ALLOW`.

No AI-generated recommendation can override steps 1–3.

## 7. Validation scenarios

- Allowed local read and write.
- Forbidden external recipient.
- Path traversal outside an allowed directory.
- Modified parameters after request creation.
- Duplicate nonce and request replay.
- Expired approval.
- Prompt-injected message leading to upload attempt.
- Many reads followed by one external send.
- Repeated blocked attempts.
- Legitimate multi-step workflow that should not trigger a false positive.
