from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CONSUMED = "consumed"


class ApprovalResolution(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalResolve(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution: ApprovalResolution


class ApprovalConsume(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: UUID


class Approval(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    approval_id: UUID
    action_id: UUID
    session_id: UUID
    tool_name: str
    status: ApprovalStatus
    expires_at: datetime
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    reason_codes: tuple[str, ...] = ()
