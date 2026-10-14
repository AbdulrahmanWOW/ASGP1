import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from app.domain.actions import ActionRequest
from app.domain.policies import Policy, PolicyEffect, PolicyOperator, PolicyRule
from app.domain.sessions import Session
from app.domain.tools import ToolDefinition


@dataclass(frozen=True)
class PolicyResult:
    allowed: bool
    code: str
    message: str


_UNSUPPORTED = object()


def _string_values(value: Any) -> list[str] | object:
    """Return the string values of a boundary parameter, or _UNSUPPORTED (fail closed)."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)) and len(value) <= 100:
        if all(isinstance(item, str) for item in value):
            return list(value)
    return _UNSUPPORTED


def _inside_roots(requested: str, roots: Iterable[str]) -> bool:
    candidate = Path(requested)
    for root_text in roots:
        root = Path(root_text).resolve()
        target = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
        if target == root or root in target.parents:
            return True
    return False


def _destination_allowed(value: str, allowed: Iterable[str]) -> bool:
    folded = value.strip().casefold()
    entries = {item.strip().casefold() for item in allowed if item.strip()}
    if folded in entries:
        return True
    if "://" in folded:
        host = (urlsplit(folded).hostname or "").casefold()
        return bool(host) and host in entries
    if "@" in folded and not folded.startswith("@"):
        domain = folded.rsplit("@", 1)[1]
        return f"@{domain}" in entries
    return False


class PermissionPolicy:
    """Deterministic rules layer: scope, boundaries and structured deny policies."""

    def evaluate(
        self,
        session: Session,
        action: ActionRequest,
        policies: list[Policy],
        tool: ToolDefinition | None = None,
    ) -> PolicyResult:
        tool_name = action.tool_name
        if tool_name in session.forbidden_tools:
            return PolicyResult(False, "TOOL_EXPLICITLY_FORBIDDEN", "Tool is explicitly forbidden.")
        if tool_name not in session.allowed_tools:
            return PolicyResult(False, "TOOL_OUTSIDE_SCOPE", "Tool is outside the allowed scope.")
        boundary_failure = self._check_boundaries(
            session, action.parameters, tool or ToolDefinition(name=tool_name)
        )
        if boundary_failure:
            return boundary_failure
        for policy in policies:
            if not policy.enabled or policy.effect is not PolicyEffect.DENY:
                continue
            if policy.tool_name is not None and policy.tool_name != tool_name:
                continue
            if all(self._matches(rule, action.parameters) for rule in policy.rules):
                return PolicyResult(
                    False, f"POLICY_{policy.name}", "A structured deny policy matched."
                )
        return PolicyResult(True, "TOOL_ALLOWED", "Tool is allowed by session permissions.")

    @staticmethod
    def _check_boundaries(
        session: Session, parameters: dict[str, Any], tool: ToolDefinition
    ) -> PolicyResult | None:
        """Every path/destination parameter must sit inside an explicit allow-list.

        Empty allow-lists deny (fail closed) instead of skipping the check.
        """
        path_names = {name.casefold() for name in tool.effective_path_parameters}
        destination_names = {name.casefold() for name in tool.effective_destination_parameters}
        for key, raw in parameters.items():
            folded = key.casefold()
            if folded in path_names:
                values = _string_values(raw)
                if values is _UNSUPPORTED:
                    return PolicyResult(
                        False, "UNSUPPORTED_BOUNDARY_VALUE", f"Parameter '{key}' is not a path."
                    )
                if values and not session.allowed_paths:
                    return PolicyResult(
                        False,
                        "PATH_BOUNDARY_NOT_CONFIGURED",
                        "The session has no allowed paths for this path parameter.",
                    )
                for value in values:
                    if not _inside_roots(value, session.allowed_paths):
                        return PolicyResult(
                            False, "PATH_OUTSIDE_BOUNDARY", "Path is outside allowed roots."
                        )
            if folded in destination_names:
                values = _string_values(raw)
                if values is _UNSUPPORTED:
                    return PolicyResult(
                        False,
                        "UNSUPPORTED_BOUNDARY_VALUE",
                        f"Parameter '{key}' is not a destination.",
                    )
                if values and not session.allowed_destinations:
                    return PolicyResult(
                        False,
                        "DESTINATION_BOUNDARY_NOT_CONFIGURED",
                        "The session has no allowed destinations for this parameter.",
                    )
                for value in values:
                    if not _destination_allowed(value, session.allowed_destinations):
                        return PolicyResult(
                            False, "DESTINATION_OUTSIDE_BOUNDARY", "Destination is not allowed."
                        )
        return None

    @staticmethod
    def _value(parameters: dict[str, Any], field: str) -> Any:
        value: Any = parameters
        for part in field.split("."):
            if not isinstance(value, dict) or part not in value:
                return None
            value = value[part]
        return value

    def _matches(self, rule: PolicyRule, parameters: dict[str, Any]) -> bool:
        actual, expected = self._value(parameters, rule.field), rule.value
        operations = {
            PolicyOperator.EQUALS: lambda: actual == expected,
            PolicyOperator.NOT_EQUALS: lambda: actual != expected,
            PolicyOperator.CONTAINS: lambda: (
                expected in actual if isinstance(actual, (str, list, tuple)) else False
            ),
            PolicyOperator.IN: lambda: (
                actual in expected if isinstance(expected, (list, tuple, set)) else False
            ),
            PolicyOperator.NOT_IN: lambda: (
                actual not in expected if isinstance(expected, (list, tuple, set)) else False
            ),
            PolicyOperator.MATCHES: lambda: (
                bool(re.fullmatch(expected, actual))
                if isinstance(actual, str) and isinstance(expected, str)
                else False
            ),
            PolicyOperator.GREATER_THAN: lambda: actual > expected,
            PolicyOperator.LESS_THAN: lambda: actual < expected,
        }
        try:
            return bool(operations[rule.operator]())
        except (TypeError, ValueError):
            return False
