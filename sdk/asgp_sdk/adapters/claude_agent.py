"""Claude Agent SDK adapter (DESIGN.md §10.2).

Two integration points; use either (or both):

``can_use_tool`` permission callback — every tool use asks ASGP::

    options = ClaudeAgentOptions(can_use_tool=asgp_can_use_tool(guard))

``PreToolUse`` hook — also fires for tools the CLI would auto-approve::

    options = ClaudeAgentOptions(hooks=asgp_hooks(guard))

Tool names are the SDK's names (``Bash``, ``Read``, ``mcp__<server>__<tool>`` …); register the
same names in the ASGP tool registry. On ALLOW the hook returns no opinion (``{}``) so the
SDK's normal permission rules still apply — ASGP can only make a decision stricter.
"""

import asyncio
from typing import Any

try:
    from claude_agent_sdk import HookMatcher
    from claude_agent_sdk.types import (
        PermissionResultAllow,
        PermissionResultDeny,
        ToolPermissionContext,
    )
except ImportError as error:  # pragma: no cover - optional dependency
    raise ImportError(
        "The Claude Agent SDK adapter needs `pip install 'asgp-sdk[claude]'`"
    ) from error

from asgp_sdk.contracts import DecisionOutcome
from asgp_sdk.guard import GuardDecision, ToolGuard


async def _decide(
    guard: ToolGuard, tool_name: str, tool_input: dict[str, Any], call_id: str | None
):
    decision: GuardDecision = await asyncio.to_thread(
        guard.check, tool_name, tool_input, call_id=call_id
    )
    if decision.outcome is DecisionOutcome.ESCALATE:
        approved = await asyncio.to_thread(guard.wait_for_approval, decision)
        return decision, approved
    return decision, decision.outcome is DecisionOutcome.ALLOW


def asgp_can_use_tool(guard: ToolGuard):
    async def can_use_tool(
        tool_name: str, tool_input: dict[str, Any], context: ToolPermissionContext
    ) -> PermissionResultAllow | PermissionResultDeny:
        decision, allowed = await _decide(guard, tool_name, tool_input, context.tool_use_id)
        if allowed:
            return PermissionResultAllow()  # never rewrites the input
        return PermissionResultDeny(message=decision.message, interrupt=guard.terminated)

    return can_use_tool


def asgp_pre_tool_use_hook(guard: ToolGuard):
    async def hook(input_data: dict[str, Any], tool_use_id: str | None, context: Any) -> dict:
        if input_data.get("hook_event_name") != "PreToolUse":
            return {}
        decision, allowed = await _decide(
            guard,
            input_data.get("tool_name", ""),
            input_data.get("tool_input") or {},
            tool_use_id or input_data.get("tool_use_id"),
        )
        if allowed:
            return {}
        output: dict[str, Any] = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": decision.message,
            }
        }
        if guard.terminated:
            output["continue_"] = False
            output["stopReason"] = "ASGP stopped the run after repeated blocked tool calls."
        return output

    return hook


def asgp_hooks(guard: ToolGuard, *, matcher: str | None = None) -> dict[str, list[HookMatcher]]:
    return {"PreToolUse": [HookMatcher(matcher=matcher, hooks=[asgp_pre_tool_use_hook(guard)])]}
