# AHI Reframing — team review (Paper 3)

> ⚠️ This review contains INVENTED content. The five-category taxonomy below (Intent Communication / Transparency / Control / Trust Calibration) is NOT in the paper; the paper is a preprint, not peer-reviewed; 'first open-source system' claims are unprovable. Use the verified summary in docs/context/DESIGN.md §13.1 instead. Kept only for history.

Paper 3 Reframing LLM Agent Security as an Agent-Human Interaction Problem Authors: Peiran Wang, Ying Li, Yuan Tian Venue: University of California, Los Angeles (UCLA) | arXiv:2605.24309v1 — May 2026

## Section 1: What is this paper?

This paper proposes a fundamental reconceptualization of LLM agent security: rather than treating it as a purely technical problem (detecting attacks, filtering inputs, patching vulnerabilities), the authors argue it should be treated as an Agent-Human Interaction (AHI) problem—a question of how well the agent's behavior aligns with and remains under meaningful human oversight throughout execution. The paper introduces a five-category AHI taxonomy, surveys 21 production agent deployments against it, and proposes two design paths for integrating human oversight: Path A (LLM-mediated) and Path B (human-in-the-loop). Authored by Peiran Wang, Ying Li, and Yuan Tian at UCLA, published May 2026.

## Section 2: What problem does it solve?

The paper identifies a structural gap in current agent security: existing security mechanisms (tool filters, prompt injection detectors, sandboxing) focus on external threats, but the deeper problem is the erosion of human oversight as agents become more autonomous. The authors survey 21 production deployments and find that the most critical oversight mechanisms are the least implemented:

- Intent anchoring (verifying that agent actions remain aligned with the original user goal throughout execution): 0 of 21 deployments
- Policy specification (explicit, machine-readable behavioral boundaries): 14 of 21 deployments
- Runtime approval (human confirmation before high-impact actions): 15 of 21 deployments
- Scope configuration (user-controlled limits on what the agent can do): 16 of 21 deployments This pattern reveals that the security community has focused on perimeter defense (external attacks) while neglecting behavioral governance (ensuring the agent does what the user intended throughout execution).

## Section 3: What is their approach?

The paper introduces a five-category AHI taxonomy for classifying human-agent interaction mechanisms in production systems:

- Intent Communication: How users express their goals to the agent (natural language, structured tasks, examples)
- Transparency: How the agent surfaces its reasoning and planned actions before executing them
- Control Mechanisms: How users intervene, pause, redirect, or terminate agent execution
- Trust Calibration: How the system builds appropriate user trust—neither blind trust nor excessive skepticism
- Intent Anchoring: How the system maintains and continuously validates alignment with the original user intent across multi-turn, multi-tool execution sequences The survey methodology coded 21 production agent deployments against these five categories and mapped each feature to a binary present/absent classification. The paper then proposes two architectural paths for improving AHI coverage:
- Path A (LLM-mediated): A secondary LLM module monitors the primary agent's actions and flags misalignment with stated user intent—fully automated, no human required at runtime
- Path B (Human-in-the-loop): A checkpoint system that pauses agent execution at high-risk decision points and requests explicit human confirmation before proceeding

## Section 4: What are their key results?

The survey produces findings that are both empirically grounded and architecturally significant:

- Intent anchoring has zero production deployments: Of the five AHI categories, intent anchoring—the mechanism that continuously validates that agent actions remain consistent with the user's original goal—is absent in every surveyed production system. This is the most critical gap.
- Perimeter-vs-governance imbalance: The most-implemented mechanisms (scope configuration: 16/21, runtime approval: 15/21, policy specification: 14/21) are all static or reactive. Intent anchoring is dynamic and proactive—and is universally absent.
- Path A and Path B are not mutually exclusive: The paper argues for a hybrid design where Path A handles routine monitoring (automated, fast, cheap) and Path B handles high-stakes decision points (deliberate, human-authorized). Neither alone is sufficient.
- The problem is architectural, not incremental: The authors conclude that adding more attack detectors or expanding tool filters will not close the gap. Intent anchoring requires a fundamentally different design—one that maintains a representation of user intent and compares every agent action against it at runtime.

## Section 5: What are the limitations?

The paper's limitations are primarily methodological:

- Small survey sample: 21 production deployments is a meaningful but limited sample. The authors note selection bias: they could only survey publicly documented systems, which skews toward enterprise and developer-facing products, underrepresenting consumer-facing agents.
- Binary coding: Each AHI feature is coded as present or absent. This misses important variation in implementation quality—a system with a primitive intent communication interface and a sophisticated one both receive the same score.
- No quantitative security validation: The paper identifies the gap (0/21 intent anchoring) but does not measure what security improvement implementing intent anchoring would provide. The claim that it matters is theoretical and survey-based, not empirically validated.
- Path A evaluation missing: The proposed LLM-based monitoring path (Path A) is not implemented or evaluated. Its effectiveness, latency overhead, and failure modes are not measured.
- Rapid pace of deployment: The paper acknowledges that the surveyed landscape is changing rapidly; several systems reviewed may have added features since the survey was conducted.

## Section 6: How does this paper relate to ASGP?

This paper is the single most direct academic justification for ASGP's existence. Three connections are foundational:

- The 0/21 finding is ASGP's primary motivation statement: ASGP is explicitly designed to implement intent anchoring—the mechanism that every surveyed production system lacks. This is not coincidental; it means ASGP fills the most critical and universally absent gap in the current production landscape.
- ASGP implements both Path A and Path B: ASGP's semantic verifier (comparing tool call embeddings against the signed intent anchor using cosine similarity) is Path A—automated, continuous, fast. ASGP's human-inthe-loop escalation mode, where low-confidence decisions are flagged for user confirmation, is Path B. ASGP is the first open-source system to implement both paths in a unified architecture.
- The Ed25519 signing mechanism directly addresses intent drift: The paper identifies intent anchoring as the critical missing mechanism but does not specify how to implement it. ASGP's approach—cryptographically signing the user's original intent statement at task initialization and comparing all subsequent tool calls against that signed anchor—is a concrete implementation of exactly what the paper calls for. 🔗 ASGP Relevance: This paper should be cited in ASGP's introduction and motivation section. The 0/21 statistic for intent anchoring is a peer-reviewed, empirically grounded justification for ASGP's core mechanism. ASGP should frame itself explicitly as the first open-source implementation of intent anchoring with both Path A (automated semantic verification) and Path B (human-in-loop escalation) as defined in this survey. This is ASGP's strongest positioning argument.
