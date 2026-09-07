from uuid import uuid4

import pytest
from app.domain.decisions import Decision, DecisionReason, DecisionType, RiskLevel
from pydantic import ValidationError


def reason() -> DecisionReason:
    return DecisionReason(code="POLICY_ALLOWED", message="Action is within scope.", source="policy")


@pytest.mark.parametrize(
    ("outcome", "requires_approval"),
    [
        (DecisionType.ALLOW, False),
        (DecisionType.BLOCK, False),
        (DecisionType.ESCALATE, True),
    ],
)
def test_valid_decision_contracts(outcome: DecisionType, requires_approval: bool) -> None:
    decision = Decision(
        action_id=uuid4(),
        session_id=uuid4(),
        outcome=outcome,
        risk_level=RiskLevel.LOW,
        risk_score=10,
        reasons=(reason(),),
        requires_approval=requires_approval,
    )

    assert decision.outcome is outcome


def test_escalate_requires_approval() -> None:
    with pytest.raises(ValidationError, match="must require approval"):
        Decision(
            action_id=uuid4(),
            session_id=uuid4(),
            outcome=DecisionType.ESCALATE,
            risk_level=RiskLevel.MEDIUM,
            risk_score=50,
            reasons=(reason(),),
        )


def test_risk_score_is_bounded() -> None:
    with pytest.raises(ValidationError):
        Decision(
            action_id=uuid4(),
            session_id=uuid4(),
            outcome=DecisionType.BLOCK,
            risk_level=RiskLevel.CRITICAL,
            risk_score=101,
            reasons=(reason(),),
        )
