# CXI: Context-to-Execution Integrity — team review (Paper 2)

> [UNVERIFIED] Not checked against the original PDF (arXiv:2607.06000v1). Token-type names and authorship differ between our documents. Safe to use only the conceptual role (boundary integrity vs. ASGP's intent integrity). See DESIGN.md §13.4.

Paper 2 CXI: Context-to-Execution Integrity for AI Agent Systems Authors: Igor Santos-Grueiro Venue: Universidad Internacional de La Rioja (UNIR) | arXiv:2607.06000v1 — July 2026

## Section 1: What is this paper?

CXI (Context-to-Execution Integrity) is a formal, language-theoretic framework for enforcing strict execution boundaries in AI agent systems. Authored by Igor Santos-Grueiro at UNIR and published in July 2026, it proposes a unified theoretical model that treats all possible information entering an agent's execution environment—user prompts, tool outputs, memory stores, environmental signals, and cross-agent communications—as typed tokens in a formal grammar. The core claim is that by enforcing type-based admission rules at every input surface, the system can provably prevent any token from crossing an execution boundary without authorization. CXI is a theoretical contribution backed by empirical validation on a code-agent benchmark.

## Section 2: What problem does it solve?

The fundamental problem CXI addresses is execution boundary ambiguity in AI agents: current agent frameworks have no formal definition of what information is "safe" to execute versus what is "contextual." This ambiguity enables prompt injection, goal hijacking, and privilege escalation—because the agent's execution layer does not distinguish between trusted user instructions and untrusted environmental data. Without a formal boundary model, every defense is ad hoc: it blocks known attack patterns but has no guarantee against novel variants. CXI's contribution is to replace this ad hoc pattern-matching with a grammar-based admission system that has provable guarantees—if the grammar correctly models the boundary, zero tokens cross it without authorization.

## Section 3: What is their approach?

CXI defines a five-type token vocabulary that classifies every input reaching the execution layer:

- T (Trust): Directly from the authenticated user, cleared for execution
- W (Workspace): From the agent's own memory or prior outputs, conditionally trusted
- D (Data): Environmental data retrieved by tools—explicitly NOT trusted for instruction execution
- O (Orchestration): From an orchestrating agent in a multi-agent system, partially trusted with scope limits
- X (External): From third-party sources—never trusted for execution Any token entering the execution layer must pass a six-step admission pipeline: (1) source identification, (2) type classification, (3) syntactic validation against the type grammar, (4) semantic boundary check, (5) authority verification, and (6) effect audit. If any step fails, the token is rejected. CXI also defines three invariants that a compliant implementation must satisfy: no field escapes (data-type tokens cannot appear in instruction slots), no effect escapes (D/X tokens cannot trigger side-effectful tool calls), and no invocation escapes (X tokens cannot initiate new agent calls). The framework is language-agnostic and is validated by applying it to a Python codeagent implementation.

## Section 4: What are their key results?

CXI's empirical validation produces two main outcomes:

- Zero Observed Escapes: Across all tested input surfaces and attack injection scenarios, the CXI-compliant implementation recorded zero successful execution boundary crossings. No field escape, effect escape, or invocation escape occurred in any tested scenario. This is the primary security result.
- Benchmark Performance: On a code-agent benchmark with 400 tasks, the CXI system achieved 231 safe task completions (57.75%)—completing tasks without triggering any boundary violation. The paper frames this as a meaningful utility-security trade-off, not a failure, noting that tasks with high environmental complexity require more conservative boundary enforcement. The paper also demonstrates that CXI's grammar correctly rejects 100% of injected D-type and X-type tokens attempting instruction execution across three attack categories: direct injection (malicious tool outputs), indirect

injection (data embedded in retrieved documents), and orchestration abuse (a compromised sub-agent sending malicious O-type tokens).

## Section 5: What are the limitations?

CXI's limitations stem primarily from its formal-system design philosophy:

- Type classification is not solved: The grammar defines what each type means, but the paper does not provide a complete solution for how an implementation reliably classifies tokens in ambiguous real-world cases (e.g., a tool output that contains both data and instructions mixed together). This is acknowledged as future work.
- 57.75% task completion rate: While framed as expected, this means 42.25% of tasks are blocked or incomplete. In production deployment, this utility cost may be unacceptable for many applications.
- No user intent model: CXI enforces what tokens can cross the boundary, but it has no representation of what the user originally intended to accomplish. Two completely different task goals look identical to CXI as long as both originate from authenticated T-type tokens.
- Static grammar: The token grammar is defined at design time. Adversaries who learn the grammar structure could craft inputs that are syntactically valid but semantically malicious—a known limitation of grammarbased security systems.
- Single-agent focus: Multi-agent scenarios with CXI-compliant orchestrators but non-CXI sub-agents are not fully addressed.

## Section 6: How does this paper relate to ASGP?

CXI and ASGP operate at different layers of the agent security stack and are complementary rather than competing:

- CXI answers: Can this information cross the execution boundary? (field/effect/invocation authority by token type)
- ASGP answers: Should this tool call happen right now for this user's task? (semantic intent alignment at execution time)
- A CXI-compliant agent that never allows D-type injection could still, legitimately, execute a tool call that violates the user's original intent through goal drift, context accumulation, or multi-turn manipulation— because CXI has no intent model. ASGP would catch this.
- Conversely, ASGP's semantic verifier operates on tool call arguments and intent embeddings, not on tokenlevel boundary enforcement. An ASGP-governed agent could theoretically have an injection reach its reasoning layer if boundary controls are weak—CXI prevents this. 🔗 ASGP Relevance: CXI and ASGP are architecturally complementary: CXI enforces what information can enter the execution layer (boundary integrity), while ASGP enforces whether a resulting tool call is consistent with the user's original intent (intent integrity). The strongest production system would implement both. ASGP's paper should cite CXI to distinguish the two contributions clearly and avoid conflation.
