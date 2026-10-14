from dataclasses import replace

from app.core.canonical import action_digest
from app.core.logging import redact
from app.domain.actions import ActionRequest, ActionVerification
from app.domain.decisions import DecisionType
from app.domain.security import SecurityFinding
from app.domain.sessions import Session, SessionStatus
from app.services.ai import IntentAlignmentService
from app.services.behavior import BehavioralAnalyzer
from app.services.crypto import RequestCryptoVerifier
from app.services.injection import InjectionDetector
from app.services.policy import PermissionPolicy
from app.services.risk import RiskAssessment, RiskEngine
from app.services.store import DatabaseStore
from app.services.timing import PipelineTimer

TERMINATION_REASON = "SESSION_TERMINATED_REPEATED_BLOCKS"


class GovernanceService:
    """Orchestrates the verification pipeline for one proposed tool call.

    Order: session → tool registry → request signature → rules (scope, boundaries, policies)
    → signals (alignment, injection, behavior) → risk score → floors (high impact, session).
    Hard-rule failures BLOCK and nothing later can override them.
    """

    def __init__(
        self,
        store: DatabaseStore,
        policy: PermissionPolicy,
        risk: RiskEngine,
        crypto: RequestCryptoVerifier,
        alignment: IntentAlignmentService,
        injection: InjectionDetector,
        behavior: BehavioralAnalyzer,
        approval_ttl_seconds: int,
        *,
        max_blocks_per_session: int = 5,
    ) -> None:
        self.store = store
        self.policy = policy
        self.risk = risk
        self.crypto = crypto
        self.alignment = alignment
        self.injection = injection
        self.behavior = behavior
        self.approval_ttl_seconds = approval_ttl_seconds
        self.max_blocks_per_session = max_blocks_per_session

    def verify(self, action: ActionRequest, *, actor: str | None = None) -> ActionVerification:
        timer = PipelineTimer()
        with timer.stage("session_validation"):
            session = self.store.get_session(action.session_id)
        if session is None:
            return self._hard_block(action, None, "UNKNOWN_SESSION", timer, actor)
        if session.status is not SessionStatus.ACTIVE:
            return self._hard_block(action, session, "SESSION_NOT_ACTIVE", timer, actor)
        with timer.stage("tool_registry"):
            tool = self.store.get_tool(action.tool_name)
        if tool is None:
            return self._hard_block(action, session, "UNREGISTERED_TOOL", timer, actor)

        with timer.stage("cryptographic_verification"):
            crypto_result = self.crypto.verify(action, session, tool)
        if not crypto_result.valid:
            return self._hard_block(action, session, crypto_result.code, timer, actor)

        with timer.stage("policy_evaluation"):
            policy_result = self.policy.evaluate(
                session, action, self.store.list_policies(), tool
            )
        if not policy_result.allowed:
            return self._hard_block(action, session, policy_result.code, timer, actor)

        with timer.stage("intent_alignment"):
            alignment_score, alignment_findings = self.alignment.analyze(session, action, tool)
        with timer.stage("injection_analysis"):
            injection_findings = self.injection.analyze_parameters(action.parameters)
        with timer.stage("behavior_analysis"):
            behavior_findings = self.behavior.analyze(
                action, self.store.recent_activity(action.session_id), tool
            )
        findings = tuple((*alignment_findings, *injection_findings, *behavior_findings))
        with timer.stage("risk_evaluation"):
            assessment = self.risk.assess(
                session.risk_score,
                tool,
                signal_delta=sum(finding.risk_delta for finding in findings),
                signal_reasons=tuple(finding.code for finding in findings),
            )
        reason_code = (
            policy_result.code
            if assessment.outcome is DecisionType.ALLOW
            else assessment.reason_code
        )
        return self._record(
            action,
            session,
            assessment,
            (reason_code,),
            intent_alignment=alignment_score,
            findings=findings,
            timer=timer,
            actor=actor,
        )

    def _hard_block(
        self,
        action: ActionRequest,
        session: Session | None,
        reason_code: str,
        timer: PipelineTimer,
        actor: str | None,
    ) -> ActionVerification:
        with timer.stage("risk_evaluation"):
            assessment = self.risk.hard_block(session.risk_score if session else 0, reason_code)
        return self._record(
            action, session, assessment, (reason_code,), timer=timer, actor=actor
        )

    def _record(
        self,
        action: ActionRequest,
        session: Session | None,
        assessment: RiskAssessment,
        reason_codes: tuple[str, ...],
        *,
        intent_alignment: float | None = None,
        findings: tuple[SecurityFinding, ...] = (),
        timer: PipelineTimer,
        actor: str | None,
    ) -> ActionVerification:
        if (
            assessment.outcome is DecisionType.BLOCK
            and session is not None
            and session.status is SessionStatus.ACTIVE
            and self.store.count_blocks(session.session_id) + 1 >= self.max_blocks_per_session
        ):
            reason_codes = (*reason_codes, TERMINATION_REASON)
            assessment = replace(assessment, reason=f"{assessment.reason}; {TERMINATION_REASON}")
            terminate = True
        else:
            terminate = False
        digest = action_digest(
            session_id=str(action.session_id),
            action_id=str(action.action_id),
            tool_name=action.tool_name,
            parameters=action.parameters,
        )
        approval_id, decision_created = self.store.record_decision(
            action,
            assessment,
            reason_codes,
            redact(action.parameters),
            action_digest=digest,
            approval_ttl_seconds=self.approval_ttl_seconds,
            intent_alignment=intent_alignment,
            findings=findings,
            stage_timings_ms=timer.timings_ms,
            total_latency_ms=timer.elapsed_ms,
            intent_anchor_version=session.anchor_version if session else None,
            intent_anchor_hash=session.intent_anchor_hash if session else None,
            actor=actor,
        )
        if terminate and decision_created and session is not None:
            self.store.revoke_session(session.session_id, reason=TERMINATION_REASON)
        total_latency_ms = timer.elapsed_ms
        if decision_created:
            self.store.update_decision_latency(action.action_id, total_latency_ms)
        return ActionVerification(
            action_id=action.action_id,
            outcome=assessment.outcome.value,
            reason_codes=reason_codes,
            approval_id=approval_id,
            risk_before=assessment.previous,
            risk_delta=assessment.delta,
            risk_after=assessment.current,
            intent_alignment=intent_alignment,
            findings=findings,
            stage_timings_ms=timer.timings_ms,
            total_latency_ms=total_latency_ms,
            action_risk=assessment.action_risk,
            decided_by=assessment.decided_by,
            intent_anchor_version=session.anchor_version if session else None,
        )
