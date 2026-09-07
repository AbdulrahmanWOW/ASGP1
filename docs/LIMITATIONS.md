# Limitations and honest security claims

ASGP is a graduation-project prototype, not a universal agent sandbox.

- It only governs tool calls routed through its SDK/gateway. Direct code execution or an unwrapped tool is outside its control.
- Prompt-injection detection is deterministic and pattern-based. It can miss paraphrases and can flag benign quotations.
- The default intent-alignment provider is a local lexical mock, not a production semantic model.
- Risk thresholds and sensitivity weights are design choices validated on the included lab, not calibrated on real incident prevalence.
- Session risk is simple accumulated state; it is not user identity, reputation, or forensic attribution.
- Signatures prove request origin and integrity, not that an action is safe.
- The dashboard has no production authentication or role-based access control.
- PostgreSQL, local CORS, and Docker defaults are for a private demonstration environment.
- Hash chaining makes detectable changes evident where continuity is available; it does not provide an external immutable timestamp or prevent database deletion.
- The twelve-case dataset is too small to support broad statistical claims. Reported rates apply only to the included labeled scenarios.

These constraints are part of the final result and should be stated during the defense.
