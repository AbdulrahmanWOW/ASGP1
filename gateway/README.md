# ASGP MCP gateway

An MCP server that sits between an MCP client (Claude Desktop, Cursor, any agent framework that speaks MCP) and the real MCP servers. Every `tools/call` goes through ASGP first:

| ASGP decision | What the agent sees | Upstream tool runs? |
|---|---|---|
| ALLOW | the upstream result (scanned by content ingress if `scan_results`) | yes |
| BLOCK | `isError: true`, `Blocked by ASGP: <reasons>` | **no** |
| ESCALATE | waits for the human in the ASGP dashboard (`approval_timeout_seconds`), then ALLOW or BLOCK | only if approved |
| gateway unreachable / error | `Blocked by ASGP: ASGP_UNAVAILABLE` (fail closed) | **no** |
| too many blocks | `Blocked by ASGP: RUN_TERMINATED` | **no** |

Use the gateway when you **don't own the agent code** but its tools are MCP servers (see `docs/context/DESIGN.md` §5). It is bypass-resistant only if the upstream servers can be reached **only** through the gateway — e.g. the gateway launches them over stdio, as below.

## Install

```bash
pip install -e ./sdk -e ./gateway
```

## 1. Confirm the intent (human)

```bash
# agent/app drafts a scope
curl -s -X POST $ASGP/api/v1/intents/drafts -H "X-ASGP-Key: $AGENT_KEY" \
     -H 'Content-Type: application/json' -d '{"intent": "Read my project notes"}'
# the human reviews the summary and confirms (user key)
curl -s -X POST $ASGP/api/v1/intents/drafts/<draft_id>/confirm -H "X-ASGP-Key: $USER_KEY" \
     -H 'Content-Type: application/json' -d '{"allowed_paths": ["/home/me/projects/demo"]}'
# -> session.session_id and intent_token.token
```

## 2. Configure

`example.gateway.json` fronts the reference filesystem server. Only tools listed under `tools` are registered when `register_tools` is true; anything else stays unregistered and is blocked (`UNREGISTERED_TOOL`). Tool names must match what the upstream server publishes — check them with `tools/list`.

Secrets come from the environment:

| Variable | Purpose |
|---|---|
| `ASGP_AGENT_KEY` | agent-role API key used for verification |
| `ASGP_SESSION_ID` | the confirmed session |
| `ASGP_INTENT_TOKEN` | the signed intent token from step 1 |
| `ASGP_ADMIN_KEY` | only if `register_tools` is true |

## 3. Point the MCP client at the gateway

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "governed-filesystem": {
      "command": "asgp-gateway",
      "args": ["--config", "/path/to/gateway.json"],
      "env": {
        "ASGP_AGENT_KEY": "…",
        "ASGP_SESSION_ID": "…",
        "ASGP_INTENT_TOKEN": "…"
      }
    }
  }
}
```

Remove the direct entry for the upstream server so the agent has no ungoverned path to it.

## Behaviour notes

- Name clashes across upstreams are exposed as `<upstream>__<tool>`; register that name in ASGP.
- With `scan_results` (default on), text results pass through content ingress; quarantined output is replaced, non-text output is withheld, and `structuredContent` is dropped (output schemas are not advertised) because it is not scanned.
- Upstream exceptions become `isError` results and never leak stack traces.
- Transport: stdio. Streamable-HTTP serving (intent token per HTTP session) is future work.

## Tests

`gateway/tests/test_gateway.py` runs real in-memory MCP servers against the real ASGP pipeline; `test_end_to_end_stdio.py` runs the CLI as a subprocess against an HTTP backend and a stdio upstream.
