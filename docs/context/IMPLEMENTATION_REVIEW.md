# ASGP — Implementation summary & review of `main`

> External team review of the `main` code (Sept–Oct 2026), converted from `ASGP_Implementation_Summary_and_Review.pdf`. Sections 4–5 are the reviewer's opinion. Claims were cross-checked against the code on Oct 14, 2026 — see "Verification notes" at the end.

## 1. What is built (in `main`)

| Part | What it is |
|---|---|
| Backend (gateway) | Python + FastAPI (`api`, `domain`, `services`, `db`, `core`). 11 groups of REST endpoints under `/api/v1` |
| Database | PostgreSQL 17 + Alembic. Sessions, tools, agents, policies, decisions, approvals, findings, risk changes, audit chain |
| SDK | `protect_tool` decorator, `guard_content` helper, request signing, approval waiting |
| Dashboard | React, 4 pages (Command center, Sessions, Approvals, Research), ~5 s refresh |
| Demo + attack lab | Demo agent and tools; 12 labeled seeds × 5 variants = 60 cases |
| Packaging + tests | Docker Compose (frontend, backend, db, optional demo agent); 17 backend + 4 SDK test files |

Results (controlled 60-case dataset only): exact accuracy 91.7%, malicious caught 100%, legitimate wrongly blocked 25% (benign quotation of attack language), median/P95 16/26 ms, policy-only ablation catches 66.7% of malicious cases.

## 2. Defense layers (order)

Hard rules (any failure → BLOCK, no score can override): session → tool registry → request signature → policy/boundaries.
Signals (add risk points): intent alignment → injection detector → behavior analyzer → risk engine → decision.

## 3. Features and why they exist

| Feature | What it does | Protects against |
|---|---|---|
| Session + intent anchor | Stores the user's request plus allowed/forbidden tools, folders, destinations; hashed and versioned | Agent drifting from the user's goal |
| Tool registry + sensitivity | Tools registered as low/medium/high/critical; optional "needs signature" | Unknown tools; treating reads like external sends |
| Agent identity + signed requests | Ed25519 signature with timestamp, nonce and intent hash | Fake, edited, old or replayed requests. Proves *who* sent it, not that it is safe |
| Boundary rules | Allow/forbid lists; paths inside allowed folders; destinations on allow-list | Path traversal, unknown destinations, out-of-task tools |
| Structured deny policies | Field/operator/value rules as data, never code | Adding protections without code changes |
| Intent alignment | 0–1 score of tool call vs. intent; default is a keyword mock | Allowed-but-unfitting actions |
| Prompt-injection detector | Regex patterns (ignore previous instructions, fake system message, exfiltration, hidden action, long encoded text) | Attacker text in emails/files/web |
| Content ingress guard | Scans outside text before the agent reads it; quarantines dirty text | Poisoning the agent's context |
| Behavior analyzer | Last 10 actions: repeated blocks, reads → external send, many discovery tools | Slow multi-step attacks |
| Risk engine | Session score 0–100; < 40 ALLOW, 40–69 ESCALATE, ≥ 70 BLOCK | One explainable number with memory |
| Decision + reason codes | Machine-readable reasons | Explainability, debugging |
| Human approval | Bound to exact action digest; expires; single use | Approving one thing and running another |
| SDK wrapper (fail-closed) | Tool runs only after ALLOW or approved ESCALATE | Crashes being dangerous |
| Audit log | Hash-chained events; secrets redacted; long text truncated | Accountability; secrets in logs |
| Dashboard | Posture, decision stream, risk history, approvals, explanations, audit seal, research | One place for humans to watch and approve |
| Timing metrics | Per-stage milliseconds | Showing checks are fast enough |
| Attack lab + evaluation | 12 seeds × 5 variants; confusion matrix; policy-only ablation | Thesis evidence |

## 4. Gaps and weaknesses (reviewer's view)

| Level | Gap | Why it matters | Quick fix |
|---|---|---|---|
| High | No API login. Anyone reaching the backend can approve escalations, revoke sessions, create sessions/policies, register tools. The agent could approve its own request | Human approval only works if the agent cannot press "approve" | API key/token; agent role (verify only) vs admin role (approve, revoke, policies) |
| High | SDK can be bypassed (runs in the agent's process) | Only wrapped tools are protected | Keep tool credentials outside the agent; add a proxy |
| High | Boundary checks depend on parameter names (`path`, `recipient`, `destination`); empty allow-lists check nothing | Main anti-leak rule skipped by naming | Tools declare path/destination params; empty lists = deny |
| Medium | Intent alignment is a keyword mock on the tool name only | Weak protection until a real model is connected | Real provider; include parameters |
| Medium | Injection detection = a few English patterns; 25% FP in own lab | Paraphrases pass; real users annoyed | More patterns/ML classifier; report FP honestly |
| Medium | High/critical tools can never reach a human (+70 → BLOCK on first call) | Human approval missing exactly where it matters | Decide the rule (e.g. high = ESCALATE) |
| Medium | Risk washing: each low call −5 | Slow attacks reset the memory | Floor after findings, or time decay |
| Medium | Behavior rules read tool names ("read", "send") | `sync_files` not seen as external | Use sensitivity or a tool category |
| Medium | Audit chain + head in the same DB | Weak against a determined insider | Export latest hash elsewhere / signed timestamp |
| Medium | Only the request is checked, not the result | Tool results can carry injections | Run `guard_content` on tool outputs by default |
| Low | No rate limiting | DoS; fills audit log | Per-session/per-key limit |
| Low | Development defaults (DB password, CORS, HTTP) | Not for shared servers | Env secrets + HTTPS |
| Low | Deny-only policies; no policy UI | Engine looks smaller than it sounds | "Allow with conditions" + admin page, or future work |
| Low | Small evidence base (12 seeds) | Cannot support strong claims | More scenarios |
| Low | Python-only SDK; synchronous approval polling up to 5 min | Hard for other languages / high traffic | Async client, or a proxy |

## 5. SDK or proxy? (reviewer's opinion)

Do not rewrite. Keep the SDK as the main design, fix the top gaps, add a small proxy as an optional second entry point. The decision pipeline is the core value and does not change; a proxy is just another client of the same verify endpoint.

| | SDK (current) | Proxy |
|---|---|---|
| Where | Wrapper around each tool function | Separate service on the call path |
| Bypass | Yes (call the function directly) | Much harder if only the proxy holds tool keys |
| Effort per tool | One decorator line | Must speak each tool's protocol (HTTP, MCP…) |
| Languages | Python | Any |
| Speed | One gateway call | One extra network hop |
| Local functions | Works well | Poor fit |

Suggested order: (1) API auth with agent/admin roles; (2) declared path/destination params, empty lists = deny; (3) decide high/critical behavior; (4) `guard_content` on tool results by default; (5) be clear about mock alignment, FP and wrapped-only limits; (6) optional proxy demo.

## Verification notes (Oct 14, 2026, against `main` @ 58b6f35)

- Confirmed: no auth; boundary checks keyed on the three parameter names; empty `allowed_paths` / `allowed_destinations` skip checks; risk deltas low −5 / medium +40 / high +70 / critical +100; alignment uses tool-name tokens only; behavior rules match substrings of tool names; audit head stored in the same DB.
- Note: an **empty `allowed_tools`** already blocks (`TOOL_OUTSIDE_SCOPE`), and `SessionCreate` requires at least one allowed tool.
- Confirmed present: digest-bound single-use expiring approvals; nonce/sequence/expiry replay protection for signed requests; secret redaction; 64 passing tests.
