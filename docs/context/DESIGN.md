# ASGP — Agent Security Governance Platform
## Design source of truth (final design + literature + known errors)

> **Single source of truth for the design.** Merged from the team's design chats (Oct 13–14, 2026). Where older documents disagreed, the newer design won. Older documents (the three paper reviews, the MCP comparative report) contain known errors; they're listed in §15. Implementation status of this branch lives in `docs/plan/IMPLEMENTATION_PLAN.md`.
>
> Read the whole file before doing anything. Facts marked **[UNVERIFIED]** haven't been checked against the original source. Don't repeat them in academic writing until they've been checked.

*Last updated: October 14, 2026*

---

## 1. What ASGP is

**Agent Security Governance Platform.** Graduation project by Abdulrahman Alseady (Alamein International University, B.Sc. Computer Science, expected 2027). Teammate **Hazem Oraby** is the main coder.

ASGP is a **middleware security layer that intercepts AI agent tool calls before they execute**. It checks each call against a **human-confirmed, Ed25519-signed user intent** and enforces one of three verdicts: **allow / block / escalate to a human**. Every decision goes to an audit log. Everything runs locally: no external AI APIs.

**Core thesis:** an agent's tool call should be authorized by what the user actually asked for, not just be technically possible given the agent's permissions.

**Key fact behind the design:** the LLM provider never runs tools. It only *proposes* a tool call, and the agent's own code executes it. That's why ASGP sits at tool execution.

---

## 2. Repositories

| Repo | Owner | Role |
|---|---|---|
| `HazemOraby/ASGP` | Hazem | **Primary repo** |
| `AbdulrahmanWOW/ASGP` | Abdulrahman | Personal fork |
| `AbdulrahmanWOW/ASGP1` | Abdulrahman | Public copy. **Branch `new-test-branch-with-newer-sdks-and-proxy` holds the new pipeline, adapters and MCP gateway** |

Always confirm which repo is active before any git operation.

---

## 3. Status before this branch (verified against the code, Oct 14 2026)

| Component | Status in `main` |
|---|---|
| Pipeline | Additive risk score: session → tool registry → agent-request signature → policy → lexical alignment → injection regex → behavior → risk (ALLOW < 40, ESCALATE 40–69, BLOCK ≥ 70) |
| Ed25519 signing | **Agent request** signing (nonce, timestamp, expiry, sequence, intent-anchor hash). Optional per tool (`requires_signature`). Not a user-confirmed intent token |
| Interception | `@protect_tool` decorator (manual per-tool wrapping). No framework hooks |
| Human escalation | Exists: approval bound to the action digest, single use, expires (TTL) |
| Replay protection | Exists for signed agent requests (nonce + sequence + expiry) |
| Hash-chained audit | Exists; chain head in the same DB → tamper-evident, not tamper-proof |
| API authentication | **None** — any caller (including the agent) can resolve approvals, update intent, register tools |
| Boundaries | Only parameters named `path`, `recipient`, `destination`; **empty allow-lists skip the check (fail-open)** |
| Risk engine | Session-cumulative; low −5 (risk washing); medium +40 (escalate); **high +70 / critical +100 → always BLOCK, never reach a human** |
| Semantic scorer | `MockProvider` (lexical, tool name only, ignores arguments) |
| Local LLM judge | Not built |
| Intent confirmation | Not built (developer sets scope directly) |
| Content ingress | Endpoint exists; agent must call it; tool results not scanned |
| MCP gateway | Not built |
| Evaluation | `python -m demo.evaluate`: 12 seeds × 5 variants = 60 cases; 91.7% exact accuracy, 100% malicious detection, **25% legitimate false-positive rate**, median 16 ms (mock provider) |

> The 91.7% figure **is a real, reproducible result**, but only from the controlled 60-case evaluation (12 team-written seeds, keyword-based detectors). Never generalize it; always report the 25% false-positive rate next to it.

What this branch changes is tracked in `docs/plan/IMPLEMENTATION_PLAN.md`.

---|---|
| Architecture | Finalized (hybrid pipeline, §6) |
| Ed25519 intent signing | Implemented |
| Middleware intercept | Implemented (interception point unconfirmed). **Check:** does Hazem's code intercept at tool execution, or does it expect manual calls? If manual, the adapters (§9–10) are the missing piece |
| Policy engine (rules) | Implemented |
| Semantic scorer | `MockProvider` only (lexical). Not a real model |
| Local LLM judge | Designed (§7), not built |
| Intent confirmation (draft scope → user OK → sign) | Designed, not built |
| Human escalation | **Check whether it exists in the code**; don't claim it until confirmed |
| Per-tool risk levels | Not built |
| Content ingress scanner | API endpoint exists, **not automatic** (must be called manually) |
| MCP gateway | Designed, not built |
| Chain of trust (multi-agent signing) | Designed, not built. Optional |
| Evaluation dataset | ~60 scenarios. Expand to 50–100+ |
| **Results** | **None yet** |

