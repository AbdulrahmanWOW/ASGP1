"""LangChain 1.x / LangGraph adapter (DESIGN.md §10.1).

LangChain ``create_agent``::

    agent = create_agent(model, tools, middleware=[ASGPMiddleware(guard)],
                         checkpointer=InMemorySaver())   # checkpointer needed for interrupts

LangGraph ``ToolNode``::

    ToolNode(tools, wrap_tool_call=asgp_wrap_tool_call(guard))

Behavior per tool call:

- ALLOW → the real tool runs; its result is returned unchanged (or scanned if
  ``scan_results=True``).
- BLOCK → the tool never runs; the model receives ``ToolMessage("Blocked by ASGP: …",
  status="error")`` and can continue.
- ESCALATE → ``approval_mode="interrupt"`` pauses the graph with ``interrupt()`` (resume with
  ``Command(resume=...)`` after the human decided in the ASGP dashboard; the resume value is
  ignored and the approval is re-checked on the gateway). ``approval_mode="wait"`` blocks the
  call until the approval resolves or times out.
- After ``max_blocks`` blocked calls, the next call raises ``RunTerminated`` and the run stops.

Custom graph nodes that call tools directly bypass this adapter (DESIGN.md §10.1).
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Literal

try:
    from langchain.agents.middleware import AgentMiddleware
    from langchain_core.messages import ToolMessage
    from langgraph.prebuilt.tool_node import ToolCallRequest
    from langgraph.types import Command, interrupt
except ImportError as error:  # pragma: no cover - optional dependency
    raise ImportError("The LangChain adapter needs `pip install 'asgp-sdk[langchain]'`") from error

from asgp_sdk.contracts import DecisionOutcome
from asgp_sdk.guard import GuardDecision, ToolGuard

ApprovalMode = Literal["interrupt", "wait"]
Handler = Callable[[ToolCallRequest], ToolMessage | Command]
AsyncHandler = Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]]


class ASGPMiddleware(AgentMiddleware):
    def __init__(
        self,
        guard: ToolGuard,
        *,
        approval_mode: ApprovalMode = "interrupt",
        scan_results: bool = False,
    ) -> None:
        super().__init__()
        self.guard = guard
        self.approval_mode = approval_mode
        self.scan_results = scan_results

    # --- sync -------------------------------------------------------------------------

    def wrap_tool_call(self, request: ToolCallRequest, handler: Handler) -> ToolMessage | Command:
        call = request.tool_call
        decision = self.guard.check(call["name"], call.get("args") or {}, call_id=call.get("id"))
        if decision.outcome is DecisionOutcome.ALLOW:
            return self._scan(handler(request), call)
        if decision.outcome is DecisionOutcome.ESCALATE and self._approved(decision):
            return self._scan(handler(request), call)
        return self._blocked(call, decision)

    # --- async ------------------------------------------------------------------------

    async def awrap_tool_call(
        self, request: ToolCallRequest, handler: AsyncHandler
    ) -> ToolMessage | Command:
        call = request.tool_call
        decision = await asyncio.to_thread(
            self.guard.check, call["name"], call.get("args") or {}, call_id=call.get("id")
        )
        if decision.outcome is DecisionOutcome.ALLOW:
            return await asyncio.to_thread(self._scan, await handler(request), call)
        if decision.outcome is DecisionOutcome.ESCALATE:
            if self.approval_mode == "wait":
                approved = await asyncio.to_thread(self.guard.wait_for_approval, decision)
            else:
                approved = self._approved(decision)
            if approved:
                return await asyncio.to_thread(self._scan, await handler(request), call)
        return self._blocked(call, decision)

    # --- helpers ----------------------------------------------------------------------

    def _approved(self, decision: GuardDecision) -> bool:
        if self.approval_mode == "wait":
            return self.guard.wait_for_approval(decision)
        while True:
            # On first execution this pauses the graph. When the graph is resumed, LangGraph
            # re-runs this function from the top: the guard's call-ID cache returns the same
            # decision and interrupt() returns the resume value instead of pausing again.
            interrupt(
                {
                    "type": "asgp_approval",
                    "approval_id": str(decision.approval_id),
                    "action_id": str(decision.action_id),
                    "tool": decision.tool_name,
                    "reason_codes": list(decision.reason_codes),
                    "message": "Approve or reject this action in ASGP, then resume the run.",
                }
            )
            status = self.guard.poll_approval(decision)
            if status == "pending":
                continue  # resumed before a human decided: pause again
            return status == "approved"

    def _scan(self, result: ToolMessage | Command, call: dict[str, Any]) -> ToolMessage | Command:
        if not self.scan_results or not isinstance(result, ToolMessage):
            return result
        if not isinstance(result.content, str):
            return result.model_copy(
                update={"content": "[ASGP withheld non-text tool output from scanning]"}
            )
        scanned = self.guard.scan_result(result.content, source=f"tool:{call['name']}")
        return result.model_copy(update={"content": scanned})

    @staticmethod
    def _blocked(call: dict[str, Any], decision: GuardDecision) -> ToolMessage:
        return ToolMessage(
            content=decision.message,
            tool_call_id=call.get("id") or "",
            name=call.get("name"),
            status="error",
        )


def asgp_wrap_tool_call(
    guard: ToolGuard,
    *,
    approval_mode: ApprovalMode = "interrupt",
    scan_results: bool = False,
) -> Callable[[ToolCallRequest, Handler], ToolMessage | Command]:
    """Wrapper for ``langgraph.prebuilt.ToolNode(tools, wrap_tool_call=...)``."""
    middleware = ASGPMiddleware(guard, approval_mode=approval_mode, scan_results=scan_results)
    return middleware.wrap_tool_call
