from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ToolSensitivity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]*$")
    description: str = Field(default="", max_length=500)
    sensitivity: ToolSensitivity = ToolSensitivity.LOW
    requires_signature: bool = False
