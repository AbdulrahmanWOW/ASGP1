# Progent: Securing AI Agents with Privilege Control

*Shi et al., UC Berkeley, UCSB and NUS, arXiv 2504.11703 (v3, May 2026) | One-page team summary*

## The problem

AI agents act through tools. An attacker can hide instructions in something the agent reads, like an email, and the agent may then send the whole inbox to the attacker (indirect prompt injection). LLMs can be tricked, but security needs rules that always hold.

## The solution

A gate sits between the agent and its tools. Only the tool calls the task needs are allowed; everything else is blocked (like a hotel key card that opens your room, not the whole building).

- **Write the policy:** an LLM reads the task and writes allow/forbid rules, e.g. `send_slack_msg` only when `to = alice`.
- **Check every call:** plain code checks each call against the rules. No matching rule means blocked. No LLM makes this decision.
- **Update as the agent learns:** after each tool result, the LLM can propose a new policy.
- **Judge every update:** an SMT solver decides if the update only removes permissions (applied automatically) or adds some (needs approval).
- **Result:** permissions can only shrink without approval, even if an injection fools the LLM.

## Results

| Test | Result |
|---|---|
| Attack success on AgentDojo | 39.9% → 1.0% |
| Attack success on ASB | 70.3% → 3.9% |
| Utility (AgentDojo, no attack) | 79.4% → 76.3% |
| Other defenses (AgentDojo) | 6.3% to 25.1% attack success |
| Policy updates needing approval | Only 6% |
| Real agents (LangChain, OpenAI Agents SDK, OpenHands) | About 1% attack success |
| Multi-agent (AutoGen) | More than 95% of successful attacks defended |
| Adaptive attacks | At most 4.2% attack success |

## Limits

- Cannot stop attacks that stay inside the allowed actions, or attacks that only change the text output.
- Relies on the LLM writing good policies and on users approving updates correctly.
- Text-only, no GUI agents.
- Most tests use gpt-4o, in the authors' own setup, with some tasks excluded or manually corrected.

## Relevance to ASGP

Very close to ASGP's rules layer (deterministic enforcement, LLM only proposes). ASGP adds human confirmation of the intent/scope and a semantic layer for "allowed tool, bad arguments" cases.
