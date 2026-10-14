# Toward Secure LLM Agents (survey), Alignment Contracts, Task Shield — summaries

> Team-written one-page summaries.

Toward Secure LLM Agents: Threat Surfaces, Attacks, Defenses, and Evaluation Yuchen Ling, Shengcheng Yu, Zhenyu Chen & Chunrong Fang | 2026 | One-page paper summary

The problem LLM agents do more than generate text: they plan, use tools, browse websites, execute code, store memory, and coordinate with other agents. Therefore, a security failure can redirect a workflow, misuse permissions, leak sensitive data, corrupt memory, or cause harmful real-world actions. The key issue is whether untrusted information can change what an agent is allowed to do—not just what it says.

What the paper does This is a survey/review paper, not a new agent model or a single experimental algorithm. It synthesizes 247 papers published/collected from 2023 to April 27, 2026. The authors combine searches across six sources, LLM-assisted candidate expansion, citation snowballing, manual screening, and structured coding.

The framework: follow the whole agent lifecycle Input → Planning → Decision → Tool Execution → Output, with Memory/State, monitoring, and multi-agent coordination affecting several stages. The framework connects three ideas: information flow (where information comes from and where it goes), delegated authority (what permissions the agent has), and persistent state (what can be saved and reused later). An attack can enter at one stage and cause harm much later.

Main findings Finding

What it means

Prompt injection is the dominant threat (142 papers); indirect prompt injection appears in 86.

Malicious instructions hidden in web pages, retrieved text, files, or tool outputs can hijack planning and actions.

Other growing risks: data exfiltration (31), memory poisoning (24), coordination failures (14).

Sensitive data may leak through tools; poisoned memory can affect future tasks; attacks can spread between agents.

Defenses exist, but are fragmented.

Approaches include instruction hierarchy/guardrails, runtime monitoring, privilege and tool controls, containment, and memory/provenance protection. Combining them reliably remains difficult.

Evaluation is not yet standardized.

AgentDojo is the most reused benchmark in the review (30 occurrences), but tests often miss long-running, stateful, multi-agent, and deployment-specific risks.

What the authors recommend Build security around explicit trust boundaries; give agents only the privileges they need; track the source and trustworthiness of stored information; monitor actions at runtime; and evaluate agents in realistic, long-horizon scenarios using consistent metrics.

Limitations / points to mention in discussion

- The paper reviews and categorizes prior work; it does not experimentally prove one defense is best.
- Many reviewed studies are preprints (169/247, 68.42%), so evidence maturity varies.
- The authors do not report inter-rater agreement; search retrieval cannot be exactly replayed from preserved logs.
- Paper counts show research attention, not necessarily real-world prevalence or defense effectiveness.

Take-home message Secure the whole agent system, not only its prompts or final answers. The strongest risks happen when untrusted content crosses into decisions, privileged tool use, persistent memory, or communication with other agents.

The Task Shield: Enforcing Task Alignment to Defend Against Indirect Prompt Injection in LLM Agents Feiran Jia, Tong Wu, Xin Qin & Anna Squicciarini | arXiv:2412.16682v1 | December 2024 | One-page summary

The problem LLM agents use tools and external content to complete tasks. A webpage, document, or tool output may contain hidden malicious instructions (indirect prompt injection) that redirect the agent away from the user's real goal—for example, a page being summarized tells the agent to email private notes to an attacker. Existing defenses can miss subtle attacks or reduce the agent's ability to complete legitimate tasks.

The solution: Task Shield Task Shield is a test-time defense that checks whether each instruction, assistant response, and tool call contributes to the user's original task. Instead of asking only “Is this instruction harmful?”, it asks “Does this instruction help achieve the user's goal?” Misaligned tool calls are blocked, and the agent receives feedback to rethink its response.

How it works 1. Extract instructions

An LLM identifies user goals and actionable instructions from assistant messages and tool outputs.

2. Check alignment

A contribution score estimates whether each instruction supports at least one user task. A total score of 0 means misaligned.

3. Give feedback / block

The shield explains the mismatch and reminds the agent of the user's goals; misaligned tool calls are prevented from executing.

Evaluation & main results Item

What the paper reports

Benchmark / models

AgentDojo benchmark; GPT-4o and GPT-4o-mini. Tasks cover Travel, Workspace, Banking, and Slack.

