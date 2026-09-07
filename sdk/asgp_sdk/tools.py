import inspect
import json
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar, cast
from uuid import UUID

from asgp_sdk.client import ContentGuard, Verifier
from asgp_sdk.contracts import (
    ActionRequest,
    ContentDisposition,
    ContentIngressRequest,
    DecisionOutcome,
)
from asgp_sdk.exceptions import ActionBlocked, ApprovalRequired, ContentQuarantined

P = ParamSpec("P")
R = TypeVar("R")


def guard_content(
    *, session_id: UUID, guard: ContentGuard, content: str, source: str = "unknown"
) -> str:
    """Return clean external content or fail closed before agent consumption."""

    result = guard.ingest_content(
        ContentIngressRequest(session_id=session_id, content=content, source=source)
    )
    if result.disposition is ContentDisposition.QUARANTINED or result.safe_content is None:
        raise ContentQuarantined(tuple(finding.code for finding in result.findings))
    return result.safe_content


def protect_tool(
    *, session_id: UUID, verifier: Verifier, name: str | None = None
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Verify a registered tool call before invoking its original function."""

    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        tool_name = name or function.__name__
        signature = inspect.signature(function)

        @wraps(function)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            parameters = cast(dict[str, Any], dict(bound.arguments))
            parameter_snapshot = json.dumps(
                parameters, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )
            result = verifier.verify(
                ActionRequest(session_id=session_id, tool_name=tool_name, parameters=parameters)
            )
            if result.outcome is DecisionOutcome.BLOCK:
                raise ActionBlocked(result.reason_codes)
            if result.outcome is DecisionOutcome.ESCALATE:
                waiter = getattr(verifier, "wait_for_approval", None)
                if waiter is None or result.approval_id is None:
                    raise ApprovalRequired("Action requires an external approval workflow")
                waiter(result.approval_id, result.action_id)
                if parameter_snapshot != json.dumps(
                    parameters, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ):
                    raise ApprovalRequired("Action parameters changed while awaiting approval")
            return function(*args, **kwargs)

        return wrapped

    return decorator
