from uuid import uuid4

import pytest
from asgp_sdk import ActionRequest, DecisionOutcome, VerificationResult, protect_tool
from asgp_sdk.exceptions import ApprovalRequired

from demo.tools import CountedDemoTools


class ApprovingVerifier:
    def __init__(self) -> None:
        self.waited = False

    def verify(self, request: ActionRequest) -> VerificationResult:
        return VerificationResult(
            action_id=request.action_id,
            outcome=DecisionOutcome.ESCALATE,
            reason_codes=("RISK_THRESHOLD_ESCALATE",),
            approval_id=uuid4(),
            risk_before=0,
            risk_delta=40,
            risk_after=40,
        )

    def wait_for_approval(self, approval_id, action_id) -> None:
        self.waited = True


def test_sdk_executes_only_after_approval_wait_succeeds() -> None:
    tools = CountedDemoTools()
    verifier = ApprovingVerifier()
    wrapped = protect_tool(session_id=uuid4(), verifier=verifier)(tools.read_message)

    assert wrapped("msg-1") == "Demo message msg-1"
    assert verifier.waited is True
    assert tools.executions["read_message"] == 1


def test_sdk_without_approval_capability_does_not_execute() -> None:
    tools = CountedDemoTools()

    class EscalatingVerifier:
        def verify(self, request: ActionRequest) -> VerificationResult:
            return VerificationResult(
                action_id=request.action_id,
                outcome=DecisionOutcome.ESCALATE,
                reason_codes=("REVIEW",),
                approval_id=uuid4(),
            )

    wrapped = protect_tool(session_id=uuid4(), verifier=EscalatingVerifier())(tools.read_message)
    with pytest.raises(ApprovalRequired):
        wrapped("msg-1")
    assert tools.executions.get("read_message", 0) == 0


def test_parameter_mutation_during_approval_prevents_execution() -> None:
    executed = 0
    payload = {"recipient": "approved@example.test"}

    class MutatingVerifier(ApprovingVerifier):
        def wait_for_approval(self, approval_id, action_id) -> None:
            payload["recipient"] = "attacker@example.test"

    def send(data: dict[str, str]) -> None:
        nonlocal executed
        executed += 1

    wrapped = protect_tool(session_id=uuid4(), verifier=MutatingVerifier())(send)
    with pytest.raises(ApprovalRequired, match="parameters changed"):
        wrapped(payload)
    assert executed == 0
