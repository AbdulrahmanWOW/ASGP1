from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.domain.decisions import DecisionType


class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    action_id: UUID
    session_id: UUID
    tool_name: str
    safe_parameters: dict[str, Any]
    outcome: DecisionType
    reason_codes: tuple[str, ...]
    sequence: int = Field(ge=1)
    previous_hash: str = Field(min_length=64, max_length=64)
    entry_hash: str = Field(min_length=64, max_length=64)
    risk_before: int = Field(ge=0, le=100)
    risk_after: int = Field(ge=0, le=100)
    finding_codes: tuple[str, ...] = ()
    stage_timings_ms: dict[str, float] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    intent_anchor_hash: str | None = Field(default=None, min_length=64, max_length=64)
    decided_by: str | None = None
    actor: str | None = None


class AuditVerification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: UUID
    valid: bool
    event_count: int = Field(ge=0)
    verified_hash: str
    errors: tuple[str, ...] = ()
