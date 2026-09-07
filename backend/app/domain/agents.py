import base64
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


class AgentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    public_key: str

    @field_validator("public_key")
    @classmethod
    def validate_public_key(cls, value: str) -> str:
        try:
            decoded = base64.b64decode(value, validate=True)
        except ValueError as error:
            raise ValueError("public_key must be valid base64") from error
        if len(decoded) != 32:
            raise ValueError("Ed25519 public key must contain 32 bytes")
        return value


class AgentIdentity(AgentCreate):
    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_id: UUID = Field(default_factory=uuid4)
    status: AgentStatus = AgentStatus.ACTIVE
    last_sequence: int = 0
    created_at: datetime
