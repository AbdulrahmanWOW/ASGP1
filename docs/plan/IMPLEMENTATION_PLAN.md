# Implementation plan — branch `new-test-branch-with-newer-sdks-and-proxy`

Goal: move `main` (additive-score MVP) to the final hybrid design in `docs/context/DESIGN.md` §5–11 without a rewrite. Each phase lands as its own commit with tests. Status boxes are updated as work lands.

Design invariants every change must keep (DESIGN.md §6, §12):

- Hard rules first; no score, judge or adapter can override a rules BLOCK.
- Automation can only tighten. The judge never approves a high/critical action alone.
- Fail closed: errors, timeouts, invalid output → BLOCK or ESCALATE, never ALLOW.
- The judge never sees untrusted content (email/web/file bodies).
- Adapters never edit tool arguments: allow as-is or refuse.
- Local models only; no external AI APIs.
- No fabricated results: numbers only from `python -m demo.evaluate` runs.

## Phase 1 — Security fixes to the existing pipeline

| # | Change | Acceptance criteria |
|---|---|---|
| 1.1 | **API authentication with roles** (`admin`, `user`, `agent`) via `X-ASGP-Key` / `Authorization: Bearer`. Keys from `ASGP_API_KEYS`. `ASGP_AUTH_MODE=disabled` only outside `production` | Agent key cannot resolve approvals, update intent, register tools/agents/policies, revoke. `resolved_by` = principal name. Unauthenticated → 401, wrong role → 403. Production + disabled auth refuses to start |
| 1.2 | **Tool declarations**: `category` (read/write/external/delete/payment/admin/other), `path_parameters`, `destination_parameters` (defaults cover common names: `file`, `url`, `to`, …) | A declared/default path or destination parameter with an **empty allow-list → BLOCK** (`*_BOUNDARY_NOT_CONFIGURED`). List values checked element-wise. URL destinations matched by host; `@domain` entries match emails |
| 1.3 | **Risk engine rework**: per-action score (low 0 / medium 40 / high 50 / critical 60 + signals); session suspicion is monotonic (no washing); high/critical floor = ESCALATE; session ≥ 70 floor = ESCALATE; N blocks per session (default 5) auto-revokes the session | High/critical tools reach a human; low calls never lower risk; a poisoned session escalates instead of blocking everything; repeated blocks terminate the run |
| 1.4 | **Behavior analyzer** uses tool `category` (name substrings only as fallback) | `sync_files` registered as `external` triggers the data-staging rule |
| 1.5 | **Traceability**: actions record intent-anchor version + hash; decisions record `decided_by` layer and per-action risk; approvals record `resolved_by`; audit events include anchor hash + layer (old chains still verify) | Alembic migration `0006`; audit verification passes for old and new events |

## Phase 2 — Hybrid pipeline (DESIGN.md §6–7)

| # | Change | Acceptance criteria |
|---|---|---|
| 2.1 | **Intent drafting + human confirmation**: `POST /intents/drafts` (agent/user) drafts a scope from the registry; `POST /intents/drafts/{id}/confirm` (user/admin only) creates the session, optionally with edits; `…/reject` | Agent cannot confirm its own draft. High/critical tools appear as "needs approval each time". Confirmed anchor records `confirmed_by` |
| 2.2 | **Signed intent token** (gateway Ed25519 key): issued on confirm / re-issued after intent updates; carried by SDKs as `intent_token`; verified on every call for sessions that require it | Missing/forged/expired/stale-version token → hard BLOCK (`INTENT_TOKEN_*`). Public key at `GET /intents/public-key` |
| 2.3 | **Embedding alignment layer**: provider interface with `lexical` (old mock), `hashing` (deterministic, dependency-free) and `sentence-transformers` (local model, lazy import). Scores tool name + description + category + **arguments** | Provider failure → finding (fail closed). Alignment input includes arguments |
| 2.4 | **Local LLM judge** (Ollama) for the gray zone only: sees signed scope + structured call + prior call names/args, never untrusted content; strict JSON verdict | Invalid JSON / timeout / error → ESCALATE. Judge BLOCK tightens. Judge ALLOW only for non-high-impact tools in a non-suspicious session. `decided_by=judge` recorded |
| 2.5 | Settings + container wiring (`ASGP_ALIGNMENT_PROVIDER`, `ASGP_JUDGE`, `ASGP_OLLAMA_URL`, `ASGP_JUDGE_MODEL`, `ASGP_REQUIRE_INTENT_TOKEN`, `ASGP_INTENT_SIGNING_KEY`, `ASGP_MAX_BLOCKS_PER_SESSION`) | Defaults keep the stack runnable with no model downloads |

## Phase 3 — SDK adapters (DESIGN.md §9–10)

| # | Change | Acceptance criteria |
|---|---|---|
| 3.1 | **`ToolGuard` core** (framework-agnostic): verify, decision cache by call ID, block counter → `RunTerminated`, fail-closed, approval wait/consume, optional result scanning. Client sends API key + intent token | Unreachable gateway → BLOCK decision, tool never runs |
| 3.2 | **LangChain / LangGraph adapter**: `ASGPMiddleware` (`wrap_tool_call` / `awrap_tool_call`) and `asgp_wrap_tool_call` for `ToolNode`. Block → `ToolMessage(status="error")`. Escalate → `interrupt()` (needs checkpointer) or blocking poll. Resume re-run uses the call-ID cache | Tested against real `langchain` / `langgraph` packages |
| 3.3 | **Raw API loop adapter**: `GuardedToolbox` for OpenAI-style, Anthropic-style and Ollama tool calls | Blocked calls return `Blocked by ASGP: …` tool results |
| 3.4 | **Claude Agent SDK adapter**: `can_use_tool` permission callback + `PreToolUse` hook | Deny result carries the ASGP reason |

## Phase 4 — MCP gateway (DESIGN.md §5)

| # | Change | Acceptance criteria |
|---|---|---|
| 4.1 | **`asgp-gateway`**: MCP server that fronts upstream MCP servers (stdio), lists their tools, routes every `tools/call` through ASGP, forwards only on ALLOW / approved ESCALATE | Blocked call never reaches upstream; result returned as `isError` with reason |
| 4.2 | Optional tool auto-registration from config; optional **tool-result scanning** (quarantine injected output) | Injected upstream output is quarantined before the agent sees it |
| 4.3 | Config file + CLI for Claude Desktop / Cursor | Example config in `gateway/README.md` |

## Phase 5 — Verification

- All backend, SDK, adapter and gateway tests pass; `ruff` clean.
- Re-run `python -m demo.evaluate`; report changes honestly (new seeds for the new rules).
- Independent review of the diff against the invariants above.
- Update README, LIMITATIONS, and this plan's status.

## Out of scope for this branch (future work)

Rate limiting; exporting audit heads outside the DB; multi-agent chain of trust; streamable-HTTP gateway transport; OpenAI Agents SDK adapter; dashboard pages for drafts/policies; AgentDojo run.

## Status

- [x] Context pack (`CLAUDE.md`, `docs/context/`, this plan)
- [x] Phase 1 — auth + roles, fail-closed boundaries, risk rework + run termination, category-based behavior, traceability (migration 0006)
- [ ] Phase 2
- [ ] Phase 3
- [ ] Phase 4
- [ ] Phase 5
