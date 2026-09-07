# Graduation presentation outline

1. **Title and one-sentence contribution** — governance before agent tool execution.
2. **Problem** — indirect prompt injection, excessive permissions, and opaque agent actions.
3. **Scope** — the integrated SDK/gateway boundary and explicit non-goals.
4. **Architecture** — modular monolith, PostgreSQL, SDK, dashboard.
5. **Decision pipeline** — integrity, policy, alignment, injection, behavior, risk.
6. **ALLOW / BLOCK / ESCALATE** — precedence and fail-closed behavior.
7. **Human approval** — expiry and action-digest binding.
8. **Request integrity** — Ed25519, nonce, sequence, timestamp, replay defense.
9. **Audit and observability** — redaction, stage timings, hash continuity.
10. **Live demo** — normal, ambiguous, and malicious paths.
11. **Evaluation methodology** — labels, exact outcomes, false positives, latency.
12. **Ablation result** — what is lost with policy-only checks.
13. **Limitations** — bypass boundary, heuristic detection, dataset size, authentication.
14. **Future work** — stronger isolation, external audit anchoring, calibrated datasets, RBAC.
15. **Conclusion** — a reproducible and explainable security control, not a claim of universal safety.
