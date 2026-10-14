"""Framework-free adapter for hand-written agent loops (DESIGN.md §10.2 "Raw API loop").

Works with any model that returns tool calls — OpenAI-compatible APIs, the Anthropic
Messages API, or a local Ollama model — because interception happens around *your*
tool-dispatch function, not around the model::

    toolbox = GuardedToolbox(guard, {"read_file": read_file, "send_email": send_email})
    messages += toolbox.openai_tool_messages(response.choices[0].message.tool_calls)

Blocked calls never execute; the model receives ``Blocked by ASGP: <reasons>`` as the tool
result. ESCALATE waits for the human (blocking, with the guard's timeout) and fails closed.
"""

import json
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from asgp_sdk.contracts import DecisionOutcome
from asgp_sdk.guard import BLOCK_PREFIX, ToolGuard


def _get(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


class GuardedToolbox:
    def __init__(
        self,
        guard: ToolGuard,
        tools: Mapping[str, Callable[..., Any]],
        *,
        scan_results: bool = False,
    ) -> None:
        self.guard = guard
        self.tools = dict(tools)
        self.scan_results = scan_results

    def call(
        self, name: str, arguments: Mapping[str, Any] | None, *, call_id: str | None = None
    ) -> tuple[str, bool]:
        """Run one tool call through ASGP. Returns ``(content, is_error)``."""
        if name not in self.tools:
            return f"{BLOCK_PREFIX}: UNKNOWN_TOOL", True
        if arguments is not None and not isinstance(arguments, Mapping):
            return f"{BLOCK_PREFIX}: INVALID_ARGUMENTS", True
        decision = self.guard.check(name, arguments or {}, call_id=call_id)
        if decision.outcome is DecisionOutcome.ESCALATE:
            if not self.guard.wait_for_approval(decision):
                return decision.message, True
        elif decision.outcome is not DecisionOutcome.ALLOW:
            return decision.message, True
        try:
            result = self.tools[name](**dict(arguments or {}))
        except Exception as error:  # surfaced to the model as a tool error, like any loop would
            return f"Tool error: {type(error).__name__}: {error}"[:2_000], True
        text = result if isinstance(result, str) else json.dumps(result, default=str)
        if self.scan_results:
            text = self.guard.scan_result(text, source=f"tool:{name}")
        return text, False

    # --- provider message formats -----------------------------------------------------

    def openai_tool_messages(self, tool_calls: Iterable[Any] | None) -> list[dict[str, Any]]:
        """OpenAI Chat Completions ``tool_calls`` → ``role="tool"`` messages."""
        messages: list[dict[str, Any]] = []
        for tool_call in tool_calls or ():
            function = _get(tool_call, "function", {})
            name = _get(function, "name", "")
            raw = _get(function, "arguments", "{}")
            try:
                arguments = json.loads(raw) if isinstance(raw, str) else raw
            except json.JSONDecodeError:
                arguments = "invalid"
            content, _ = self.call(name, arguments, call_id=_get(tool_call, "id"))
            messages.append(
                {"role": "tool", "tool_call_id": _get(tool_call, "id"), "content": content}
            )
        return messages

    def anthropic_tool_results(self, content_blocks: Iterable[Any]) -> list[dict[str, Any]]:
        """Anthropic Messages ``tool_use`` blocks → ``tool_result`` blocks for the next turn."""
        results: list[dict[str, Any]] = []
        for block in content_blocks:
            if _get(block, "type") != "tool_use":
                continue
            content, is_error = self.call(
                _get(block, "name", ""), _get(block, "input", {}), call_id=_get(block, "id")
            )
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": _get(block, "id"),
                    "content": content,
                    "is_error": is_error,
                }
            )
        return results

    def ollama_tool_messages(self, tool_calls: Iterable[Any] | None) -> list[dict[str, Any]]:
        """Ollama ``/api/chat`` ``message.tool_calls`` → ``role="tool"`` messages."""
        messages: list[dict[str, Any]] = []
        for index, tool_call in enumerate(tool_calls or ()):
            function = _get(tool_call, "function", {})
            name = _get(function, "name", "")
            content, _ = self.call(
                name,
                _get(function, "arguments", {}),
                call_id=_get(tool_call, "id", f"ollama-{index}"),
            )
            messages.append({"role": "tool", "tool_name": name, "content": content})
        return messages
