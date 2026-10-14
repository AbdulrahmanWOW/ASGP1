"""``asgp-gateway --config gateway.json`` — run the MCP gateway over stdio.

Point Claude Desktop, Cursor or any MCP client at this command instead of the real MCP servers.
Secrets are read from environment variables named in the config (defaults: ``ASGP_AGENT_KEY``,
``ASGP_INTENT_TOKEN``, ``ASGP_SESSION_ID``, ``ASGP_ADMIN_KEY`` for optional registration).
"""

import argparse
import logging
import os
import sys
from contextlib import AsyncExitStack
from typing import Any

import anyio
import httpx
from asgp_sdk.client import ASGPClient
from asgp_sdk.guard import ToolGuard
from mcp import Client, StdioServerParameters
from mcp.server.stdio import stdio_server

from asgp_gateway.config import GatewayConfig
from asgp_gateway.gateway import ASGPGateway

logger = logging.getLogger("asgp_gateway")


def build_guard(config: GatewayConfig) -> ToolGuard:
    agent_key = os.getenv(config.asgp.agent_key_env)
    if not agent_key:
        raise SystemExit(f"Set {config.asgp.agent_key_env} to an ASGP agent API key")
    client = ASGPClient(
        config.asgp.base_url,
        timeout_seconds=config.asgp.timeout_seconds,
        api_key=agent_key,
        intent_token=os.getenv(config.asgp.intent_token_env) or None,
    )
    return ToolGuard(
        client,
        session_id=config.asgp.resolved_session_id(),
        intent_token=client.intent_token,
        content_guard=client if config.scan_results else None,
        max_blocks=config.asgp.max_blocks,
        approval_timeout_seconds=config.asgp.approval_timeout_seconds,
    )


def register_tools(config: GatewayConfig, gateway: ASGPGateway) -> list[str]:
    """Register configured tools in ASGP (admin key). Unlisted tools stay unregistered → BLOCK."""
    admin_key = os.getenv(config.asgp.admin_key_env)
    if not admin_key:
        raise SystemExit(f"register_tools needs {config.asgp.admin_key_env}")
    registered: list[str] = []
    for exposed, route in gateway.routes.items():
        policy = config.tools.get(exposed)
        if policy is None:
            continue
        body: dict[str, Any] = {
            "name": exposed,
            "description": (policy.description or route.tool.description or "")[:500],
            "sensitivity": policy.sensitivity,
            "category": policy.category,
        }
        if policy.path_parameters is not None:
            body["path_parameters"] = policy.path_parameters
        if policy.destination_parameters is not None:
            body["destination_parameters"] = policy.destination_parameters
        response = httpx.post(
            f"{config.asgp.base_url.rstrip('/')}/api/v1/tools/register",
            json=body,
            headers={"X-ASGP-Key": admin_key},
            timeout=config.asgp.timeout_seconds,
        )
        response.raise_for_status()
        registered.append(exposed)
    return registered


async def serve(config: GatewayConfig) -> None:
    guard = build_guard(config)
    async with AsyncExitStack() as stack:
        upstreams: dict[str, Any] = {}
        for upstream in config.upstreams:
            target: Any = upstream.url
            if upstream.command is not None:
                target = StdioServerParameters(
                    command=upstream.command,
                    args=upstream.args,
                    env={**os.environ, **upstream.env} if upstream.env else None,
                )
            upstreams[upstream.name] = await stack.enter_async_context(Client(target))
        gateway = ASGPGateway(guard, upstreams, scan_results=config.scan_results)
        routes = await gateway.discover()
        logger.info("Fronting %d tools from %d upstream servers", len(routes), len(upstreams))
        if config.register_tools:
            logger.info("Registered in ASGP: %s", register_tools(config, gateway))
        server = gateway.build_server()
        read_stream, write_stream = await stack.enter_async_context(stdio_server())
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="ASGP MCP gateway (stdio)")
    parser.add_argument("--config", required=True, help="Path to gateway JSON config")
    parser.add_argument("--log-level", default="WARNING")
    args = parser.parse_args(argv)
    # stdout carries the MCP protocol; logs go to stderr.
    logging.basicConfig(stream=sys.stderr, level=args.log_level.upper())
    anyio.run(serve, GatewayConfig.load(args.config))


if __name__ == "__main__":  # pragma: no cover
    main()
