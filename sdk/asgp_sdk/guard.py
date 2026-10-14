"""Framework-agnostic interception core used by every adapter (DESIGN.md §9).

``ToolGuard`` turns "the agent wants to call tool X with arguments Y" into an ASGP decision and
enforces the rules adapters must not break:

- **Fail closed:** if the gateway is unreachable or answers badly, the decision is BLOCK.
- **Never edit arguments:** the guard only allows a call as-is or refuses it.
- **Decision cache by call ID:** frameworks that re-run interceptors (LangGraph resume) get the
  same decision back instead of a second verification, audit entry and judge call.
- **Repeated blocks end the run:** after ``max_blocks`` blocks, ``RunTerminated`` is raised on
  the next call (repeated blocks usually mean the agent is being steered by an injection).
- **Optional result scanning:** tool output can be passed through content ingress before the
  model sees it; a quarantined or unscannable result is withheld.
"""

import json
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

from asgp_sdk.client import ContentGuard, Verifier
from asgp_sdk.contracts import (
    ActionRequest,
    ApprovalResult,
    ApprovalState,
    ContentDisposition,
    ContentIngressRequest,
    DecisionOutcome,
)
from asgp_sdk.exceptions import ASGPError

BLOCK_PREFIX = "Blocked by ASGP"
ApprovalPoll = Literal["approved", "rejected", "pending"]


class RunTerminated(ASGPError):
    """The run hit the block limit; the agent must stop."""


class ApprovalClient(Protocol):
    def get_approval(self, approval_id: UUID) -> ApprovalResult: ...

    def consume_approval(self, approval_id: UUID, action_id: UUID) -> None: ...

    def wait_for_approval(
        self, approval_id: UUID, action_id: UUID, *, max_wait_seconds: float = ...
    ) -> None: ...


@dataclass(frozen=True)
class GuardDecision:
    outcome: DecisionOutcome
    reason_codes: tuple[str, ...]
    action_id: UUID
    tool_name: str
    approval_id: UUID | None = None
    call_id: str | None = None

    @property
    def allowed(self) -> bool:
        return self.outcome is DecisionOutcome.ALLOW

    @property
    def message(self) -> str:
        return f"{BLOCK_PREFIX}: {', '.join(self.reason_codes) or 'BLOCKED'}"


class ToolGuard:
    def __init__(
        self,
        verifier: Verifier,
        *,
        session_id: UUID | str,
        intent_token: str | None = None,
        content_guard: ContentGuard | None = None,
        max_blocks: int = 5,
        approval_timeout_seconds: float = 300,
    ) -> None:
        self.verifier = verifier
        self.session_id = UUID(str(session_id))
        self.intent_token = intent_token
        self.content_guard = content_guard
        self.max_blocks = max_blocks
        self.approval_timeout_seconds = approval_timeout_seconds
        self.blocks = 0
        self._cache: dict[str, GuardDecision] = {}
        self._lock = threading.Lock()

    @property
    def terminated(self) -> bool:
        return self.blocks >= self.max_blocks

    def ensure_running(self) -> None:
        if self.terminated:
            raise RunTerminated(f"ASGP stopped this run after {self.blocks} blocked tool calls")

    def check(
        self, tool_name: str, arguments: Mapping[str, Any] | None, *, call_id: str | None = None
    ) -> GuardDecision:
        """Return the gateway decision for one proposed call (cached per call ID)."""
        if call_id is not None:
            with self._lock:
                cached = self._cache.get(call_id)
            if cached is not None:
                return cached
        self.ensure_running()
        action_id = uuid4()
        try:
            parameters = json.loads(json.dumps(dict(arguments or {}), default=str))
            result = self.verifier.verify(
                ActionRequest(
                    action_id=action_id,
                    session_id=self.session_id,
                    tool_name=tool_name,
                    parameters=parameters,
                    intent_token=self.intent_token,
                )
            )
            decision = GuardDecision(
                outcome=result.outcome,
                reason_codes=result.reason_codes,
                action_id=result.action_id,
                tool_name=tool_name,
                approval_id=result.approval_id,
                call_id=call_id,
            )
        except Exception:  # fail closed on any verification problem
            decision = GuardDecision(
                outcome=DecisionOutcome.BLOCK,
                reason_codes=("ASGP_UNAVAILABLE",),
                action_id=action_id,
                tool_name=tool_name,
                call_id=call_id,
            )
        if decision.outcome is DecisionOutcome.BLOCK:
            with self._lock:
                self.blocks += 1
        if call_id is not None:
            with self._lock:
                self._cache[call_id] = decision
        return decision

    # --- approvals --------------------------------------------------------------------

    def wait_for_approval(self, decision: GuardDecision) -> bool:
        """Block until a human resolves the approval. True only if approved and consumed."""
        waiter = getattr(self.verifier, "wait_for_approval", None)
        if decision.approval_id is None or waiter is None:
            return False
        try:
            waiter(
                decision.approval_id,
                decision.action_id,
                max_wait_seconds=self.approval_timeout_seconds,
            )
        except Exception:  # rejected, expired, timeout or gateway failure -> do not run
            return False
        return True

    def poll_approval(self, decision: GuardDecision) -> ApprovalPoll:
        """One non-blocking look at the approval; consumes it if approved."""
        getter = getattr(self.verifier, "get_approval", None)
        consumer = getattr(self.verifier, "consume_approval", None)
        if decision.approval_id is None or getter is None or consumer is None:
            return "rejected"
        try:
            approval = getter(decision.approval_id)
            if approval.action_id != decision.action_id:
                return "rejected"
            if approval.status is ApprovalState.PENDING:
                return "pending"
            if approval.status is not ApprovalState.APPROVED:
                return "rejected"
            consumer(decision.approval_id, decision.action_id)
        except Exception:
            return "rejected"
        return "approved"

    # --- results ----------------------------------------------------------------------

    def scan_result(self, text: str, *, source: str) -> str:
        if self.content_guard is None or not text:
            return text
        try:
            result = self.content_guard.ingest_content(
                ContentIngressRequest(
                    session_id=self.session_id, content=text[:100_000], source=source[:120]
                )
            )
        except Exception:
            return "[ASGP withheld this tool output: content scanning unavailable]"
        if result.disposition is ContentDisposition.QUARANTINED or result.safe_content is None:
            codes = ", ".join(finding.code for finding in result.findings) or "SUSPICIOUS"
            return f"[ASGP quarantined this tool output: {codes}]"
        return result.safe_content
