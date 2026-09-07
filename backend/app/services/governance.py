from app.core.canonical import action_digest
from app.core.logging import redact
from app.domain.actions import ActionRequest, ActionVerification
from app.domain.security import SecurityFinding
from app.domain.sessions import SessionStatus
from app.services.ai import IntentAlignmentService
from app.services.behavior import BehavioralAnalyzer
from app.services.crypto import RequestCryptoVerifier
from app.services.injection import InjectionDetector
from app.services.policy import PermissionPolicy
from app.services.risk import RiskAssessment, RiskEngine
from app.services.store import DatabaseStore
from app.services.timing import PipelineTimer


class GovernanceService:
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
    ) -> None:
        self.store = store
        self.policy = policy
        self.risk = risk
        self.crypto = crypto
        self.alignment = alignment
        self.injection = injection
        self.behavior = behavior
        self.approval_ttl_seconds = approval_ttl_seconds

    def verify(self, action: ActionRequest) -> ActionVerification:
        timer = PipelineTimer()
        with timer.stage("session_validation"):
            session = self.store.get_session(action.session_id)
        if session is None:
            return self._hard_block(action, 0, "UNKNOWN_SESSION", timer)
        if session.status is not SessionStatus.ACTIVE:
            return self._hard_block(action, session.risk_score, "SESSION_NOT_ACTIVE", timer)
        with timer.stage("tool_registry"):
            tool = self.store.get_tool(action.tool_name)
        if tool is None:
            return self._hard_block(action, session.risk_score, "UNREGISTERED_TOOL", timer)

        with timer.stage("cryptographic_verification"):
            crypto_result = self.crypto.verify(action, session, tool)
        if not crypto_result.valid:
            return self._hard_block(action, session.risk_score, crypto_result.code, timer)

        with timer.stage("policy_evaluation"):
            policy_result = self.policy.evaluate(session, action, self.store.list_policies())
        if not policy_result.allowed:
            return self._hard_block(action, session.risk_score, policy_result.code, timer)

        with timer.stage("intent_alignment"):
            alignment_score, alignment_findings = self.alignment.analyze(session, action)
        with timer.stage("injection_analysis"):
            injection_findings = self.injection.analyze_parameters(action.parameters)
        with timer.stage("behavior_analysis"):
            behavior_findings = self.behavior.analyze(
                action, self.store.recent_activity(action.session_id)
            )
        findings = tuple((*alignment_findings, *injection_findings, *behavior_findings))
        with timer.stage("risk_evaluation"):
            assessment = self.risk.assess(
                session.risk_score,
                tool.sensitivity,
                signal_delta=sum(finding.risk_delta for finding in findings),
                signal_reasons=tuple(finding.code for finding in findings),
            )
        reason_code = (
            policy_result.code if assessment.outcome.value == "ALLOW" else assessment.reason_code
        )
        return self._record(
            action,
            assessment,
            reason_code,
            intent_alignment=alignment_score,
            findings=findings,
            timer=timer,
        )

    def _hard_block(
        self,
        action: ActionRequest,
        previous_risk: int,
        reason_code: str,
        timer: PipelineTimer,
    ) -> ActionVerification:
        with timer.stage("risk_evaluation"):
            assessment = self.risk.hard_block(previous_risk, reason_code)
        return self._record(action, assessment, reason_code, timer=timer)

    def _record(
        self,
        action: ActionRequest,
        assessment: RiskAssessment,
        reason_code: str,
        *,
        intent_alignment: float | None = None,
        findings: tuple[SecurityFinding, ...] = (),
        timer: PipelineTimer,
    ) -> ActionVerification:
        digest = action_digest(
            session_id=str(action.session_id),
            action_id=str(action.action_id),
            tool_name=action.tool_name,
            parameters=action.parameters,
        )
        approval_id, decision_created = self.store.record_decision(
            action,
            assessment,
            (reason_code,),
            redact(action.parameters),
            action_digest=digest,
            approval_ttl_seconds=self.approval_ttl_seconds,
            intent_alignment=intent_alignment,
            findings=findings,
            stage_timings_ms=timer.timings_ms,
            total_latency_ms=timer.elapsed_ms,
        )
        total_latency_ms = timer.elapsed_ms
        if decision_created:
            self.store.update_decision_latency(action.action_id, total_latency_ms)
        return ActionVerification(
            action_id=action.action_id,
            outcome=assessment.outcome.value,
            reason_codes=(reason_code,),
            approval_id=approval_id,
            risk_before=assessment.previous,
            risk_delta=assessment.delta,
            risk_after=assessment.current,
            intent_alignment=intent_alignment,
            findings=findings,
            stage_timings_ms=timer.timings_ms,
            total_latency_ms=total_latency_ms,
        )
