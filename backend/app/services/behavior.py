from dataclasses import dataclass

from app.domain.actions import ActionRequest
from app.domain.security import FindingKind, FindingSeverity, SecurityFinding
from app.domain.tools import ToolCategory, ToolDefinition

READ_MARKERS = ("read", "list", "search", "browse", "fetch", "get")
EXTERNAL_MARKERS = ("send", "upload", "export", "publish", "post", "share", "sync")


@dataclass(frozen=True)
class Activity:
    tool_name: str
    outcome: str
    category: str = ToolCategory.OTHER.value


def _is_read(name: str, category: str) -> bool:
    if category == ToolCategory.READ:
        return True
    if category != ToolCategory.OTHER:
        return False
    return any(marker in name.casefold() for marker in READ_MARKERS)


def _is_external(name: str, category: str) -> bool:
    if category == ToolCategory.EXTERNAL:
        return True
    if category != ToolCategory.OTHER:
        return False
    return any(marker in name.casefold() for marker in EXTERNAL_MARKERS)


class BehavioralAnalyzer:
    """Stateful sequence rules over recent session activity.

    Uses the registered tool ``category``; tool-name substrings are only a fallback for tools
    registered without a category.
    """

    def analyze(
        self,
        action: ActionRequest,
        history: list[Activity],
        tool: ToolDefinition | None = None,
    ) -> list[SecurityFinding]:
        findings: list[SecurityFinding] = []
        recent = history[-10:]
        blocked = sum(item.outcome == "BLOCK" for item in recent)
        reads = [item for item in recent if _is_read(item.tool_name, item.category)]
        category = tool.category.value if tool else ToolCategory.OTHER.value
        is_external = _is_external(action.tool_name, category)
        if blocked >= 2:
            findings.append(
                SecurityFinding(
                    kind=FindingKind.BEHAVIOR,
                    code="REPEATED_BLOCKED_ACTIONS",
                    severity=FindingSeverity.MEDIUM,
                    confidence=0.85,
                    evidence="At least two recent actions were blocked.",
                    risk_delta=20,
                )
            )
        if len(reads) >= 3 and is_external:
            findings.append(
                SecurityFinding(
                    kind=FindingKind.BEHAVIOR,
                    code="DATA_STAGING_SEQUENCE",
                    severity=FindingSeverity.HIGH,
                    confidence=0.9,
                    evidence="Multiple reads were followed by an external action.",
                    risk_delta=45,
                )
            )
        distinct_read_tools = {item.tool_name for item in reads}
        if len(distinct_read_tools) >= 4:
            findings.append(
                SecurityFinding(
                    kind=FindingKind.BEHAVIOR,
                    code="RECONNAISSANCE_SEQUENCE",
                    severity=FindingSeverity.MEDIUM,
                    confidence=0.75,
                    evidence="Several distinct discovery tools were used recently.",
                    risk_delta=20,
                )
            )
        return findings
