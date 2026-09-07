from uuid import uuid4

import pytest
from asgp_sdk import DecisionOutcome, VerificationResult
from pydantic import ValidationError


@pytest.mark.parametrize("outcome", [DecisionOutcome.ALLOW, DecisionOutcome.BLOCK])
def test_terminal_results_do_not_need_approval(outcome: DecisionOutcome) -> None:
    result = VerificationResult(action_id=uuid4(), outcome=outcome, reason_codes=("TEST_REASON",))
    assert result.approval_id is None


def test_escalate_result_requires_approval_reference() -> None:
    with pytest.raises(ValidationError, match="require an approval_id"):
        VerificationResult(
            action_id=uuid4(),
            outcome=DecisionOutcome.ESCALATE,
            reason_codes=("REVIEW_REQUIRED",),
        )


def test_escalate_result_accepts_approval_reference() -> None:
    approval_id = uuid4()
    result = VerificationResult(
        action_id=uuid4(),
        outcome=DecisionOutcome.ESCALATE,
        reason_codes=("REVIEW_REQUIRED",),
        approval_id=approval_id,
    )
    assert result.approval_id == approval_id
