from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DecisionOutcome(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"


class VerificationResult(BaseModel):
    """Stable Phase 0 response contract consumed by the future tool wrapper."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: UUID
    outcome: DecisionOutcome
    reason_codes: tuple[str, ...] = Field(min_length=1)
    approval_id: UUID | None = None
    risk_before: int = Field(default=0, ge=0, le=100)
    risk_delta: int = Field(default=0, ge=-100, le=100)
    risk_after: int = Field(default=0, ge=0, le=100)
    intent_alignment: float | None = Field(default=None, ge=0, le=1)
    findings: tuple["SecurityFindingResult", ...] = ()
    stage_timings_ms: dict[str, float] = Field(default_factory=dict)
    total_latency_ms: float = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_approval_reference(self) -> "VerificationResult":
        if self.outcome is DecisionOutcome.ESCALATE and self.approval_id is None:
            raise ValueError("ESCALATE results require an approval_id")
        if self.outcome is not DecisionOutcome.ESCALATE and self.approval_id is not None:
            raise ValueError("Only ESCALATE results may include an approval_id")
        return self


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    tool_name: str = Field(min_length=1, max_length=120)
    parameters: dict[str, Any] = Field(default_factory=dict)
    agent_id: UUID | None = None
    intent_anchor_hash: str | None = Field(default=None, min_length=64, max_length=64)
    scope: str | None = Field(default=None, max_length=160)
    timestamp: datetime | None = None
    expires_at: datetime | None = None
    nonce: str | None = Field(default=None, min_length=16, max_length=120)
    sequence: int | None = Field(default=None, ge=1)
    signature: str | None = Field(default=None, min_length=40, max_length=200)


class ApprovalState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CONSUMED = "consumed"


class ContentDisposition(StrEnum):
    CLEAN = "clean"
    QUARANTINED = "quarantined"


class ContentIngressRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: UUID
    content: str = Field(min_length=1, max_length=100_000)
    source: str = Field(default="unknown", max_length=120)


class ContentIngressResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    disposition: ContentDisposition
    safe_content: str | None = None
    max_confidence: float = Field(ge=0, le=1)
    findings: tuple["SecurityFindingResult", ...] = ()


class SecurityFindingResult(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    code: str
    kind: str
    severity: str
    confidence: float = Field(ge=0, le=1)
    evidence: str
    risk_delta: int = Field(ge=0, le=100)


VerificationResult.model_rebuild()
ContentIngressResult.model_rebuild()


class ApprovalResult(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    approval_id: UUID
    action_id: UUID
    status: ApprovalState