> ⚠️ "91.7% accuracy on 60 cases" from earlier chats is **not a real result**. It was illustrative. Never present it as project output.

External gap analysis (friend's review): ~88% MVP, ~57% full spec.

---

## 4. Threat model and scope

- **Protects against:** a **manipulated agent**, through indirect prompt injection or excessive agency.
- **Does not protect against:** a malicious developer, jailbreaks of the model itself, or hallucination as such.
  - Hallucination is a *belief* problem inside the model. ASGP works on the *action* layer. It may catch the *consequences* of hallucination, but it doesn't fix hallucination.
- **Out of scope (state explicitly in the report):**
  - Provider-hosted tools (e.g. OpenAI's built-in web search, Claude's server-side code execution). They run on the provider's servers and can't be intercepted.
  - Closed agents you can't modify whose tools are built-in rather than MCP.
  - Attacks that stay entirely inside the allowed scope, and attacks that only change the agent's text output (a shared limit with Progent and others).

---

## 5. Integration modes: SDK vs. MCP gateway

**The deciding question is whether you own the agent code and where the tools live.** It's *not* about which LLM is used.

**"Do I own the code?" test**
- *Yes:* you wrote the script that builds the agent (`create_agent`, a LangGraph graph, a loop around an LLM API), you can see `tools=[...]`, and you deploy it. You can `import asgp`.
- *No:* it's an installed or hosted product (Claude Desktop, Cursor, Copilot, ChatGPT), or your only control is configuration (e.g. adding an MCP server in a config file).

**SDK (in-process):** wraps tool execution inside the agent's process. Works with any model and any framework, as long as you own the code. Weakness: **bypass**. An unwrapped tool or a direct API call is never seen.

**Proxy = MCP gateway (the only proxy that works):**
- A proxy between the agent and the **LLM API** was **rejected**. It only sees *proposed* calls while the tool still runs locally. To act, it would have to rewrite model responses, which is fragile and breaks streaming.
- A proxy in front of **MCP servers** is strong. It sees the real invocation regardless of framework. The signed intent travels in a header or session.

**Final decision table**

| Situation | Use |
|---|---|
| Don't own code + MCP tools (Claude Desktop, Cursor) | **Gateway** (only option) |
| Don't own code + built-in/non-MCP tools | **Out of scope** |
| Own code + local Python function tools | **SDK** (only option) |
| Own code + MCP tools + a first-class ASGP adapter exists (LangChain/LangGraph) | **SDK** (richer context) |
| Own code + MCP tools + no adapter (CrewAI, LlamaIndex, …) | **Gateway** (zero code) |

| | SDK | Gateway |
|---|---|---|
| Sees agent history | Yes, the full task | Only the calls passing through |
| Intent transport | Easy (in memory) | Harder (session/header) |
| Human pause | True pause/resume (LangGraph) | Blocking wait + timeout |
| Code changes | A few lines | None (config) |
| Bypass resistance | Weaker | **Stronger**, if tool servers accept only gateway traffic |

**Outer architecture: both entry points share one core engine**
```
[Your agent code: LangGraph, LangChain, raw API]   [Third-party agent: Claude Desktop, Cursor]
              │                                                 │
     [SDK adapter: wraps tool execution]        [MCP gateway: in front of MCP servers]
              └───────────────────┬─────────────────────────────┘
                     [ASGP CORE ENGINE (one shared engine)]
                                  │
             [Real tools: run only if allowed]   [Audit log: every decision]
```
Adapters are thin, so supporting a new framework only takes a small adapter.

---

## 6. FINAL hybrid pipeline (inside the core engine)

**Path B (human) at both ends, Path A (automated) in the middle.** This follows the AHI paper's proposed hybrid (§13.1).

0. **Setup (once):** the user or admin writes policies and tool scopes. *(Path B)*
1. **Confirm and sign intent** (once per task, before the agent runs). *(Path B)*
   - Example: "Summarize my last 5 emails" → ASGP drafts the scope "read emails: yes; send/delete: no" → the user approves → the scope is signed with Ed25519.
   - This is the paper's "proactive ambiguity detection": the anchor becomes something the human expressed, not something the system inferred.
2. **The agent proposes a tool call → checks run top-down, and most calls exit early:**
   1. **Rules check** (deterministic, Path B): user policies, scope/allowlists, argument constraints, signature verification. **A hard block can't be overridden.** A tool not in the signed scope is blocked immediately.
   2. **Embedding score** (lightweight, Path A): local sentence-transformers. High → allow; low → block; middle → gray zone.
   3. **Local LLM judge** (full, Path A): **gray zone only** (§7).
   4. **Human approval** (Path B). Two triggers:
      - **(a) Low confidence:** still unresolved after the judge.
      - **(b) High impact:** payments, deletes and external sends **always** need confirmation, even if the score looks fine (risk-adaptive approval).
3. **Outcome:** run the tool, or block it with a readable reason. Everything is written to the audit log.

**Safety rules**
- The judge **never sees untrusted content** (email, web or file bodies).
- Automated layers can only make a decision **stricter**. The LLM never overrides a rules block and never approves a high-risk action alone.
- **Fail closed:** a crash, timeout or garbled output becomes block or escalate, never allow.
- **Persistence limit:** count blocks per task. Past a threshold, terminate the run, since repeated blocks suggest an injection.

**How the pipeline answers the AHI paper's concerns**

| Paper's concern | ASGP answer |
|---|---|
| Prompts are imprecise | Confirm intent before signing |
| LLM judges can be injected | The judge sees only the signed intent + the structured tool call |
| Path B is more fundamental | User policies and scopes form the rules layer; nothing automated overrides them |
| Approval fatigue | Risk-adaptive approval (only low-confidence or high-impact calls) |
| Unexplained blocks erode trust | Every block has a readable reason, plus the audit log |

---

## 7. Local LLM judge spec

- **One narrow question:** "Does this specific tool call serve the confirmed intent?"
- **Input:** the signed intent/scope, the tool name + description, the arguments, and the earlier tool calls in this task (names and arguments only). **Never** email, web or file content.
- **Output:** strict JSON `{"verdict": "allow" | "block" | "escalate", "reason": "..."}`. Anything that isn't valid JSON → escalate.
- **Typical decisions:**
  - Is this recipient or URL consistent with the task?
  - Does deleting `/project/build/tmp` fit "clean the build"?
  - Does a sequence of calls look like exfiltration (read contacts → post to an external URL)?
- **Limits:** it can't override a rules block and can't approve a high-risk action alone.
- **Assistive jobs (AHI agenda item D3: LLMs assist, they don't decide):** draft the scope for confirmation; write the human-readable block reasons.
- **Weak spot:** arguments can carry injected text. Mitigations: mark arguments as data, truncate long arguments, accept only valid JSON.
- **Runtime:** local (e.g. Qwen or Llama via Ollama). Together with the embedding layer, this **replaces `MockProvider`** and keeps the no-external-AI-API promise.

---

## 8. Latency estimates (ballpark; measure on our hardware for the report)

| Layer | Time |
|---|---|
| Rules + signature | < 1 ms |
| Embedding (MiniLM-class, intent embedding cached) | ~5–20 ms on CPU |
| Local LLM judge (1–3B) | ~0.3–1 s on GPU / 1–5 s on CPU |
| Human | seconds to minutes |

Baseline: each agent step already waits 1–10 s for its own LLM.

| Case | Added time |
|---|---|
| Safe action | ~10–30 ms (unnoticeable) |
| Gray zone | +0.3–3 s |
| Intent confirmation | A few seconds of human time, once per task |
| Obvious attack (out-of-scope tool) | Blocked in < 1 ms, faster than a safe call |
| Subtle attack (allowed tool, bad arguments, e.g. `send_email` to an attacker when replying is allowed) | Judge blocks in ~0.3–3 s, or escalates if high-risk |

---

## 9. SDK structure

**Four parts**
- **Interceptor (adapter):** a thin gate in front of tool execution. It catches every call but doesn't judge.
- **Core engine:** all the security logic, identical for every framework.
- **Signed intent:** attached to the run somewhere the model can't edit, and fixed for the run.
- **Human approval:** used only on "escalate".

**Package layout:** `asgp/core/` (engine), `asgp/intent.py` (draft/confirm/sign), `asgp/adapters/langchain.py`, `asgp/adapters/langgraph.py`.

**Interceptor, per tool call**
1. **Catch:** gets the tool name, arguments and call ID.
2. **Gather context:** the tool call, signed intent, task history and tool risk level.
3. **Ask the engine:** gets the verdict, the reason and which layer decided.
4. **Act:**
   - **Allow:** the real tool runs and its result is returned unchanged.
   - **Block:** the tool never runs. The model receives "Blocked by ASGP: \<reason\>" as the tool result and continues (no crash).
   - **Escalate:** the whole agent pauses and saves progress. The user approves or rejects, and the agent resumes at the same point.
5. **Record:** an audit entry with the attempt, verdict, reason, layer and latency.

**Special cases**
- **Fail closed** on any engine error or timeout.
- **Resume re-runs the interceptor** (verified in testing). Cache decisions by call ID, log once, and never run the judge twice.
- **Parallel tool calls:** intercept each one separately and group the approvals into one screen.
- **Repeated blocks:** count them per task and stop the run past a limit.
- **Unknown tools** (not in the signed scope): block immediately, before scoring.

**What the interceptor does NOT do:** judge; change the agent's reasoning or prompts; **edit arguments** (it allows them as-is or refuses); read untrusted content.

**One-sentence report version:**
> The interceptor is a thin, framework-specific gate in front of tool execution that guarantees every tool call is evaluated against the signed intent, enforces the engine's verdict (allow, block, or pause for human approval), fails closed on errors, and records every decision.

---

## 10. Framework integration

### 10.1 LangChain / LangGraph (verified by running tests on langchain 1.4.5, langgraph 1.2.15)

- **One function serves both frameworks.** Both use the interceptor signature `(request, handler)`:
  - `request.tool_call` = `{name, args, id}`, plus `request.tool`, `request.state` and `request.runtime`.
  - `handler(request)` runs the real tool.
- **LangChain:**
  - Subclass `AgentMiddleware` and implement `wrap_tool_call` (async: `awrap_tool_call`).
  - Pass it via `create_agent(model, tools, middleware=[...], context_schema=Ctx, checkpointer=...)`.
  - Other hooks: `before_agent` (reject runs without a valid signed intent), `after_agent` (finalize the audit), `before_model`, `after_model`, `wrap_model_call`.
- **LangGraph:** `ToolNode(tools, wrap_tool_call=asgp_wrap)`. Custom nodes that call tools directly **bypass ASGP**. Consider an `asgp.audit_graph()` check that flags them.
- **Intent transport:** runtime context. Pass it with `invoke(..., context=Ctx(intent=...))` and read it via `request.runtime.context`.
  - Context is fixed per run and the model can't touch it. State and messages *can* be influenced.
  - The engine still verifies the signature on every call.
- **Block:** return `ToolMessage(content="Blocked by ASGP: ...", tool_call_id=id, status="error")`.
- **Human pause:**
  - Call `interrupt({...})` inside the interceptor. This **requires a checkpointer**.
  - The result contains `__interrupt__`. Resume with `invoke(Command(resume=answer), config)`.
  - On resume, the interceptor runs again from the top, so cache by call ID.
- **Stop a run** (too many blocks): the middleware can return a `Command`.

### 10.2 Other frameworks

Integration types, ranked: **official interception hook (can block) > tool wrapping (universal fallback, easier to bypass) > observe-only callbacks (audit only, can't enforce).** Seeing a call isn't the same as being able to stop it.

| Target | Plug-in point | Type | Human pause |
|---|---|---|---|
| LangChain | Middleware `wrap_tool_call` | Hook | Native pause/resume |
| LangGraph | `ToolNode` wrapper | Hook | Native pause/resume |
| Claude Agent SDK | Pre-tool-use hook / permission callback (can deny) | Hook | Callback waits |
| OpenAI Agents SDK | Tool guardrails, or wrap function tools | Hook/wrap | Built-in approval or blocking wait |
| Semantic Kernel | Function-invocation filter | Hook | Blocking wait |
| AutoGen | Intervention handler (drop tool-call messages) | Hook | Blocking wait |
| CrewAI | Tool-call hooks if available, else wrap tools | Hook/wrap | Blocking wait |
| LlamaIndex | Wrap tools (its instrumentation is observe-only) | Wrap | Blocking wait |
| Raw API loop (OpenAI/Claude/Ollama) | Around your tool-dispatch function | Wrap | Write it yourself |

- **Intent transport:** use the run context where the framework has one. For tool wrapping, bind the intent into the guarded tools when they're created (one guarded set per task).
- **Blocking waits** need a timeout that **rejects by default** (fail closed).
- Microsoft is merging AutoGen and Semantic Kernel into the **Microsoft Agent Framework**. Target that instead of both.
- **Verify hook names against current docs** before claiming support; they change fast.

---

## 11. Build order (final scope)

1. **LangChain + LangGraph** (one shared adapter): the main, fully featured integration and demo. We build the test agent ourselves in LangGraph.
2. **Raw API loop:** shows framework-free support, including local Ollama.
3. **One agent SDK** (Claude Agent SDK *or* OpenAI Agents SDK): shows a different hook style. *Optional.*
4. **MCP gateway:** covers third-party apps and other frameworks that use MCP tools, with zero code.
5. **Generic tool wrapper:** *optional.* If dropped, list "non-MCP local tools in other frameworks" as future work.

Chain of trust (multi-agent signing, user → orchestrator → sub-agent): nice-to-have. If attempted, limit it to two levels.

---

## 12. Key design decisions

| Decision | Rationale |
|---|---|
| Ed25519 over HMAC/RSA | Asymmetric (the verifier never needs the private key); tamper-evident; very fast. **Settled; don't re-suggest alternatives unless asked.** |
| Human-confirmed intent before signing | The anchor is human-expressed, not inferred; answers the "prompts are imprecise" critique |
| Layered checks with early exit | Cheap deterministic checks first; expensive LLM only in the gray zone |
| Local sentence-transformers + local LLM judge | No external API dependency, no data leakage, works offline. **Don't suggest API-based embedders or judges.** |
| Judge never sees untrusted content | Avoids the "LLM judge is injectable" circular dependency |
| Automation can only tighten | Rules blocks and human authority are final |
| Interceptor never edits arguments | Simpler and auditable: allow as-is or refuse |
| Fail closed everywhere | Errors and timeouts never become allow |
| Intercept at tool execution, not the LLM API | The provider only proposes calls; execution is where enforcement works |
| One core engine, thin adapters | New frameworks cost a small adapter, not a rewrite |
| Model-agnostic | Works with any LLM backend |

---

## 13. Literature base

Group the papers by role. **Don't claim ASGP is "the first"** intent-alignment system: several exist (§13.3).

**Safe novelty wording:**
> ASGP is a concrete, locally run build of the hybrid architecture proposed by Wang et al. (AHI): human-confirmed signed intent, deterministic rules, local embedding and LLM judging, and risk-adaptive human approval, deployable both as in-process SDK middleware and as an MCP gateway.

### 13.1 Motivation: AHI Reframing ✅ verified against the original PDF

**Wang, Li, Tian (UCLA). "Reframing LLM Agent Security as an Agent–Human Interaction Problem." arXiv:2605.24309v1, May 2026.** **Preprint, not peer-reviewed; a position paper.**

- **Corpus:** 59 papers, 21 production systems, 26 security plugins (as of April 2026).
- **Real five AHI categories**, with adoption across the 21 systems:

  | Category | Adoption |
  |---|---|
  | Scope & boundary configuration | 16/21 |
  | Runtime approval | 15/21 |
  | Policy specification | 14/21 |
  | Trust & data labeling | 0/21 |
  | Intent anchoring | 0/21 (found in 5 academic papers) |

- **Path A (LLM-based, academic):** a secondary model checks proposed actions against the user prompt. This explicitly includes task-alignment classifiers that score each tool call, so **ASGP's embedding scorer and judge are Path A**.
- **Path B (human-based intent expression, industry):** four channels: policy specification, runtime approval, scope configuration, trust labeling. It is *not* just checkpoints.
- **Relationship between the paths:** complementary but asymmetric. **Path B is more fundamental**, because intent can only come from the human.
- **Five reasons humans can't be removed:**
  1. Prompts are imprecise.
  2. Some ambiguity can't be resolved.
  3. LLM judges can be attacked.
  4. Direct human expression beats inference.
  5. Industry converged on human-centric designs.
- **On the 0/21 finding:** the paper reads it partly as industry *rejecting* pure intent anchoring. Its hypotheses are that the value is invisible to users and that unexplained false positives feel hostile; neither is tested.
- **Research agenda:**
  - **D1, fatigue-resistant mechanisms:** risk-adaptive approval (RTBAS blocked all targeted attacks with a 2% utility loss), bidirectional scope.
  - **D2, usable policies:** natural-language-to-formal policy translation, progressive trust.
  - **D3, LLM-augmented human intent alignment:** LLMs should be *assistive, not decisional* (AutoPermissions predicts approvals at 85.1%), plus proactive ambiguity detection.
- **Hybrid** = "automated pre-filtering with targeted human judgment", with the human as the final authority. The agenda is conceptual (no prototypes or user studies), and **ASGP can position itself as a concrete build of it.**
- **Framing warning:** presenting ASGP as *pure* intent anchoring would mean defending exactly what this paper argues against. Always present it as the hybrid.

### 13.2 Benchmark: AgentDojo

**Debenedetti, Zhang, Balunović, Beurer-Kellner, Fischer, Tramèr (ETH Zurich + Invariant Labs). NeurIPS 2024 Datasets & Benchmarks. arXiv:2406.13352.**

- **Setup:** 4 suites (Workspace, Slack, Travel, Banking), 97 user tasks and 629 security test cases.
- **Metrics:** benign utility, utility under attack, targeted attack success rate (ASR).
- **Findings:**
  - More capable models tend to be more attackable. This is a 2024 correlation; newer models with instruction-hierarchy training may differ.
  - The best built-in defense is the **tool filter, at ~7.5% ASR**.
  - Defenses cost about 15–20 points of utility.
  - "Important message" is the strongest attack phrasing. Injections at the end of a tool output are most effective, and correct user/model names roughly double ASR.
- **[UNVERIFIED] GPT-4o numbers conflict between our documents:**
  - Older CLAUDE.md: 69.00% utility / 47.69% ASR.
  - AgentDojo review PDF: 74.69% / 72.32%.
  - Task Shield reports 47.69% as the GPT-4o no-defense ASR under "Important Instructions", which supports the first pair.
  - Tool counts: "74 total" and "17–28 per suite" aren't necessarily a conflict, since per-suite counts add up to the total. But "17–28" probably understates the smaller suites. Check the per-suite counts.
  - Check against the original paper before citing.
- **Role for ASGP:** the main evaluation harness.
  - **The target is no longer "beat 7.5%".** Task Shield reports 2.07% and Progent 1.0% on AgentDojo (different setups).
  - Report ASR, utility under attack and benign utility, plus **per-layer accuracy, per-layer latency and escalation rate** (approval fatigue).

### 13.3 Closest related systems (compare against these in Related Work)

- **Task Shield** (Jia, Wu, Qin, Squicciarini; arXiv:2412.16682, Dec 2024).
  - **What it does:** checks whether each instruction and tool call contributes to the user's goal, then blocks and gives feedback. On AgentDojo with GPT-4o: 2.07% ASR and 69.79% utility under attack (vs. 47.69% / 50.08% with no defense).
  - **Difference from ASGP:** it relies on a cloud LLM and extracts instructions *from tool outputs*, so its judge sees untrusted content. ASGP's judge doesn't, ASGP is local, and its intent is human-confirmed and signed.
- **Progent** (Shi et al., UC Berkeley/UCSB/NUS; arXiv:2504.11703 v3, May 2026).
  - **What it does:** privilege control. An LLM writes allow/forbid policies, plain code enforces them, and an SMT solver checks updates (permissions can only shrink without approval). AgentDojo ASR fell from 39.9% to 1.0%; ASB from 70.3% to 3.9%.
  - **Difference from ASGP:** very close to ASGP's rules layer. ASGP adds human confirmation of the intent and a semantic layer for allowed-tool-bad-argument cases.
- **AgentSpec** (Wang, Poskitt, Sun, SMU; ICSE 2026).
  - **What it does:** a rule language (trigger, check, enforcement) enforced at runtime on LangChain. Over 90% of unsafe code executions intercepted; about 1–3 ms per check.
  - **Difference from ASGP:** comparable to ASGP's rules layer, but hand-written per domain, with no intent model, and evaluated against safety hazards rather than attackers.
- **Alignment Contracts** (David, Guarnieri, Gervais; arXiv:2605.00081, Apr 2026).
  - **What it does:** formal contracts covering scope, effects, budgets and disclosure, with a reference monitor and Lean 4 proofs. The guarantee holds only if every relevant effect passes through the monitor (the Effect Observability Assumption).
  - **Why it matters for ASGP:** supports the "signed scope + enforcement boundary" idea. The observability assumption is the formal version of ASGP's bypass caveat for the SDK mode.
- **OpenKedge** (He & Yu; arXiv:2604.08601, Apr 2026).
  - **What it does:** agents submit an intent; context collection and a Cedar policy produce a contract; short-lived credentials are scoped to that contract; and a linked log records everything. Results are simulated only, and the authors run the company.
  - **Difference from ASGP:** a similar intent → decision → audit flow, but for infrastructure changes, with credential scoping instead of semantic checks.
- **Alignment Gate** (Borigi et al., Missouri S&T + Aiceberg; ESANN 2026).
  - **What it does:** 250 intent types × 217 instruction types, scored offline by ChatGPT; small models label steps at run time against per-intent thresholds. A feasibility study with no accuracy evaluation; most thresholds are 10–15, so it may be permissive.
  - **Why it matters for ASGP:** an alternative to the embedding layer; a useful contrast for threshold-setting.
- **Still to read and compare** (named in the AHI paper as intent-anchoring systems): **MELON, DRIFT, Agent-Sentry, AgentGuardian.**
  - **[UNVERIFIED]** AHI says intent anchoring appears in **5** academic papers, but only these 4 are listed here. Confirm the fifth in the AHI PDF (possibly Task Shield) before citing "5".

### 13.4 Complementary layer: CXI ⚠️ [UNVERIFIED review]

**"CXI: Context-to-Execution Integrity", Igor Santos-Grueiro (UNIR), arXiv:2607.06000v1 (ID taken from our review; confirm it), July 2026.** Our two documents disagree on the authors ("et al." vs. a single author) and on the token-type names:

| Source | T | W | D | O | X |
|---|---|---|---|---|---|
| One version | Trusted | World knowledge | Dynamic | Orchestrator | eXternal |
| Other version | Trust | Workspace | Data | Orchestration | External |

Both describe:
- Three invariants: no field, effect or invocation escapes by untrusted tokens.
- A six-step admission pipeline.
- Zero observed escapes.
- 231/400 tasks (57.75%) completed safely.

**The AHI review turned out to contain invented content, so check this one against the original PDF before citing any detail.**

- **Conceptual role (safe to use):** CXI = boundary integrity ("may this *kind* of input cause this kind of effect?"). ASGP = intent integrity ("does this action match what the user asked for?"). They're complementary.

### 13.5 Survey: Toward Secure LLM Agents

**Ling, Yu, Chen, Fang (2026).** Reviews 247 papers (to April 27, 2026).
- Prompt injection is the dominant threat (142 papers; 86 on indirect injection).
- Defenses are fragmented, and evaluation isn't standardized.
- AgentDojo is the most reused benchmark (30 occurrences).
- 68% of the reviewed papers are preprints.

**Use:** background and threat landscape; it supports the choice of AgentDojo.

### 13.6 Our own report: MCP Proxies and Middleware: A Comparative Analysis (Sept 2026)

- **Content:** surveys 8 open-source MCP gateways and security middleware (Bifrost, Docker MCP Gateway, IBM ContextForge, Microsoft MCP Gateway, MCPProxy, MCPShield, Haze518, AIM-Intelligence). None of them does intent-based checking.
- **Known issues:** see §15.

---

## 14. OWASP LLM Top 10 (2025) mapping

| ID | Name | ASGP link | Strength |
|---|---|---|---|
| LLM01 | Prompt Injection | Limits the *damage* of indirect injection by checking actions against the signed intent; ingress scanner (once automatic) | Strong (mitigation, not prevention) |
| LLM06 | Excessive Agency | Signed scope + rules + high-impact approval | **Strongest** |
| LLM07 | System Prompt Leakage | Only indirect: blocks out-of-scope exfiltration *via tool calls* | Weak; phrase carefully |
| LLM08 | Vector & Embedding Weaknesses | Local embedder removes the *external API* risk; the model can still be fooled by adversarial text | Weak; phrase carefully |

---

## 15. Known errors in older documents (fix before submission)

**`ASGP_Review_Paper3_AHI_Reframing` (DOCX/PDF)**
1. Its taxonomy is invented (Intent Communication / Transparency / Control / Trust Calibration aren't in the paper).
2. It calls the paper "peer-reviewed"; it's a **preprint**.
3. It claims ASGP is "the first open-source system to implement both paths." Unprovable, and the paper itself lists 5 intent-anchoring systems.
4. It misses the thesis: the paper argues intent anchoring *alone* is insufficient.
5. It understates the corpus (only mentions the 21 systems).
6. It describes Path B as checkpoints only, and describes ASGP's human escalation as existing (unconfirmed).

**`ASGP_Review_Paper1_AgentDojo`**
- The GPT-4o figures (74.69% / 72.32%) probably don't match the paper.
- It sets "under 7.5% ASR" as ASGP's target; that bar is outdated (§13.2).

**`ASGP_Review_Paper2_CXI`**
- Not verified against the source; see §13.4.

**`MCP_Proxies_Comparative_Analysis` (our report)**
- **The ASGP column in Table 5.1 overclaims.** Prompt injection detection, semantic alignment scoring, human-in-loop escalation, plain-language explanation and the signing chain are marked ✔, but in the code they're manual, mock, designed-only or unconfirmed. Use "planned" or "partial".
- **"Intent-based governance is entirely absent" is true only among MCP gateways.** Research systems (Task Shield, Progent, OpenKedge, Alignment Gate, Alignment Contracts) do this. Scope the claim to gateways.
- **Some figures come from vendor sources.** Bifrost's 11 µs overhead is cited from Maxim AI's own article. The "97 million monthly downloads" and Cisco RSA 2026 claims need a primary source.
- **The note under Table 5.1 says "proxy is planned future work"**, which is consistent with the build order (the gateway is step 4). Section 5.3 should say this explicitly too.
- **The Bifrost section contradicts itself.**
  - Its capabilities list says "Federated Authentication" turns REST/gRPC APIs into MCP tools, but its cons say it can't do protocol translation. Pick one, based on Bifrost's own docs.
  - It's called "the only tool capable of acting as a true protocol-level proxy", but the other gateways are proxies too. Remove or narrow this claim.
- **Table 5.1 doesn't match the body text.**
  - IBM ContextForge and Microsoft are marked ✔ for tamper-evident audit, but the IBM section says immutable audit trails are "still maturing".
  - Bifrost's ✔ for tamper-evident audit is never supported in its section.
  - AIM-Intelligence is missing from the table, although the report says it compares 8 tools.
- **ASGP's audit claims aren't confirmed in the code.** Table 5.1 gives ASGP ✔ for tamper-evident audit, and §4.2 says Haze518's hash chaining is "the same approach used by ASGP's audit layer". Confirm hash chaining exists in the code, or mark it as planned.
- **§2.2 overclaims.** It says the proxy being invisible to the agent "prevents" injections that target the security layer. Soften this to "reduces": an attacker can still guess that a guard exists and probe it.

---

## 16. Open problems / to-dos

**Code checks**
- [x] Interception: manual `@protect_tool` wrapping in `main` (framework hooks added on this branch)
- [x] Human escalation exists (digest-bound, single-use, expiring approvals)

**Build (critical path first)**
- [ ] **Replace `MockProvider`**: real embedding layer + local LLM judge with JSON verdicts.
- [ ] Add intent confirmation (draft scope → user OK → sign).
- [ ] Add per-tool risk levels (the triggers for high-impact approval).
- [ ] Make the content ingress scanner automatic (middleware, not a manual call).
- [ ] LangChain/LangGraph adapter with interrupt/resume and caching by call ID.

**Design decisions still open (likely defense questions)**
- [ ] **Multi-turn policy:** does a new user message create a new signed intent or extend the old one?
- [x] **Replay protection:** exists for signed agent requests; the new intent token carries session ID, anchor hash, expiry and a unique token ID.
- [ ] **Thresholds:** the embedding high/low cutoffs and the block-count limit. These need empirical tuning.
- [ ] **Sub-agent identity** (only if chain of trust is attempted).

**Evaluation**
- [ ] Expand to 50–100+ scenarios and/or run on AgentDojo.
- [ ] Report ASR, utility (benign and under attack), per-layer accuracy, per-layer latency and escalation rate.

**Writing**
- [ ] Fix the review docs and the MCP report (§15).
- [ ] Verify the CXI and AgentDojo details against the originals.
- [ ] Read MELON, DRIFT, Agent-Sentry and AgentGuardian; write Related Work against §13.3.

---

## 17. Report talking points

- Cite AHI (as a preprint) for **both** the 0/21 gap **and** its argument that humans must stay in the loop. ASGP is a concrete build of its hybrid.
- Integration ranking: hook > wrap > callbacks. Seeing a call isn't the same as being able to stop it.
- The SDK and the gateway are complementary: one is context-rich, the other bypass-resistant.
- State the out-of-scope boundaries explicitly (provider-hosted tools, closed non-MCP agents, in-scope attacks).
- Threat model: a manipulated agent, not a malicious developer.

---

## 18. Instructions for Claude working on this project

- **Never fabricate results.** No numbers unless they come from actual code runs.
- **The handoff design (§5–11) is final.** Don't reopen settled choices (Ed25519, local models, intercepting at tool execution, rejecting an LLM-API proxy) unless asked.
- **Scope conservatively.** Graduation is in 2027. Flag explicitly whenever a suggestion would change the graduation scope.
- **Check which repo is active** before any git operation (`HazemOraby/ASGP` is primary).
- **Don't call ASGP "the first."** Use the novelty wording in §13.
- **Respect the [UNVERIFIED] markers.** Don't repeat those facts in academic writing until they're checked.
- **Verify framework hook names** against current docs before claiming support.
- **Cite across roles:** AHI (motivation), AgentDojo (benchmark), CXI (complementary layer), and the §13.3 systems (related work).

---

## 19. Terminology

| Term | Meaning |
|---|---|
| Intent token | Ed25519-signed payload of the user's **confirmed** intent and scope |
| Scope | The approved list of allowed and forbidden actions drafted from the intent |
| Alignment score | Embedding similarity between a tool call and the intent (0.0–1.0) |
| Gray zone | Scores between the allow and block thresholds; sent to the LLM judge |
| Path A / Path B | AHI terms: automated (LLM/classifier) checking vs. human intent expression |
| Risk-adaptive approval | Human approval only for low-confidence or high-impact calls |
| Fail closed | Errors become block or escalate, never allow |
| ASR | Attack Success Rate |
| Benign utility | Task completion rate with no attack |
| Utility under attack | Task completion rate while an attack is present |
| Silent attack | The attack succeeds *and* the user task completes, so the user notices nothing |
| Intent anchoring | Binding all agent actions to a verified original user intent |
| Ownership gap | The LLM provider, app developer and MCP author each disclaim responsibility for governance |
| Chain of trust | Multi-hop signing (user → orchestrator → sub-agent). Optional |
| MockProvider | Lexical-only scorer from `main` (kept as the `lexical` provider; embedding provider + LLM judge added on this branch) |
