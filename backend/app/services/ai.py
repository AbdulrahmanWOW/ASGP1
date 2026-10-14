import re
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.domain.actions import ActionRequest
from app.domain.security import FindingKind, FindingSeverity, SecurityFinding
from app.domain.sessions import Session
from app.domain.tools import ToolDefinition


class AlignmentResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    score: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1, max_length=500)
    risk_factors: tuple[str, ...] = ()


@dataclass(frozen=True)
class AlignmentContext:
    intent: str
    allowed_tools: frozenset[str]
    tool_name: str
    parameters: dict[str, Any]
    tool_description: str = ""
    tool_category: str = "other"


class AIProvider(Protocol):
    def score_alignment(self, context: AlignmentContext) -> AlignmentResult | dict: ...


class MockProvider:
    """Deterministic local scorer used by tests and the default MVP runtime."""

    def score_alignment(self, context: AlignmentContext) -> AlignmentResult:
        intent_tokens = set(re.findall(r"[a-z0-9]+", context.intent.casefold()))
        tool_tokens = set(re.findall(r"[a-z0-9]+", context.tool_name.casefold().replace("_", " ")))
        external = bool(tool_tokens & {"send", "upload", "export", "publish", "email"})
        external_authorized = bool(intent_tokens & {"send", "upload", "export", "publish", "email"})
        if external and not external_authorized:
            return AlignmentResult(
                score=0.25,
                reason="External action is not evident in the original intent.",
                risk_factors=("external_action_not_stated",),
            )
        if tool_tokens & intent_tokens:
            return AlignmentResult(score=0.95, reason="Tool purpose overlaps the user intent.")
        return AlignmentResult(
            score=0.75, reason="Tool is allowed but has limited lexical overlap."
        )


class IntentAlignmentService:
    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider

    def analyze(
        self, session: Session, action: ActionRequest, tool: ToolDefinition | None = None
    ) -> tuple[float | None, list[SecurityFinding]]:
        context = AlignmentContext(
            intent=session.intent,
            allowed_tools=session.allowed_tools,
            tool_name=action.tool_name,
            parameters=action.parameters,
            tool_description=tool.description if tool else "",
            tool_category=tool.category.value if tool else "other",
        )
        try:
            result = AlignmentResult.model_validate(self.provider.score_alignment(context))
        except Exception:
            return None, [
                SecurityFinding(
                    kind=FindingKind.PROVIDER_FAILURE,
                    code="AI_PROVIDER_FAILURE",
                    severity=FindingSeverity.MEDIUM,
                    confidence=1,
                    evidence="Intent provider failed or returned an invalid schema.",
                    risk_delta=40,
                )
            ]
        if result.score < 0.3:
            severity, delta = FindingSeverity.HIGH, 45
        elif result.score < 0.6:
            severity, delta = FindingSeverity.MEDIUM, 20
        else:
            return result.score, []
        return result.score, [
            SecurityFinding(
                kind=FindingKind.INTENT_ALIGNMENT,
                code="LOW_INTENT_ALIGNMENT",
                severity=severity,
                confidence=1 - result.score,
                evidence=result.reason,
                risk_delta=delta,
            )
        ]
