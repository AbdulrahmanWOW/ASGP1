# Limitations and honest security claims

ASGP is a graduation-project prototype, not a universal agent sandbox.

- It only governs tool calls routed through its SDK adapters or MCP gateway. Direct code execution, an unwrapped tool, or a custom LangGraph node that calls tools itself is outside its control. The MCP gateway is bypass-resistant only if upstream servers are reachable solely through it.
- Prompt-injection detection is deterministic and pattern-based. It can miss paraphrases and can flag benign quotations.
- The default intent-alignment provider is a local lexical mock. The hashing and sentence-transformers embedding providers use **untuned** calibration thresholds; they have not been evaluated on the dataset yet.
- The local LLM judge (Ollama) has not been evaluated; no accuracy or latency numbers are claimed for it. It only runs in the gray zone and fails closed to ESCALATE.
- Risk thresholds and sensitivity weights are design choices validated on the included lab, not calibrated on real incident prevalence.
- Session risk is simple accumulated state; it is not user identity, reputation, or forensic attribution.
- Signatures prove request origin and integrity, not that an action is safe.
- Authentication is static API keys with three roles (admin, user, agent). There are no individual user accounts, key rotation endpoint or SSO; the dashboard stores its key in the browser's localStorage.
- Intent tokens are bearer tokens bound to one session and anchor version. If `ASGP_INTENT_SIGNING_KEY` is not set, an ephemeral key is generated and tokens die with the process.
- The rule-based scope drafter is a heuristic; the human must read the drafted scope (including any folders or destinations the agent proposed) before confirming.
- Fail-closed defaults cost usability: a parameter named like a destination (`email`, `to`, `url`, …) is blocked when the session has no allowed destinations, even when it is only a lookup key. Tools can declare `destination_parameters` / `path_parameters` explicitly.
- PostgreSQL, local CORS, and Docker defaults are for a private demonstration environment.
- Hash chaining makes detectable changes evident where continuity is available; it does not provide an external immutable timestamp or prevent database deletion.
- The 19-seed (95-case) dataset is too small to support broad statistical claims, and seven seeds were written after the branch changes to exercise them. Reported rates apply only to the included labeled scenarios.
- Tool results are scanned only when result scanning is enabled in an adapter or the gateway; scanning uses the same pattern-based detector.

These constraints are part of the final result and should be stated during the defense.
