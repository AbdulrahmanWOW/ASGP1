from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SessionStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: str = Field(min_length=3, max_length=2_000)
    allowed_tools: frozenset[str] = Field(min_length=1)
    forbidden_tools: frozenset[str] = Field(default_factory=frozenset)
    allowed_paths: tuple[str, ...] = ()
    allowed_destinations: frozenset[str] = Field(default_factory=frozenset)

    @model_validator(mode="after")
    def permissions_must_not_conflict(self) -> "SessionCreate":
        overlap = self.allowed_tools & self.forbidden_tools
        if overlap:
            raise ValueError(f"Tools cannot be both allowed and forbidden: {sorted(overlap)}")
        return self


class Session(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: UUID = Field(default_factory=uuid4)
    intent: str
    allowed_tools: frozenset[str]
    forbidden_tools: frozenset[str]
    allowed_paths: tuple[str, ...] = ()
    allowed_destinations: frozenset[str] = Field(default_factory=frozenset)
    anchor_version: int = Field(default=1, ge=1)
    risk_score: int = Field(default=0, ge=0, le=100)
    intent_anchor_hash: str = Field(min_length=64, max_length=64)
    status: SessionStatus = SessionStatus.ACTIVE
    status_reason: str | None = None
    requires_intent_token: bool = False
    confirmed_by: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class IntentAnchorUpdate(SessionCreate):
    expected_current_version: int = Field(ge=1)
