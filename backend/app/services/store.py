from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.canonical import audit_entry_hash, intent_anchor_digest
from app.db.models import (
    ActionRecord,
    AgentRecord,
    ApprovalRecord,
    AuditHeadRecord,
    AuditRecord,
    DecisionRecord,
    IntentAnchorRecord,
    NonceRecord,
    PolicyRecord,
    RiskChangeRecord,
    SecurityFindingRecord,
    SessionRecord,
    ToolRecord,
)
from app.db.session import Database
from app.domain.actions import ActionRequest
from app.domain.agents import AgentCreate, AgentIdentity, AgentStatus
from app.domain.approvals import Approval, ApprovalResolution, ApprovalStatus
from app.domain.audit import AuditEvent, AuditVerification
from app.domain.decisions import DecisionType
from app.domain.policies import Policy, PolicyCreate
from app.domain.risk import RiskChange
from app.domain.security import FindingKind, FindingSeverity, SecurityFinding
from app.domain.sessions import IntentAnchorUpdate, Session, SessionCreate, SessionStatus
from app.domain.tools import ToolDefinition, ToolSensitivity
from app.services.behavior import Activity
from app.services.risk import RiskAssessment


class VersionConflictError(ValueError):
    pass


class SessionNotFoundError(LookupError):
    pass


class ReplayError(ValueError):
    pass


class DatabaseStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_session(self, request: SessionCreate) -> Session:
        now, session_id = datetime.now(UTC), uuid4()
        with self.database.session() as db:
            session_record = SessionRecord(
                id=str(session_id),
                status=SessionStatus.ACTIVE.value,
                created_at=now,
                risk_score=0,
            )
            db.add(session_record)
            db.flush()
            db.add(self._anchor_record(session_id, 1, request, now))
            db.add(
                AuditHeadRecord(
                    session_id=str(session_id),
                    last_sequence=0,
                    last_hash="0" * 64,
                    event_count=0,
                )
            )
            db.commit()
        result = self.get_session(session_id)
        if result is None:
            raise RuntimeError("Created session could not be loaded")
        return result

    def get_session(self, session_id: UUID) -> Session | None:
        with self.database.session() as db:
            session = db.get(SessionRecord, str(session_id))
            if session is None:
                return None
            anchor = db.scalar(
                select(IntentAnchorRecord)
                .where(IntentAnchorRecord.session_id == str(session_id))
                .order_by(IntentAnchorRecord.version.desc())
                .limit(1)
            )
            if anchor is None:
                raise RuntimeError("Session has no intent anchor")
            return self._to_session(session, anchor)

    def list_sessions(self) -> list[Session]:
        with self.database.session() as db:
            records = db.scalars(
                select(SessionRecord).order_by(SessionRecord.created_at.desc())
            ).all()
            sessions: list[Session] = []
            for record in records:
                anchor = db.scalar(
                    select(IntentAnchorRecord)
                    .where(IntentAnchorRecord.session_id == record.id)
                    .order_by(IntentAnchorRecord.version.desc())
                    .limit(1)
                )
                if anchor is not None:
                    sessions.append(self._to_session(record, anchor))
            return sessions

    def update_intent(self, session_id: UUID, request: IntentAnchorUpdate) -> Session:
        current = self.get_session(session_id)
        if current is None:
            raise SessionNotFoundError(str(session_id))
        if current.anchor_version != request.expected_current_version:
            raise VersionConflictError("Intent anchor version is stale")
        with self.database.session() as db:
            db.add(
                self._anchor_record(
                    session_id, current.anchor_version + 1, request, datetime.now(UTC)
                )
            )
            db.commit()
        result = self.get_session(session_id)
        if result is None:
            raise RuntimeError("Updated session could not be loaded")
        return result

    def revoke_session(self, session_id: UUID) -> Session:
        with self.database.session() as db:
            record = db.get(SessionRecord, str(session_id))
            if record is None:
                raise SessionNotFoundError(str(session_id))
            record.status = SessionStatus.REVOKED.value
            db.commit()
        result = self.get_session(session_id)
        if result is None:
            raise RuntimeError("Revoked session could not be loaded")
        return result

    def register_tool(self, tool: ToolDefinition) -> ToolDefinition:
        with self.database.session() as db:
            record = db.get(ToolRecord, tool.name)
            if record is None:
                db.add(
                    ToolRecord(
                        name=tool.name,
                        description=tool.description,
                        sensitivity=tool.sensitivity.value,
                        requires_signature=tool.requires_signature,
                    )
                )
            else:
                record.description = tool.description
                record.sensitivity = tool.sensitivity.value
                record.requires_signature = tool.requires_signature
            db.commit()
        return tool

    def is_tool_registered(self, name: str) -> bool:
        with self.database.session() as db:
            return db.get(ToolRecord, name) is not None

    def get_tool(self, name: str) -> ToolDefinition | None:
        with self.database.session() as db:
            record = db.get(ToolRecord, name)
            if record is None:
                return None
            return ToolDefinition(
                name=record.name,
                description=record.description,
                sensitivity=ToolSensitivity(record.sensitivity),
                requires_signature=record.requires_signature,
            )

    def create_agent(self, request: AgentCreate) -> AgentIdentity:
        now, agent_id = datetime.now(UTC), uuid4()
        with self.database.session() as db:
            db.add(
                AgentRecord(
                    id=str(agent_id),
                    name=request.name,
                    public_key=request.public_key,
                    status=AgentStatus.ACTIVE.value,
                    last_sequence=0,
                    created_at=now,
                )
            )
            db.commit()
        result = self.get_agent(agent_id)
        if result is None:
            raise RuntimeError("Created agent could not be loaded")
        return result

    def get_agent(self, agent_id: UUID) -> AgentIdentity | None:
        with self.database.session() as db:
            record = db.get(AgentRecord, str(agent_id))
            return self._to_agent(record) if record else None

    def revoke_agent(self, agent_id: UUID) -> AgentIdentity:
        with self.database.session() as db:
            record = db.scalar(
                select(AgentRecord).where(AgentRecord.id == str(agent_id)).with_for_update()
            )
            if record is None:
                raise LookupError("Agent not found")
            record.status = AgentStatus.REVOKED.value
            db.commit()
            return self._to_agent(record)

    def claim_signed_request(
        self,
        *,
        agent_id: UUID,
        nonce: str,
        sequence: int,
        action_id: UUID,
        expires_at: datetime,
    ) -> None:
        with self.database.session() as db:
            agent = db.scalar(
                select(AgentRecord).where(AgentRecord.id == str(agent_id)).with_for_update()
            )
            if agent is None or agent.status != AgentStatus.ACTIVE.value:
                raise ReplayError("Agent is unknown or revoked")
            existing = db.scalar(
                select(NonceRecord).where(
                    NonceRecord.agent_id == str(agent_id),
                    NonceRecord.nonce == nonce,
                )
            )
            if existing is not None:
                raise ReplayError("Nonce was already used")
            if sequence <= agent.last_sequence:
                raise ReplayError("Sequence is not greater than the last accepted sequence")
            agent.last_sequence = sequence
            db.add(
                NonceRecord(
                    id=str(uuid4()),
                    agent_id=str(agent_id),
                    nonce=nonce,
                    action_id=str(action_id),
                    expires_at=expires_at,
                )
            )
            db.commit()

    def create_policy(self, request: PolicyCreate) -> Policy:
        policy = Policy(**request.model_dump())
        with self.database.session() as db:
            db.add(
                PolicyRecord(
                    id=str(policy.policy_id),
                    name=policy.name,
                    enabled=policy.enabled,
                    document=policy.model_dump(mode="json"),
                )
            )
            db.commit()
        return policy

    def list_policies(self) -> list[Policy]:
        with self.database.session() as db:
            records = db.scalars(select(PolicyRecord).order_by(PolicyRecord.name)).all()
            return [Policy.model_validate(record.document) for record in records]

    def record_decision(
        self,
        action: ActionRequest,
        assessment: RiskAssessment,
        reason_codes: tuple[str, ...],
        safe_parameters: dict[str, object],
        *,
        action_digest: str | None = None,
        approval_ttl_seconds: int = 300,
        intent_alignment: float | None = None,
        findings: tuple[SecurityFinding, ...] = (),
        stage_timings_ms: dict[str, float] | None = None,
        total_latency_ms: float = 0,
    ) -> tuple[UUID | None, bool]:
        now = datetime.now(UTC)
        timings = stage_timings_ms or {}
        approval_id = uuid4() if assessment.outcome is DecisionType.ESCALATE else None
        with self.database.session() as db:
            existing_action = db.get(ActionRecord, str(action.action_id))
            if existing_action is None:
                db.add(
                    ActionRecord(
                        id=str(action.action_id),
                        session_id=str(action.session_id),
                        tool_name=action.tool_name,
                        safe_parameters=safe_parameters,
                        created_at=now,
                    )
                )
                db.add(
                    DecisionRecord(
                        id=str(uuid4()),
                        action_id=str(action.action_id),
                        outcome=assessment.outcome.value,
                        reason_codes=list(reason_codes),
                        risk_before=assessment.previous,
                        risk_delta=assessment.delta,
                        risk_after=assessment.current,
                        approval_id=str(approval_id) if approval_id else None,
                        intent_alignment=intent_alignment,
                        stage_timings_ms=timings,
                        total_latency_ms=total_latency_ms,
                        created_at=now,
                    )
                )
            head = db.scalar(
                select(AuditHeadRecord)
                .where(AuditHeadRecord.session_id == str(action.session_id))
                .with_for_update()
            )
            if head is None:
                head = AuditHeadRecord(
                    session_id=str(action.session_id),
                    last_sequence=0,
                    last_hash="0" * 64,
                    event_count=0,
                )
                db.add(head)
                db.flush()
            event_id = uuid4()
            sequence = head.last_sequence + 1
            finding_codes = [finding.code for finding in findings]
            entry_hash = audit_entry_hash(
                event_id=str(event_id),
                action_id=str(action.action_id),
                session_id=str(action.session_id),
                sequence=sequence,
                tool_name=action.tool_name,
                safe_parameters=safe_parameters,
                outcome=assessment.outcome.value,
                reason_codes=list(reason_codes),
                risk_before=assessment.previous,
                risk_after=assessment.current,
                finding_codes=finding_codes,
                stage_timings_ms=timings,
                previous_hash=head.last_hash,
                created_at=now,
            )
            db.add(
                AuditRecord(
                    id=str(event_id),
                    action_id=str(action.action_id),
                    session_id=str(action.session_id),
                    tool_name=action.tool_name,
                    safe_parameters=safe_parameters,
                    outcome=assessment.outcome.value,
                    reason_codes=list(reason_codes),
                    sequence=sequence,
                    previous_hash=head.last_hash,
                    entry_hash=entry_hash,
                    risk_before=assessment.previous,
                    risk_after=assessment.current,
                    finding_codes=finding_codes,
                    stage_timings_ms=timings,
                    created_at=now,
                )
            )
            head.last_sequence = sequence
            head.last_hash = entry_hash
            head.event_count += 1
            db.add(
                RiskChangeRecord(
                    id=str(uuid4()),
                    action_id=str(action.action_id),
                    session_id=str(action.session_id),
                    previous_score=assessment.previous,
                    delta=assessment.delta,
                    new_score=assessment.current,
                    reason=assessment.reason,
                    created_at=now,
                )
            )
            for finding in findings:
                db.add(
                    SecurityFindingRecord(
                        id=str(finding.finding_id),
                        action_id=str(action.action_id),
                        session_id=str(action.session_id),
                        kind=finding.kind.value,
                        code=finding.code,
                        severity=finding.severity.value,
                        confidence=finding.confidence,
                        evidence=finding.evidence,
                        risk_delta=finding.risk_delta,
                        created_at=now,
                    )
                )
            session = db.get(SessionRecord, str(action.session_id))
            if session is not None:
                session.risk_score = assessment.current
            if approval_id is not None and existing_action is None:
                if action_digest is None:
                    raise ValueError("Escalated decisions require an action digest")
                db.add(
                    ApprovalRecord(
                        id=str(approval_id),
                        action_id=str(action.action_id),
                        session_id=str(action.session_id),
                        tool_name=action.tool_name,
                        action_digest=action_digest,
                        status=ApprovalStatus.PENDING.value,
                        expires_at=now + timedelta(seconds=approval_ttl_seconds),
                        created_at=now,
                    )
                )
            db.commit()
        created = existing_action is None
        return (approval_id if created else None, created)

    def list_pending_approvals(self) -> list[Approval]:
        with self.database.session() as db:
            records = db.scalars(
                select(ApprovalRecord).where(ApprovalRecord.status == ApprovalStatus.PENDING.value)
            ).all()
            approvals = [self._refresh_approval(db, record) for record in records]
            db.commit()
            return [
                self._to_approval(record)
                for record in approvals
                if record.status == ApprovalStatus.PENDING.value
            ]

    def update_decision_latency(self, action_id: UUID, total_latency_ms: float) -> None:
        with self.database.session() as db:
            record = db.scalar(
                select(DecisionRecord).where(DecisionRecord.action_id == str(action_id))
            )
            if record is not None:
                record.total_latency_ms = total_latency_ms
                db.commit()

    def get_approval(self, approval_id: UUID) -> Approval | None:
        with self.database.session() as db:
            record = db.get(ApprovalRecord, str(approval_id))
            if record is None:
                return None
            record = self._refresh_approval(db, record)
            db.commit()
            return self._to_approval(record)

    def resolve_approval(self, approval_id: UUID, resolution: ApprovalResolution) -> Approval:
        with self.database.session() as db:
            record = db.scalar(
                select(ApprovalRecord)
                .where(ApprovalRecord.id == str(approval_id))
                .with_for_update()
            )
            if record is None:
                raise LookupError("Approval not found")
            record = self._refresh_approval(db, record)
            if record.status != ApprovalStatus.PENDING.value:
                raise ValueError("Approval is no longer pending")
            record.status = resolution.value
            record.resolved_at = datetime.now(UTC)
            db.commit()
            return self._to_approval(record)

    def consume_approval(self, approval_id: UUID, action_id: UUID) -> Approval:
        with self.database.session() as db:
            record = db.scalar(
                select(ApprovalRecord)
                .where(ApprovalRecord.id == str(approval_id))
                .with_for_update()
            )
            if record is None:
                raise LookupError("Approval not found")
            record = self._refresh_approval(db, record)
            if record.action_id != str(action_id):
                raise ValueError("Approval is bound to another action")
            if record.status != ApprovalStatus.APPROVED.value:
                raise ValueError("Approval is not approved or was already consumed")
            record.status = ApprovalStatus.CONSUMED.value
            db.commit()
            return self._to_approval(record)

    @staticmethod
    def _refresh_approval(db: object, record: ApprovalRecord) -> ApprovalRecord:
        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if record.status == ApprovalStatus.PENDING.value and expires_at <= datetime.now(UTC):
            record.status = ApprovalStatus.EXPIRED.value
        return record

    @staticmethod
    def _to_approval(record: ApprovalRecord) -> Approval:
        return Approval(
            approval_id=UUID(record.id),
            action_id=UUID(record.action_id),
            session_id=UUID(record.session_id),
            tool_name=record.tool_name,
            status=ApprovalStatus(record.status),
            expires_at=record.expires_at,
            created_at=record.created_at,
            resolved_at=record.resolved_at,
        )

    def audit_for_session(self, session_id: UUID) -> list[AuditEvent]:
        with self.database.session() as db:
            records = db.scalars(
                select(AuditRecord)
                .where(AuditRecord.session_id == str(session_id))
                .order_by(AuditRecord.created_at, AuditRecord.id)
            ).all()
            return [
                AuditEvent(
                    event_id=UUID(record.id),
                    action_id=UUID(record.action_id),
                    session_id=UUID(record.session_id),
                    tool_name=record.tool_name,
                    safe_parameters=record.safe_parameters,
                    outcome=DecisionType(record.outcome),
                    reason_codes=tuple(record.reason_codes),
                    sequence=record.sequence,
                    previous_hash=record.previous_hash,
                    entry_hash=record.entry_hash,
                    risk_before=record.risk_before,
                    risk_after=record.risk_after,
                    finding_codes=tuple(record.finding_codes),
                    stage_timings_ms=record.stage_timings_ms,
                    created_at=record.created_at,
                )
                for record in records
            ]

    def verify_audit_chain(self, session_id: UUID) -> AuditVerification:
        events = self.audit_for_session(session_id)
        errors: list[str] = []
        expected_previous = "0" * 64
        expected_sequence = 1
        for event in events:
            if event.sequence != expected_sequence:
                errors.append(f"Sequence gap at event {event.event_id}")
            if event.previous_hash != expected_previous:
                errors.append(f"Previous hash mismatch at event {event.event_id}")
            calculated = audit_entry_hash(
                event_id=str(event.event_id),
                action_id=str(event.action_id),
                session_id=str(event.session_id),
                sequence=event.sequence,
                tool_name=event.tool_name,
                safe_parameters=event.safe_parameters,
                outcome=event.outcome.value,
                reason_codes=list(event.reason_codes),
                risk_before=event.risk_before,
                risk_after=event.risk_after,
                finding_codes=list(event.finding_codes),
                stage_timings_ms=event.stage_timings_ms,
                previous_hash=event.previous_hash,
                created_at=event.created_at,
            )
            if calculated != event.entry_hash:
                errors.append(f"Entry hash mismatch at event {event.event_id}")
            expected_previous = event.entry_hash
            expected_sequence += 1
        with self.database.session() as db:
            head = db.get(AuditHeadRecord, str(session_id))
            if head is None:
                if events:
                    errors.append("Audit head is missing")
                head_count, head_hash = 0, "0" * 64
            else:
                head_count, head_hash = head.event_count, head.last_hash
        if head_count != len(events):
            errors.append("Audit head event count mismatch")
        if head_hash != expected_previous:
            errors.append("Audit head hash mismatch")
        return AuditVerification(
            session_id=session_id,
            valid=not errors,
            event_count=len(events),
            verified_hash=expected_previous,
            errors=tuple(errors),
        )

    def pipeline_metrics(self) -> dict[str, object]:
        with self.database.session() as db:
            records = db.scalars(select(DecisionRecord)).all()
        if not records:
            return {"decision_count": 0, "average_total_latency_ms": 0, "stage_averages_ms": {}}
        stages: dict[str, list[float]] = {}
        for record in records:
            for name, duration in record.stage_timings_ms.items():
                stages.setdefault(name, []).append(duration)
        return {
            "decision_count": len(records),
            "average_total_latency_ms": round(
                sum(record.total_latency_ms for record in records) / len(records), 6
            ),
            "stage_averages_ms": {
                name: round(sum(values) / len(values), 6) for name, values in stages.items()
            },
        }

    def risk_for_session(self, session_id: UUID) -> list[RiskChange]:
        with self.database.session() as db:
            records = db.scalars(
                select(RiskChangeRecord)
                .where(RiskChangeRecord.session_id == str(session_id))
                .order_by(RiskChangeRecord.created_at, RiskChangeRecord.id)
            ).all()
            return [
                RiskChange(
                    action_id=UUID(record.action_id),
                    session_id=UUID(record.session_id),
                    previous_score=record.previous_score,
                    delta=record.delta,
                    new_score=record.new_score,
                    reason=record.reason,
                    created_at=record.created_at,
                )
                for record in records
            ]

    def recent_activity(self, session_id: UUID, limit: int = 20) -> list[Activity]:
        with self.database.session() as db:
            rows = db.execute(
                select(ActionRecord.tool_name, DecisionRecord.outcome)
                .join(DecisionRecord, DecisionRecord.action_id == ActionRecord.id)
                .where(ActionRecord.session_id == str(session_id))
                .order_by(ActionRecord.created_at.desc())
                .limit(limit)
            ).all()
            return [
                Activity(tool_name=row.tool_name, outcome=row.outcome) for row in reversed(rows)
            ]

    def findings_for_session(self, session_id: UUID) -> list[SecurityFinding]:
        with self.database.session() as db:
            records = db.scalars(
                select(SecurityFindingRecord)
                .where(SecurityFindingRecord.session_id == str(session_id))
                .order_by(SecurityFindingRecord.created_at, SecurityFindingRecord.id)
            ).all()
            return [
                SecurityFinding(
                    finding_id=UUID(record.id),
                    kind=FindingKind(record.kind),
                    code=record.code,
                    severity=FindingSeverity(record.severity),
                    confidence=record.confidence,
                    evidence=record.evidence,
                    risk_delta=record.risk_delta,
                )
                for record in records
            ]

    @staticmethod
    def _anchor_record(
        session_id: UUID, version: int, request: SessionCreate, created_at: datetime
    ) -> IntentAnchorRecord:
        allowed_tools = sorted(request.allowed_tools)
        forbidden_tools = sorted(request.forbidden_tools)
        allowed_paths = list(request.allowed_paths)
        allowed_destinations = sorted(request.allowed_destinations)
        return IntentAnchorRecord(
            id=str(uuid4()),
            session_id=str(session_id),
            version=version,
            intent=request.intent,
            allowed_tools=allowed_tools,
            forbidden_tools=forbidden_tools,
            allowed_paths=allowed_paths,
            allowed_destinations=allowed_destinations,
            canonical_hash=intent_anchor_digest(
                session_id=str(session_id),
                version=version,
                intent=request.intent,
                allowed_tools=allowed_tools,
                forbidden_tools=forbidden_tools,
                allowed_paths=allowed_paths,
                allowed_destinations=allowed_destinations,
            ),
            created_at=created_at,
        )

    @staticmethod
    def _to_session(record: SessionRecord, anchor: IntentAnchorRecord) -> Session:
        return Session(
            session_id=UUID(record.id),
            intent=anchor.intent,
            allowed_tools=frozenset(anchor.allowed_tools),
            forbidden_tools=frozenset(anchor.forbidden_tools),
            allowed_paths=tuple(anchor.allowed_paths),
            allowed_destinations=frozenset(anchor.allowed_destinations),
            anchor_version=anchor.version,
            risk_score=record.risk_score,
            intent_anchor_hash=anchor.canonical_hash,
            status=SessionStatus(record.status),
            created_at=record.created_at,
        )

    @staticmethod
    def _to_agent(record: AgentRecord) -> AgentIdentity:
        return AgentIdentity(
            agent_id=UUID(record.id),
            name=record.name,
            public_key=record.public_key,
            status=AgentStatus(record.status),
            last_sequence=record.last_sequence,
            created_at=record.created_at,
        )
