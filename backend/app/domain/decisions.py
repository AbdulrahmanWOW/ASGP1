from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

UnitScore = Annotated[float, Field(ge=0.0, le=1.0)]
RiskScore = Annotated[int, Field(ge=0, le=100)]


class DecisionType(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DecisionReason(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z][A-Z0-9_]*$")
    message: str = Field(min_length=1, max_length=500)
    source: str = Field(min_length=1, max_length=80)


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_id: UUID = Field(default_factory=uuid4)
    action_id: UUID
    session_id: UUID
    outcome: DecisionType
    risk_level: RiskLevel
    risk_score: RiskScore
    reasons: tuple[DecisionReason, ...]
    intent_alignment: UnitScore | None = None
    requires_approval: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_approval_contract(self) -> "Decision":
        if self.outcome is DecisionType.ESCALATE and not self.requires_approval:
            raise ValueError("ESCALATE decisions must require approval")
        if self.outcome is not DecisionType.ESCALATE and self.requires_approval:
            raise ValueError("Only ESCALATE decisions may require approval")
        if not self.reasons:
            raise ValueError("A decision must contain at least one reason")
        return self
