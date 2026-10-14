import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Parameter names treated as filesystem paths / outbound destinations when a tool does not
# declare its own. Matching is case-insensitive on the top-level parameter name.
DEFAULT_PATH_PARAMETERS: tuple[str, ...] = (
    "path",
    "paths",
    "file",
    "files",
    "file_path",
    "filepath",
    "filename",
    "relative_path",
    "directory",
    "dir",
    "folder",
    "source_path",
    "target_path",
)
DEFAULT_DESTINATION_PARAMETERS: tuple[str, ...] = (
    "recipient",
    "recipients",
    "to",
    "cc",
    "bcc",
    "destination",
    "destinations",
    "url",
    "endpoint",
    "webhook",
    "host",
    "email",
    "address",
    "channel",
)
_PARAMETER_NAME = r"^[a-zA-Z_][a-zA-Z0-9_.-]*$"


class ToolSensitivity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolCategory(StrEnum):
    """What kind of effect a tool has. Used by behavior rules and high-impact escalation."""

    READ = "read"
    WRITE = "write"
    EXTERNAL = "external"
    DELETE = "delete"
    PAYMENT = "payment"
    ADMIN = "admin"
    OTHER = "other"


HIGH_IMPACT_CATEGORIES = frozenset(
    {ToolCategory.EXTERNAL, ToolCategory.DELETE, ToolCategory.PAYMENT, ToolCategory.ADMIN}
)
HIGH_IMPACT_SENSITIVITIES = frozenset({ToolSensitivity.HIGH, ToolSensitivity.CRITICAL})


class ToolDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]*$")
    description: str = Field(default="", max_length=500)
    sensitivity: ToolSensitivity = ToolSensitivity.LOW
    requires_signature: bool = False
    category: ToolCategory = ToolCategory.OTHER
    # None = use the defaults above. An explicit empty tuple = the tool has no such parameters.
    path_parameters: tuple[str, ...] | None = None
    destination_parameters: tuple[str, ...] | None = None

    @field_validator("path_parameters", "destination_parameters")
    @classmethod
    def validate_parameter_names(cls, value: tuple[str, ...] | None) -> tuple[str, ...] | None:
        if value is None:
            return None
        if len(value) > 50:
            raise ValueError("At most 50 declared parameters")
        for name in value:
            if not re.fullmatch(_PARAMETER_NAME, name) or len(name) > 120:
                raise ValueError(f"Invalid parameter name: {name!r}")
        return tuple(dict.fromkeys(value))

    @property
    def effective_path_parameters(self) -> tuple[str, ...]:
        return DEFAULT_PATH_PARAMETERS if self.path_parameters is None else self.path_parameters

    @property
    def effective_destination_parameters(self) -> tuple[str, ...]:
        if self.destination_parameters is None:
            return DEFAULT_DESTINATION_PARAMETERS
        return self.destination_parameters

    @property
    def is_high_impact(self) -> bool:
        """High-impact calls always need a human (risk-adaptive approval, DESIGN.md §6)."""
        return (
            self.sensitivity in HIGH_IMPACT_SENSITIVITIES
            or self.category in HIGH_IMPACT_CATEGORIES
        )
