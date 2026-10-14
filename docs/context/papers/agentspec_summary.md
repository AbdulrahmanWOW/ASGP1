# AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents

*Wang, Poskitt & Sun, Singapore Management University, ICSE 2026 (arXiv 2503.18666 v3) | One-page team summary*

## The problem

LLM agents act on their own and can take unsafe actions. The same action can be fine in one place and unsafe in another (e.g. adjusting medication doses in a research lab vs. a hospital). ToolEmu checks risk before execution but cannot enforce anything; GuardAgent relies on an LLM and needs manual work per agent.

## The solution

A small rule language that lets each organization write its own safety rules, checked while the agent runs (a rulebook at a checkpoint).

- **Write a rule:** each rule has a trigger (when it applies), a check (the condition) and an enforcement (what happens). Example: before Transfer, if the recipient is not family, ask the user.
- **Intercept:** the framework hooks into the agent (built on LangChain) and sees each planned action before it runs.
- **Check:** Python functions return True/False. The rule fires when the trigger happens and all checks are True.
- **Enforce:** stop the agent, ask the user, let the LLM re-examine its plan, or run a corrective action.
- **Rules can come from people or an LLM:** LLM-written rules are meant to be reviewed by the user; enforcement happens outside the LLM.

## Results

| Test | Result |
|---|---|
| Code agent (RedCode-Exec) | Over 90% of unsafe executions intercepted |
| Embodied agent (SafeAgentBench) | 0% hazardous actions in 10 categories; safe tasks 58.62% → 54.26% |
| Autonomous vehicles (FixDrive) | 100% compliance in the tested scenarios |
| LLM-written rules, code agent | 87.26% of risky code caught |
| LLM-written rules, embodied agent | Precision 95.56%, recall 70.96% |
| LLM-written rules, vehicles | 5 of 8 scenarios prevented |
| Reuse | 25 rules covered 750 code scenarios |
| Overhead | About 1–3 ms per check, vs 25.4 s (code) and 9.82 s (embodied) average runtime |

## Limits

- Checks single points in time; cannot predict whether a sequence of actions leads somewhere unsafe.
- Rules must be written by hand or by an LLM (which overfits or makes rules too rigid).
- Strongest numbers use hand-written rules built for the same datasets; some outcomes judged manually.
- Built and tested on LangChain; evaluated on safety hazards rather than against attackers.

## Relevance to ASGP

Comparable to ASGP's rules layer and to the LangChain middleware integration. AgentSpec has no intent model; ASGP anchors every check to a confirmed, signed intent.
