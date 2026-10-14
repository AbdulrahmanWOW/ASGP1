"""End-to-end: MCP client → `python -m asgp_gateway` (stdio) → upstream MCP server (stdio),
with the ASGP backend served over real HTTP. This is the Claude Desktop / Cursor deployment path.
"""

import json
import os
import socket
import sys
import textwrap
import threading
import time
from pathlib import Path

import anyio
import httpx
import uvicorn
from app.main import create_app
from mcp import Client, StdioServerParameters

from tests_support.harness import ADMIN, AGENT, KEYS, USER, h

UPSTREAM = textwrap.dedent(
    """
    from mcp.server.mcpserver import MCPServer

    server = MCPServer("demo-mail")

    @server.tool()
    def read_email(limit: int = 1) -> str:
        \"\"\"Read inbox emails.\"\"\"
        return f"{limit} email(s): the quarterly report is attached"

    @server.tool()
    def delete_email(message_id: str) -> str:
        \"\"\"Delete an email.\"\"\"
        with open(__file__ + ".deleted", "w") as marker:
            marker.write(message_id)
        return "deleted"

    server.run("stdio")
    """
)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_stdio_gateway_end_to_end(tmp_path: Path) -> None:
    port = free_port()
    app = create_app(
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'e2e.db').as_posix()}",
        initialize_schema=True,
        auth_mode="required",
        api_keys=KEYS,
    )
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                if httpx.get(f"{base}/api/v1/health", timeout=0.5).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.05)
        upstream = tmp_path / "upstream.py"
        upstream.write_text(UPSTREAM)
        config = tmp_path / "gateway.json"
        config.write_text(
            json.dumps(
                {
                    "asgp": {"base_url": base, "approval_timeout_seconds": 2},
                    "upstreams": [
                        {"name": "mail", "command": sys.executable, "args": [str(upstream)]}
                    ],
                    "register_tools": True,
                    "tools": {
                        "read_email": {"sensitivity": "low", "category": "read"},
                        "delete_email": {"sensitivity": "high", "category": "delete"},
                    },
                }
            )
        )
        # The human confirms a scope: reading is fine, deleting is not part of the request.
        httpx.post(
            f"{base}/api/v1/tools/register",
            json={"name": "read_email", "category": "read"},
            headers=h(ADMIN),
        ).raise_for_status()
        httpx.post(
            f"{base}/api/v1/tools/register",
            json={"name": "delete_email", "sensitivity": "high", "category": "delete"},
            headers=h(ADMIN),
        ).raise_for_status()
        draft = httpx.post(
            f"{base}/api/v1/intents/drafts",
            json={"intent": "Read my latest emails"},
            headers=h(AGENT),
        ).json()
        confirmed = httpx.post(
            f"{base}/api/v1/intents/drafts/{draft['draft_id']}/confirm",
            json={},
            headers=h(USER),
        ).json()
        env = {
            **os.environ,
            "ASGP_AGENT_KEY": AGENT,
            "ASGP_ADMIN_KEY": ADMIN,
            "ASGP_SESSION_ID": confirmed["session"]["session_id"],
            "ASGP_INTENT_TOKEN": confirmed["intent_token"]["token"],
        }

        async def drive():
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "asgp_gateway", "--config", str(config)],
                env=env,
            )
            async with Client(params) as agent:
                names = {tool.name for tool in (await agent.list_tools()).tools}
                read = await agent.call_tool("read_email", {"limit": 2})
                delete = await agent.call_tool("delete_email", {"message_id": "m-1"})
                return names, read, delete

        names, read, delete = anyio.run(drive)
        audit = httpx.get(
            f"{base}/api/v1/audit/{confirmed['session']['session_id']}", headers=h(USER)
        ).json()
    finally:
        server.should_exit = True
        thread.join(timeout=10)

    assert names == {"read_email", "delete_email"}
    assert not read.is_error and "quarterly report" in read.content[0].text
    assert delete.is_error
    assert delete.content[0].text == "Blocked by ASGP: TOOL_EXPLICITLY_FORBIDDEN"
    assert not Path(f"{upstream}.deleted").exists()  # the upstream tool never ran
    assert [event["outcome"] for event in audit] == ["ALLOW", "BLOCK"]
    assert {event["actor"] for event in audit} == {"test-agent"}
