# Review of the "Software Analysis & Design" draft

> Review of `ANALYSIS_AND_DESIGN.md` (team draft derived from `main`), Oct 14, 2026. The draft is a good **as-built** document; the issues below are where it diverges from the final design (`DESIGN.md`) or hides design flaws.

## What is right

- Pipeline order: session → tool registry → crypto → policy → signals → risk. Hard blocks before any scoring; NFR-02 ("a hard denial can't be overridden by an AI score") is the right invariant.
- Approval model: digest-bound, single use, expiring. One of the strongest parts of the project.
- Scope and limitations (§3.3) are honest: tamper-evident not tamper-proof, controlled 60-case dataset.
- Hard-block reason codes separated from risk thresholds.

## Problems

1. **The end user is missing as an actor.** The Developer creates and rewrites the intent anchor (UC-01/UC-02); Level 0 merges "User / Developer". ASGP's thesis is authorization by what the *user* asked for (AHI Path B). → Add an **End User** actor who confirms the drafted scope; decide who approves escalations.
2. **No authentication anywhere.** No use case, FR or diagram covers it. In Sequence 3 nothing stops the agent from calling `POST /approvals/{id}/resolve`; UC-02 lets anything widen scope mid-session. → FR for API keys/roles (agent, user, admin); the agent credential can never resolve approvals or update intent.
3. **Risk engine flaw.** `score = clamp(prev + sensitivity + signals)` with low −5 / medium +40 / high +70 / critical +100: high/critical always BLOCK (never reach a human); medium escalates on the first call; the score carries across the session (risk washing down, session poisoning up). → Per-action score, separate session signal, high-impact → ESCALATE.
4. **Decisions don't record the intent version; approvals don't record who approved.** ERD: no link from `actions`/`decisions` to `intent_anchors`; `approvals` has no `resolved_by`. Also actions→approvals/findings/audit are logical links, not FKs.
5. **Signing is optional and the diagrams hide it.** Activity diagram shows crypto on every request, but FR-12 says "for tools that require signatures" and Sequence 2 "+ signature *if agent registered*". It signs the *agent request*, not a *user-confirmed intent*.
6. **Content ingress drawn as automatic.** Level 0 "quarantined before context" — in reality the agent must call `/content/ingress`, and tool results return unscanned (Sequence 2).
7. **AI provider drawn as an external system.** The design is fully local (embedder + Ollama judge) → the model belongs inside the system boundary.
8. **BLOCK raises an exception** (crashes most agent loops). Design: return `Blocked by ASGP: <reason>` as the tool result. Approval by polling is fine for MVP; LangGraph interrupt/resume is the target.

## Missing

- A **target design** (marked "Proposed"): intent confirmation, embedding layer + local judge in the gray zone, LangGraph adapter, MCP gateway, Ollama container in deployment.
- A **threat model** section (trust boundaries, STRIDE or attacker model).
- A class or component-interface diagram if the supervisor's template expects one.

## Numbers

The 91.7% figure is real (`demo/evaluate.py`), from 60 cases (12 seeds), with a **25% legitimate false-positive rate** and median 16 ms latency measured with the **mock** provider. Present the FP rate next to the accuracy; latency will rise with real models.

## Status on this branch

Items 1–8 are addressed by the work tracked in `docs/plan/IMPLEMENTATION_PLAN.md`. The draft itself (diagrams) still needs updating to the new design.
