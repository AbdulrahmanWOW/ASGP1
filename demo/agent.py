from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

from asgp_sdk.client import Verifier
from asgp_sdk.contracts import ActionRequest, DecisionOutcome, VerificationResult
from asgp_sdk.exceptions import ActionBlocked
from asgp_sdk.tools import protect_tool

from demo.attack_lab import ControlledAttackLab


@dataclass
class DemoRun:
    """Reviewable evidence produced by the SDK-integrated demo agent."""

    allowed_content: str
    blocked: bool
    blocked_tool_executions: int
    escalation: VerificationResult
    events: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed_content": self.allowed_content,
            "blocked": self.blocked,
            "blocked_tool_executions": self.blocked_tool_executions,
            "escalation": self.escalation.model_dump(mode="json"),
            "events": self.events,
        }


class DemoAgent:
    """A tiny deterministic agent proving ASGP sits before real tool execution."""

    def __init__(self, *, session_id: UUID, verifier: Verifier, lab_root: Path) -> None:
        self.session_id = session_id
        self.verifier = verifier
        self.lab = ControlledAttackLab(lab_root)
        self.blocked_tool_executions = 0

        self.read_file = protect_tool(
            session_id=session_id, verifier=verifier, name="read_file"
        )(self.lab.read_file)
        self.send_mail = protect_tool(
            session_id=session_id, verifier=verifier, name="send_mail"
        )(self._counted_send_mail)

    def _counted_send_mail(self, recipient: str, body: str) -> str:
        self.blocked_tool_executions += 1
        return self.lab.send_mail(recipient, body)

    def run(self) -> DemoRun:
        events: list[str] = []
        escalation = self.verifier.verify(
            ActionRequest(
                session_id=self.session_id,
                tool_name="upload",
                parameters={
                    "destination": "review.internal",
                    "relative_path": "inbox/legitimate.txt",
                },
            )
        )
        if escalation.outcome is not DecisionOutcome.ESCALATE:
            raise RuntimeError("The demo upload must produce a reviewable pending approval")
        events.append("ESCALATE: upload paused with an action-bound approval")

        content = self.read_file("inbox/legitimate.txt")
        events.append("ALLOW: read_file executed through the SDK wrapper")

        blocked = False
        try:
            self.send_mail("reviewer@example.test", "This call must remain blocked")
        except ActionBlocked:
            blocked = True
            events.append("BLOCK: send_mail did not reach the underlying tool")
        return DemoRun(
            allowed_content=content,
            blocked=blocked,
            blocked_tool_executions=self.blocked_tool_executions,
            escalation=escalation,
            events=events,
        )
