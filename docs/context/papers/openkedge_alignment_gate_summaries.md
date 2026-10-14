# OpenKedge and The Alignment Gate — team summaries

## OpenKedge: Governing Agentic Mutation

*He & Yu, OpenKedge.io, arXiv 2604.08601 (April 2026)*

### The problem

If an AI agent has permission to do something, the system just does it. But "allowed" does not mean "safe": an agent might delete a database that looks unused while other services still depend on it.

### The solution

Agents no longer call APIs directly. They send an **intent**, and the system decides if it is safe before anything happens:

- **Collect context:** check the real system state (dependencies, traffic), not just what the agent says.
- **Check policy:** Cedar rules give Approve, Reject, or Escalate to a human.
- **Make a contract:** if approved, a contract fixes the exact action, resource and time limit.
- **Give a temporary key:** a short-lived credential (AWS STS) works only for that contract.
- **Record everything:** the IEEC is a linked log of intent, context, decision, contract and result.

Conflicts between actors are ranked by authority (humans first), trust score and recency; a tie goes to a human.

### Results (all simulated)

| Test | Result |
|---|---|
| 10,000 concurrent proposals | Same contracts, logs and final state on every run |
| Policy decision time | 11 ms average |
| State computation (p99) | Under 30 ms |
| Throughput | Up to 3,200 mutations/s |
| Safety cases | Deleting a server with dependencies and cutting capacity at peak traffic were both blocked |

### Limits

- No baseline comparison, no false-positive rate.
- Policies are hand-written; prompt injection is out of scope (it only limits damage).
- The policy engine and log must be trusted; the "theorem" is not formally proven; the authors run the company.

### Relevance to ASGP

Similar intent → decision → audit flow, but for infrastructure changes, using credential scoping instead of semantic checks.

## The Alignment Gate: Intent and Instruction Guardrails for Agentic AI

*Borigi et al., Missouri S&T and Aiceberg, ESANN 2026*

### The problem

Agents turn a request into steps and run them with tools. There is a gap between what the agent **can** do and what it **should** do: hallucination, goal drift, unauthorized actions.

### The solution

A gate that checks every planned step against the user's intent **before** it runs, then says Execute or Block.

Offline setup:

- A taxonomy of **250 intent types** and **217 instruction types**.
- ChatGPT Thinking scores each pair 0–100 ("how likely is this step to come from this intent?").
- Per-intent threshold via the **min-median rule** (smaller of mean and median).

At run time, small language models label the prompt and each step; a step runs only if its score is above the intent's threshold.

### Results

| Item | Result |
|---|---|
| Taxonomy size | 250 intents, 217 instructions |
| Example intent UPDATE_INFORMATION | Threshold 62.48 |
| Example steps | CHECK_FEASIBILITY (91.87) runs; LOG_USER_ACTIVITY (12.01) blocked |
| Threshold spread | 188 of 250 intents between 10 and 15 |

No accuracy/precision/recall or baseline comparison — a feasibility study.

### Limits

- No real evaluation of catches vs. false blocks.
- Scores come from ChatGPT (probabilistic); "deterministic" only at run time.
- Assumes SLM labels are always right; checks each step alone.
- Low thresholds (10–15) mean the gate may be very permissive.

### Relevance to ASGP

An alternative to ASGP's embedding layer, and a useful contrast for threshold-setting.
