from dataclasses import replace

from app.core.canonical import action_digest
from app.core.logging import redact
from app.domain.actions import ActionRequest, ActionVerification
from app.domain.decisions import DecisionType
from app.domain.security import FindingKind, FindingSeverity, SecurityFinding
from app.domain.sessions import Session, SessionStatus
from app.domain.tools import ToolDefinition
from app.services.ai import IntentAlignmentService
from app.services.behavior import BehavioralAnalyzer
from app.services.crypto import RequestCryptoVerifier
from app.services.injection import InjectionDetector
from app.services.intent_tokens import IntentTokenService
from app.services.judge import Judge, JudgeRequest
from app.services.policy import PermissionPolicy
from app.services.risk import DecisionLayer, RiskAssessment, RiskEngine
from app.services.store import DatabaseStore
from app.services.timing import PipelineTimer

TERMINATION_REASON = "SESSION_TERMINATED_REPEATED_BLOCKS"


class GovernanceService:
    """Orchestrates the verification pipeline for one proposed tool call.

    Order: session → signed intent token → tool registry → request signature → rules (scope,
    boundaries, policies) → signals (alignment, injection, behavior) → risk score → floors
    (high impact, session) → local LLM judge (gray zone only) → human approval (ESCALATE).
    Hard-rule failures BLOCK and nothing later can override them; the judge can only tighten,
    or relax an ESCALATE to ALLOW for non-high-impact calls in a non-suspicious session.
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
        intent_tokens: IntentTokenService | None = None,
        require_intent_token: bool = False,
        judge: Judge | None = None,
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
        self.intent_tokens = intent_tokens
        self.require_intent_token = require_intent_token
        self.judge = judge

    def verify(self, action: ActionRequest, *, actor: str | None = None) -> ActionVerification:
        timer = PipelineTimer()
        with timer.stage("session_validation"):
            session = self.store.get_session(action.session_id)
        if session is None:
            return self._hard_block(action, None, "UNKNOWN_SESSION", timer, actor)
        if session.status is not SessionStatus.ACTIVE:
            return self._hard_block(action, session, "SESSION_NOT_ACTIVE", timer, actor)
        needs_token = (
            session.requires_intent_token
            or self.require_intent_token
            or action.intent_token is not None
        )
        if needs_token:
            with timer.stage("intent_token"):
                check = (
                    self.intent_tokens.verify(action.intent_token, session)
                    if self.intent_tokens is not None
                    else None
                )
            if check is None or not check.valid:
                code = check.code if check else "INTENT_TOKEN_UNVERIFIABLE"
                return self._hard_block(action, session, code, timer, actor)
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
        reason_codes = (
            (policy_result.code,)
            if assessment.outcome is DecisionType.ALLOW
            else (assessment.reason_code,)
        )
        if assessment.outcome is DecisionType.ESCALATE and self.judge is not None:
            assessment, reason_codes, judge_finding = self._consult_judge(
                session, action, tool, assessment, timer
            )
            findings = (*findings, judge_finding)
        return self._record(
            action,
            session,
            assessment,
            reason_codes,
            intent_alignment=alignment_score,
            findings=findings,
            timer=timer,
            actor=actor,
        )

    def _consult_judge(
        self,
        session: Session,
        action: ActionRequest,
        tool: ToolDefinition,
        assessment: RiskAssessment,
        timer: PipelineTimer,
    ) -> tuple[RiskAssessment, tuple[str, ...], SecurityFinding]:
        request = JudgeRequest(
            intent=session.intent,
            scope={
                "allowed_tools": sorted(session.allowed_tools),
                "forbidden_tools": sorted(session.forbidden_tools),
                "allowed_paths": list(session.allowed_paths),
                "allowed_destinations": sorted(session.allowed_destinations),
            },
            tool={
                "name": tool.name,
                "description": tool.description,
                "category": tool.category.value,
                "sensitivity": tool.sensitivity.value,
                "high_impact": tool.is_high_impact,
            },
            arguments=action.parameters,
            history=self.store.recent_calls(action.session_id),
        )
        try:
            with timer.stage("llm_judge"):
                verdict = self.judge.judge(request)
        except Exception:  # fail closed: any judge failure keeps the human in the loop
            return (
                assessment,
                (assessment.reason_code, "JUDGE_UNAVAILABLE"),
                self._judge_finding(
                    "JUDGE_UNAVAILABLE",
                    FindingSeverity.MEDIUM,
                    "Judge failed or returned invalid output; escalated to a human.",
                ),
            )
        evidence = verdict.reason[:500]
        if verdict.verdict == "block":
            blocked = replace(
                assessment,
                outcome=DecisionType.BLOCK,
                reason_code="JUDGE_BLOCK",
                decided_by=DecisionLayer.JUDGE,
            )
            return (
                blocked,
                ("JUDGE_BLOCK",),
                self._judge_finding("JUDGE_BLOCK", FindingSeverity.HIGH, evidence),
            )
        may_relax = (
            assessment.decided_by == DecisionLayer.SCORE
            and not tool.is_high_impact
            and session.risk_score < self.risk.SESSION_REVIEW_AT
        )
        if verdict.verdict == "allow" and may_relax:
            allowed = replace(
                assessment,
                outcome=DecisionType.ALLOW,
                reason_code="JUDGE_ALLOW",
                decided_by=DecisionLayer.JUDGE,
            )
            return (
                allowed,
                ("JUDGE_ALLOW",),
                self._judge_finding("JUDGE_ALLOW", FindingSeverity.LOW, evidence),
            )
        code = "JUDGE_ALLOW_NOT_PERMITTED" if verdict.verdict == "allow" else "JUDGE_ESCALATE"
        return (
            assessment,
            (assessment.reason_code, code),
            self._judge_finding(code, FindingSeverity.LOW, evidence),
        )

    @staticmethod
    def _judge_finding(code: str, severity: FindingSeverity, evidence: str) -> SecurityFinding:
        return SecurityFinding(
            kind=FindingKind.JUDGE,
            code=code,
            severity=severity,
            confidence=0.5,
            evidence=evidence or "No reason given.",
            risk_delta=0,
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
