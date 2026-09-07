from dataclasses import dataclass

from app.domain.actions import ActionRequest
from app.domain.security import FindingKind, FindingSeverity, SecurityFinding


@dataclass(frozen=True)
class Activity:
    tool_name: str
    outcome: str


class BehavioralAnalyzer:
    READ_MARKERS = ("read", "list", "search", "browse", "fetch")
    EXTERNAL_MARKERS = ("send", "upload", "export", "publish", "post")

    def analyze(self, action: ActionRequest, history: list[Activity]) -> list[SecurityFinding]:
        findings: list[SecurityFinding] = []
        recent = history[-10:]
        blocked = sum(item.outcome == "BLOCK" for item in recent)
        reads = [
            item
            for item in recent
            if any(marker in item.tool_name.casefold() for marker in self.READ_MARKERS)
        ]
        is_external = any(marker in action.tool_name.casefold() for marker in self.EXTERNAL_MARKERS)
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
