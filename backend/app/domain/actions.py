from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.domain.security import SecurityFinding


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    tool_name: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]*$")
    parameters: dict[str, Any] = Field(default_factory=dict)
    agent_id: UUID | None = None
    intent_anchor_hash: str | None = Field(default=None, min_length=64, max_length=64)
    scope: str | None = Field(default=None, max_length=160)
    timestamp: datetime | None = None
    expires_at: datetime | None = None
    nonce: str | None = Field(default=None, min_length=16, max_length=120)
    sequence: int | None = Field(default=None, ge=1)
    signature: str | None = Field(default=None, min_length=40, max_length=200)


class ActionVerification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: UUID
    outcome: str
    reason_codes: tuple[str, ...]
    approval_id: UUID | None = None
    risk_before: int = Field(ge=0, le=100)
    risk_delta: int = Field(ge=-100, le=100)
    risk_after: int = Field(ge=0, le=100)
    intent_alignment: float | None = Field(default=None, ge=0, le=1)
    findings: tuple[SecurityFinding, ...] = ()
    stage_timings_ms: dict[str, float] = Field(default_factory=dict)
    total_latency_ms: float = Field(default=0, ge=0)
