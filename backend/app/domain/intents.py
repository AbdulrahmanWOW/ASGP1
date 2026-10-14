from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.sessions import Session


class DraftStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class IntentDraftCreate(BaseModel):
    """A request (usually from the agent runtime) to draft a scope for the user to confirm."""

    model_config = ConfigDict(extra="forbid")

    intent: str = Field(min_length=3, max_length=2_000)
    candidate_tools: tuple[str, ...] | None = Field(default=None, max_length=200)
    allowed_paths: tuple[str, ...] = Field(default=(), max_length=50)
    allowed_destinations: tuple[str, ...] = Field(default=(), max_length=50)


class ScopeItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool: str
    included: bool
    requires_approval: bool = False
    reason: str


class IntentDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    draft_id: UUID
    intent: str
    status: DraftStatus
    allowed_tools: tuple[str, ...]
    forbidden_tools: tuple[str, ...]
    approval_required_tools: tuple[str, ...]
    allowed_paths: tuple[str, ...]
    allowed_destinations: tuple[str, ...]
    items: tuple[ScopeItem, ...]
    summary: str
    drafted_by: str
    created_by: str
    created_at: datetime
    expires_at: datetime
    session_id: UUID | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None


class IntentDraftConfirm(BaseModel):
    """The human's confirmation. Any field left as None keeps the drafted value."""

    model_config = ConfigDict(extra="forbid")

    allowed_tools: frozenset[str] | None = None
    forbidden_tools: frozenset[str] | None = None
    allowed_paths: tuple[str, ...] | None = None
    allowed_destinations: frozenset[str] | None = None


class IntentToken(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    token: str
    session_id: UUID
    anchor_version: int
    anchor_hash: str
    expires_at: datetime
    public_key: str


class ConfirmedIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    session: Session
    intent_token: IntentToken
