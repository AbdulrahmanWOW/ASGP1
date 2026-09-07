from uuid import UUID, uuid4

import pytest
from asgp_sdk import (
    ActionBlocked,
    ActionRequest,
    DecisionOutcome,
    VerificationResult,
    VerificationUnavailable,
    protect_tool,
)

from demo.tools import CountedDemoTools


class FakeVerifier:
    def __init__(self, outcome: DecisionOutcome) -> None:
        self.outcome = outcome
        self.requests: list[ActionRequest] = []

    def verify(self, request: ActionRequest) -> VerificationResult:
        self.requests.append(request)
        return VerificationResult(
            action_id=request.action_id,
            outcome=self.outcome,
            reason_codes=("TEST_DECISION",),
        )


class UnavailableVerifier:
    def verify(self, request: ActionRequest) -> VerificationResult:
        raise VerificationUnavailable("gateway unavailable")


def protected_read(tools: CountedDemoTools, verifier: object, session_id: UUID):
    return protect_tool(session_id=session_id, verifier=verifier, name="read_message")(
        tools.read_message
    )


def test_allowed_tool_executes_exactly_once() -> None:
    tools = CountedDemoTools()
    verifier = FakeVerifier(DecisionOutcome.ALLOW)
    wrapped = protected_read(tools, verifier, uuid4())

    assert wrapped("msg-1") == "Demo message msg-1"
    assert tools.executions["read_message"] == 1
    assert verifier.requests[0].parameters == {"message_id": "msg-1"}


def test_blocked_tool_never_executes() -> None:
    tools = CountedDemoTools()
    wrapped = protected_read(tools, FakeVerifier(DecisionOutcome.BLOCK), uuid4())

    with pytest.raises(ActionBlocked):
        wrapped("msg-1")

    assert tools.executions.get("read_message", 0) == 0


def test_verification_failure_fails_closed() -> None:
    tools = CountedDemoTools()
    wrapped = protected_read(tools, UnavailableVerifier(), uuid4())

    with pytest.raises(VerificationUnavailable):
        wrapped("msg-1")

    assert tools.executions.get("read_message", 0) == 0
