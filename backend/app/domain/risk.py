from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RiskChange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: UUID
    session_id: UUID
    previous_score: int = Field(ge=0, le=100)
    delta: int = Field(ge=-100, le=100)
    new_score: int = Field(ge=0, le=100)
    reason: str
    created_at: datetime
