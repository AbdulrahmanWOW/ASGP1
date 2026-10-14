"""Per-action risk scoring with a separate, monotonic session-suspicion score.

Changes from the MVP engine (see docs/context/IMPLEMENTATION_REVIEW.md):

- The decision is driven by the **action** score (tool base + this call's signals), not by a
  session total that carries across calls. A suspicious session can no longer turn every later
  call into a BLOCK ("session poisoning"); instead it forces human review.
- Session suspicion only grows (findings, hard blocks). Low-risk calls never lower it, so it
  cannot be "washed" by many harmless calls.
- High-impact tools (high/critical sensitivity, or external/delete/payment/admin category) are
  never silently allowed and never blocked by sensitivity alone: they reach a human.
"""

from dataclasses import dataclass

from app.domain.decisions import DecisionType
from app.domain.tools import ToolDefinition, ToolSensitivity


class DecisionLayer:
    RULES = "rules"
    SCORE = "score"
    HIGH_IMPACT = "high_impact"
    SESSION = "session"
    JUDGE = "judge"


@dataclass(frozen=True)
class RiskAssessment:
    previous: int
    delta: int
    current: int
    outcome: DecisionType
    reason_code: str
    reason: str
    action_risk: int = 0
    decided_by: str = DecisionLayer.SCORE


def _clamp(value: int) -> int:
    return max(0, min(100, value))


class RiskEngine:
    BASE_RISK = {
        ToolSensitivity.LOW: 0,
        ToolSensitivity.MEDIUM: 40,
        ToolSensitivity.HIGH: 50,
        ToolSensitivity.CRITICAL: 60,
    }
    ESCALATE_AT = 40
    BLOCK_AT = 70
    SESSION_REVIEW_AT = 70
    HARD_BLOCK_SUSPICION = 20

    def hard_block(self, previous: int, reason_code: str) -> RiskAssessment:
        current = _clamp(previous + self.HARD_BLOCK_SUSPICION)
        return RiskAssessment(
            previous,
            current - previous,
            current,
            DecisionType.BLOCK,
            reason_code,
            "Hard control blocked action",
            action_risk=100,
            decided_by=DecisionLayer.RULES,
        )

    def assess(
        self,
        previous: int,
        tool: ToolDefinition | ToolSensitivity,
        *,
        signal_delta: int = 0,
        signal_reasons: tuple[str, ...] = (),
    ) -> RiskAssessment:
        definition = tool if isinstance(tool, ToolDefinition) else None
        sensitivity = definition.sensitivity if definition else tool
        high_impact = definition.is_high_impact if definition else (
            sensitivity in {ToolSensitivity.HIGH, ToolSensitivity.CRITICAL}
        )
        base = self.BASE_RISK[sensitivity]
        signals = max(0, signal_delta)
        action_risk = _clamp(base + signals)
        current = _clamp(previous + signals)

        decided_by = DecisionLayer.SCORE
        if action_risk >= self.BLOCK_AT:
            outcome, code = DecisionType.BLOCK, "RISK_THRESHOLD_BLOCK"
        elif action_risk >= self.ESCALATE_AT:
            outcome, code = DecisionType.ESCALATE, "RISK_THRESHOLD_ESCALATE"
        else:
            outcome, code = DecisionType.ALLOW, "RISK_ACCEPTABLE"

        if outcome is DecisionType.ALLOW and high_impact:
            outcome, code = DecisionType.ESCALATE, "HIGH_IMPACT_REQUIRES_APPROVAL"
            decided_by = DecisionLayer.HIGH_IMPACT
        if outcome is DecisionType.ALLOW and previous >= self.SESSION_REVIEW_AT:
            outcome, code = DecisionType.ESCALATE, "SESSION_RISK_REQUIRES_REVIEW"
            decided_by = DecisionLayer.SESSION

        reason = "; ".join(
            (f"Tool sensitivity is {sensitivity.value} (base {base})", *signal_reasons)
        )
        return RiskAssessment(
            previous,
            current - previous,
            current,
            outcome,
            code,
            reason,
            action_risk=action_risk,
            decided_by=decided_by,
        )
