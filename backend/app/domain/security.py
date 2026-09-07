from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class FindingKind(StrEnum):
    INTENT_ALIGNMENT = "intent_alignment"
    PROMPT_INJECTION = "prompt_injection"
    BEHAVIOR = "behavior"
    PROVIDER_FAILURE = "provider_failure"


class FindingSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    finding_id: UUID = Field(default_factory=uuid4)
    kind: FindingKind
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$", max_length=100)
    severity: FindingSeverity
    confidence: float = Field(ge=0, le=1)
    evidence: str = Field(min_length=1, max_length=500)
    risk_delta: int = Field(ge=0, le=100)


class ContentScanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=100_000)
    source: str = Field(default="unknown", max_length=120)


class ContentScanResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    suspicious: bool
    max_confidence: float = Field(ge=0, le=1)
    findings: tuple[SecurityFinding, ...]
