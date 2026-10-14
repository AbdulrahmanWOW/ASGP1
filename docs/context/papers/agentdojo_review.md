# AgentDojo — team review (Paper 1)

> Team-written review. Known issues (see docs/context/DESIGN.md §15): the GPT-4o figures 74.69% / 72.32% probably do not match the paper (47.69% ASR is the figure Task Shield reports); the 'beat 7.5% ASR' target is outdated (Task Shield 2.07%, Progent 1.0%). Verify numbers against arXiv:2406.13352 before citing.

Paper 1 AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents Authors: Edoardo Debenedetti, Jie Zhang, Mislav Balunović, Luca Beurer-Kellner, Marc Fischer, Florian Tramèr Venue: ETH Zurich & Invariant Labs | NeurIPS 2024 — Datasets and Benchmarks Track

## Section 1: What is this paper?

AgentDojo is a publicly released, dynamic benchmarking framework built specifically to evaluate prompt injection attacks and the defenses designed to counter them in the context of LLM-based agentic systems. It was presented at the NeurIPS 2024 Datasets and Benchmarks Track and developed jointly by ETH Zurich and Invariant Labs. The benchmark is designed to be extensible: new tasks, new pipelines, new attack strategies, and new defense mechanisms can be added without breaking existing evaluations. It provides a unified, reproducible standard for measuring how vulnerable AI agents are when adversaries embed malicious instructions in tool outputs—content the agent retrieves from the environment during execution.

## Section 2: What problem does it solve?

Before AgentDojo, there was no standardized way to evaluate how AI agents respond to prompt injection attacks in realistic multi-step agentic scenarios. Existing evaluations were either narrow (single-turn), synthetic (not drawn from real workflows), or non-reproducible. Researchers and practitioners had no shared ground truth for comparing defenses, and vendors had no principled way to claim safety. This benchmark fills that gap by providing:

- A rigorous, reproducible attack/defense evaluation environment
- Realistic task suites drawn from four domains: email, calendar, banking, and travel booking
- A dual-metric system that prevents defense strategies from achieving safety by simply refusing all actions (measuring both benign utility and security)
- A separation between the attacker goal and the user goal so that targeted attack success rate (ASR) can be measured with precision

## Section 3: What is their approach?

AgentDojo defines 97 user tasks spread across four agentic environments—each with a set of available tools (17– 28 per environment)—and pairs each task with one or more adversarial injection scenarios, totaling 629 security test cases. The evaluation methodology uses three metrics:

- Benign Utility Rate: fraction of tasks completed correctly when no attack is present
- Utility Under Attack: fraction of tasks still completed when an attack is injected
- Targeted Attack Success Rate (ASR): fraction of runs where the adversarial goal was also achieved Each task specifies a ground-truth sequence of tool calls; the framework checks whether the agent executed the correct tools with correct arguments. Attacks are injected as malicious instructions embedded in tool return values (e.g., an email body, a web search result). The framework supports pluggable agents and defenses through a clean Python API, and comes with five built-in defense strategies: tool filter, prompt injection detection, spotlighting (data/instruction delimiter), think-then-act (CoT reasoning), and transforming user tasks into more explicit internal instructions.

## Section 4: What are their key results?

AgentDojo produces three major empirical findings of lasting significance:

- Inverse Scaling Law: More capable models are paradoxically easier to attack. GPT-4o achieves the highest benign utility (74.69%) but also the highest ASR (72.32%). Claude 3.5 Sonnet achieves 78.22% benign utility and is among the most capable—yet also highly susceptible. This directly challenges the assumption that capability improvements improve security.
- Best Defense — Tool Filter: Restricting tool calls to only those semantically necessary for the current task reduces ASR from over 70% to 7.5% on average, making it the most effective defense tested. This comes at a modest cost to benign utility.

- No Defense is Complete: Even the tool filter still allows 7.5% of targeted attacks to succeed. The combination of prompt injection detection + spotlighting + CoT provides broader but still incomplete protection. No defense reaches zero ASR across all environments. A secondary finding is that attack difficulty scales with the number of tools available: environments with more tools provide more attack surface and enable more complex injection sequences.

## Section 5: What are the limitations?

AgentDojo has several acknowledged boundaries:

- Static attack library: The adversarial injection prompts are hand-crafted. The framework does not include automated adversarial generation (e.g., red-teaming LLMs), which may underestimate future attack sophistication.
- Text-only modality: All attacks and tool outputs are textual. Multimodal agentic systems (agents that also process images, audio, or code execution results) are not evaluated.
- Closed-world task set: All 97 tasks are pre-defined by the authors. Real-world deployments involve unbounded task diversity, which the benchmark cannot fully capture.
- Black-box evaluation only: The framework measures behavioral outcomes (did the tool get called?) but not internal reasoning traces or attention patterns.
- No runtime intent verification: AgentDojo evaluates attacks against agent behavior, but does not model or test systems that verify the agent's intent before execution—leaving that research direction unexplored.

## Section 6: How does this paper relate to ASGP?

AgentDojo is the primary benchmark for validating ASGP's security claims. Three connections are direct and critical:

- ASGP's intent verification mechanism (signed intent anchor + semantic scoring) directly targets the injection vectors that AgentDojo operationalizes. If an injected instruction causes an agent to request a tool call inconsistent with the original user intent, ASGP's verifier catches it before execution—regardless of whether the agent itself was deceived.
- The inverse scaling law result motivates ASGP's architecture. Since more capable models are more susceptible to injection, ASGP cannot rely on model capability as a safety guarantee. An external governance layer is necessary—exactly what ASGP provides.
- The tool filter defense (best existing defense at 7.5% ASR) operates on tool availability, not intent alignment. ASGP's approach is orthogonal: it does not restrict which tools are available, but verifies whether the specific invocation is consistent with the original signed intent. These approaches are complementary and could be combined. 🔗 ASGP Relevance: AgentDojo provides ASGP's evaluation harness. ASGP's security effectiveness should be measured on AgentDojo benchmarks, targeting sub-7.5% ASR (better than the best known defense) while maintaining comparable benign utility. This is the primary experimental claim ASGP should substantiate.
