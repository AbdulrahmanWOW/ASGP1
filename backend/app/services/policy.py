from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.domain.actions import ActionRequest
from app.domain.policies import Policy, PolicyEffect, PolicyOperator, PolicyRule
from app.domain.sessions import Session


@dataclass(frozen=True)
class PolicyResult:
    allowed: bool
    code: str
    message: str


class PermissionPolicy:
    """Phase 1 deterministic policy based on the session tool allowlist."""

    def evaluate(
        self, session: Session, action: ActionRequest, policies: list[Policy]
    ) -> PolicyResult:
        tool_name = action.tool_name
        if tool_name in session.forbidden_tools:
            return PolicyResult(False, "TOOL_EXPLICITLY_FORBIDDEN", "Tool is explicitly forbidden.")
        if tool_name not in session.allowed_tools:
            return PolicyResult(False, "TOOL_OUTSIDE_SCOPE", "Tool is outside the allowed scope.")
        boundary_failure = self._check_boundaries(session, action.parameters)
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
    def _check_boundaries(session: Session, parameters: dict[str, Any]) -> PolicyResult | None:
        if session.allowed_paths and isinstance(parameters.get("path"), str):
            requested = Path(parameters["path"]).resolve()
            allowed = [Path(path).resolve() for path in session.allowed_paths]
            if not any(requested == root or root in requested.parents for root in allowed):
                return PolicyResult(
                    False, "PATH_OUTSIDE_BOUNDARY", "Path is outside allowed roots."
                )
        for field in ("recipient", "destination"):
            value = parameters.get(field)
            if session.allowed_destinations and isinstance(value, str):
                if value.casefold() not in {
                    item.casefold() for item in session.allowed_destinations
                }:
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
        import re

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