Metrics

Clean Utility (CU): task success without attack; Utility under attack (U): legitimate task success during attack; Attack Success Rate (ASR): how often the attacker's goal succeeds.

GPT-4o result

Against the strongest tested “Important Instructions” attack, Task Shield achieved 69.79% utility under attack and reduced ASR to 2.07%, versus 50.08% utility and 47.69% ASR with no defense.

GPT-4o-mini result

Task Shield achieved 54.53% utility under attack and 2.23% ASR, compared with 49.92% utility and 27.19% ASR without defense.

Limitations

- Instruction extraction and alignment scoring rely on an LLM, so weaker models or adaptive attacks may fool the shield.
- Evaluation is limited by cost to one benchmark and one main model family; results are not proof of protection against every attack type.
- Task Shield focuses on whether actions support the user task; it does not solve all agent-security problems, and useful but indirect steps may be difficult to score.

Relevance to ASGP Strongly supports ASGP's Intent Alignment layer: compare every proposed tool call with the user's original goal, not just whether the call looks suspicious. It can complement Prompt Injection Detection, while ASGP's trust scoring and policy enforcement can provide additional checks. A key design question is how to handle multi-step actions that indirectly support the goal.

Take-home message Protect the user's goal, not just the wording of the prompt. Task Shield catches instructions that do not help complete the user's task—even when malicious content is hidden inside otherwise normal external data.

Alignment Contracts for Agentic Security Systems Isaac David, Marco Guarnieri & Arthur Gervais | arXiv:2605.00081 | April 2026 | One-page summary

The problem AI security agents can scan systems and test vulnerabilities, but the same actions can be harmful when aimed at an unauthorized target or when sensitive findings are sent to an attacker. Prompt injection may also redirect an agent. Ordinary guardrails do not provide a formal guarantee that every real action stays within the approved engagement.

The solution: Alignment Contracts The paper proposes a formal contract that specifies where the agent may act (scope), which effects are allowed or forbidden, resource budgets, and where data may be disclosed. A runtime monitor checks observable actions before they happen. The key idea is control what the agent actually does, rather than trusting what the model says it intends to do.

How it works 1. Define contract

The operator sets approved targets, allowed/forbidden actions, limits, and disclosure rules.

2. Observe effects

Tool actions are converted into events, such as network requests, file operations, or process execution.

3. Check & enforce

A reference monitor checks each event against the contract; forbidden or out-of-scope effects are blocked.

4. Prove the boundary

Formal definitions and Lean 4 proofs show contract compliance when the stated assumptions hold.

Main contributions / results

- Formal model: contracts describe scope, allowed/forbidden effects, budgets, and data-disclosure flows.
- Soundness theorem: monitored execution satisfies the contract even if the underlying agent behaves adversarially or is prompt-injected—provided every relevant effect is mediated and correctly observed.
- Contract composition: refinement and composition rules support modular contract design; admissibility checking is decidable once events are extracted.
- Mechanized proofs: Lean 4 is used to check the paper's core formal claims.
- Example: an injected instruction tries to send vulnerability data to an attacker-controlled domain; the request is blocked because the destination is outside the approved scope.

Limitations / what the paper does NOT prove

- The guarantee depends on the Effect Observability Assumption (EOA): all relevant effects must pass through the monitor and be represented correctly.
- Effects that bypass mediation, covert timing channels, steganographic/payload channels, and mistakes in the written policy are not fully covered.
- This is mainly a formal-methods paper, not a large empirical benchmark study; it does not report real-world false-positive, bypass-rate, or utility results.
- Full static certification that an arbitrary tool will never produce a forbidden effect is undecidable under the stated assumptions.

Relevance to ASGP This paper is especially relevant to Intent Anchor and Signing Chain: define the authorized scope and verify actions against it instead of trusting the agent's stated intent. It also supports the idea of checking tool calls at an enforcement boundary and keeping an auditable record. ASGP would still need to address its own threat model, including prompt-injection detection and trust scoring; this paper does not provide a complete ASGP system.

Take-home message Give the agent freedom inside an explicitly authorized scope, but enforce a hard boundary around its real actions. The guarantee is strong within the modeled and monitored effects—not universal protection against every possible channel or implementation flaw.
