"""ASGP MCP gateway (DESIGN.md §5 "Proxy = MCP gateway").

An MCP server that sits in front of one or more upstream MCP servers. It re-publishes their
tools and routes every ``tools/call`` through ASGP before forwarding:

- ALLOW → forwarded to the upstream server; the result is optionally scanned by content
  ingress before the agent sees it (``scan_results``).
- BLOCK → never reaches the upstream; returned as ``isError`` with ``Blocked by ASGP: …``.
- ESCALATE → the call waits for the human decision (with a timeout) and fails closed.
- Unknown tools, gateway errors and upstream errors never fall through to execution.

This works for agents you don't own (Claude Desktop, Cursor, any MCP client) with only a config
change. It is bypass-resistant **only if** the upstream servers are reachable solely through the
gateway (e.g. launched by it over stdio, or bound to a private network).
"""

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import mcp_types as types
from asgp_sdk.contracts import DecisionOutcome
from asgp_sdk.guard import BLOCK_PREFIX, RunTerminated, ToolGuard
from mcp.server import Server

logger = logging.getLogger(__name__)


class UpstreamClient:
    """What the gateway needs from an upstream connection (``mcp.Client`` satisfies it)."""

    async def list_tools(self) -> types.ListToolsResult: ...  # pragma: no cover

    async def call_tool(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> types.CallToolResult: ...  # pragma: no cover


@dataclass(frozen=True)
class Route:
    upstream: str
    original_name: str
    tool: types.Tool


def _error(text: str) -> types.CallToolResult:
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)], is_error=True)


class ASGPGateway:
    def __init__(
        self,
        guard: ToolGuard,
        upstreams: Mapping[str, UpstreamClient],
        *,
        scan_results: bool = True,
        name: str = "asgp-gateway",
    ) -> None:
        self.guard = guard
        self.upstreams = dict(upstreams)
        self.scan_results = scan_results
        self.name = name
        self.routes: dict[str, Route] = {}

    async def discover(self) -> dict[str, Route]:
        """Collect upstream tools. Name clashes are exposed as ``<upstream>__<tool>``."""
        listed: list[tuple[str, types.Tool]] = []
        for upstream_name, client in self.upstreams.items():
            result = await client.list_tools()
            listed += [(upstream_name, tool) for tool in result.tools]
        counts: dict[str, int] = {}
        for _, tool in listed:
            counts[tool.name] = counts.get(tool.name, 0) + 1
        routes: dict[str, Route] = {}
        for upstream_name, tool in listed:
            exposed = tool.name if counts[tool.name] == 1 else f"{upstream_name}__{tool.name}"
            update: dict[str, Any] = {"name": exposed}
            if self.scan_results:
                # Structured output is not scanned and is therefore dropped; stop advertising it.
                update["output_schema"] = None
            routes[exposed] = Route(upstream_name, tool.name, tool.model_copy(update=update))
        self.routes = routes
        return routes

    async def list_tools(self) -> types.ListToolsResult:
        return types.ListToolsResult(tools=[route.tool for route in self.routes.values()])

    async def call_tool(self, name: str, arguments: dict[str, Any] | None) -> types.CallToolResult:
        route = self.routes.get(name)
        if route is None:
            return _error(f"{BLOCK_PREFIX}: UNKNOWN_TOOL")
        try:
            decision = await asyncio.to_thread(self.guard.check, name, arguments or {})
        except RunTerminated:
            return _error(f"{BLOCK_PREFIX}: RUN_TERMINATED")
        if decision.outcome is DecisionOutcome.ESCALATE:
            approved = await asyncio.to_thread(self.guard.wait_for_approval, decision)
            if not approved:
                return _error(decision.message)
        elif decision.outcome is not DecisionOutcome.ALLOW:
            return _error(decision.message)
        try:
            result = await self.upstreams[route.upstream].call_tool(
                route.original_name, arguments or {}
            )
        except Exception as error:
            logger.warning("Upstream %s failed for %s: %s", route.upstream, name, error)
            return _error(f"Upstream tool error: {type(error).__name__}")
        if not self.scan_results:
            return result
        return await asyncio.to_thread(self._scan, name, result)

    def _scan(self, name: str, result: types.CallToolResult) -> types.CallToolResult:
        content: list[Any] = []
        for block in result.content:
            if isinstance(block, types.TextContent):
                scanned = self.guard.scan_result(block.text, source=f"mcp:{name}")
                content.append(block.model_copy(update={"text": scanned}))
            else:
                content.append(
                    types.TextContent(
                        type="text",
                        text=f"[ASGP withheld non-text tool output ({block.type}) from scanning]",
                    )
                )
        # structured_content is not scanned, so it is not passed through.
        return result.model_copy(update={"content": content, "structured_content": None})

    def build_server(self) -> Server:
        async def on_list_tools(_ctx: Any, _params: Any) -> types.ListToolsResult:
            return await self.list_tools()

        async def on_call_tool(
            _ctx: Any, params: types.CallToolRequestParams
        ) -> types.CallToolResult:
            return await self.call_tool(params.name, params.arguments)

        return Server(
            self.name,
            instructions="Tools are governed by ASGP: some calls may be blocked or need approval.",
            on_list_tools=on_list_tools,
            on_call_tool=on_call_tool,
        )
