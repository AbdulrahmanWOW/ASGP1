from dataclasses import dataclass

from app.domain.decisions import DecisionType
from app.domain.tools import ToolSensitivity


@dataclass(frozen=True)
class RiskAssessment:
    previous: int
    delta: int
    current: int
    outcome: DecisionType
    reason_code: str
    reason: str


class RiskEngine:
    SENSITIVITY_DELTAS = {
        ToolSensitivity.LOW: -5,
        ToolSensitivity.MEDIUM: 40,
        ToolSensitivity.HIGH: 70,
        ToolSensitivity.CRITICAL: 100,
    }

    def hard_block(self, previous: int, reason_code: str) -> RiskAssessment:
        return self._build(
            previous, 20, DecisionType.BLOCK, reason_code, "Hard control blocked action"
        )

    def assess(
        self,
        previous: int,
        sensitivity: ToolSensitivity,
        *,
        signal_delta: int = 0,
        signal_reasons: tuple[str, ...] = (),
    ) -> RiskAssessment:
        sensitivity_delta = self.SENSITIVITY_DELTAS[sensitivity]
        if signal_delta > 0 and sensitivity_delta < 0:
            sensitivity_delta = 0
        delta = sensitivity_delta + signal_delta
        current = max(0, min(100, previous + delta))
        if current >= 70:
            outcome = DecisionType.BLOCK
            code = "RISK_THRESHOLD_BLOCK"
        elif current >= 40:
            outcome = DecisionType.ESCALATE
            code = "RISK_THRESHOLD_ESCALATE"
        else:
            outcome = DecisionType.ALLOW
            code = "RISK_ACCEPTABLE"
        return RiskAssessment(
            previous,
            current - previous,
            current,
            outcome,
            code,
            "; ".join((f"Tool sensitivity is {sensitivity.value}", *signal_reasons)),
        )

    @staticmethod
    def _build(
        previous: int, delta: int, outcome: DecisionType, code: str, reason: str
    ) -> RiskAssessment:
        current = max(0, min(100, previous + delta))
        return RiskAssessment(previous, current - previous, current, outcome, code, reason)
