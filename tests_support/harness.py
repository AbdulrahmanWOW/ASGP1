"""In-process ASGP gateway for adapter tests: real backend pipeline, real auth, no network."""

from pathlib import Path
from typing import Any
from uuid import UUID

from app.main import create_app
from asgp_sdk.contracts import (
    ActionRequest,
    ApprovalResult,
    ApprovalState,
    ContentIngressRequest,
    ContentIngressResult,
    VerificationResult,
)
from asgp_sdk.exceptions import ActionBlocked, VerificationUnavailable
from fastapi.testclient import TestClient

ADMIN = "admin-key-0123456789abcdef"
USER = "user-key-0123456789abcdef"
AGENT = "agent-key-0123456789abcdef"
KEYS = f"admin:ops:{ADMIN},user:alice:{USER},agent:test-agent:{AGENT}"


def h(key: str) -> dict[str, str]:
    return {"X-ASGP-Key": key}


def gateway(tmp_path: Path) -> TestClient:
    url = f"sqlite+pysqlite:///{(tmp_path / 'adapter.db').as_posix()}"
    return TestClient(
        create_app(database_url=url, initialize_schema=True, auth_mode="required", api_keys=KEYS)
    )


class InProcessClient:
    """Same surface as ``asgp_sdk.ASGPClient`` but routed through a TestClient (agent key)."""

    def __init__(self, client: TestClient, *, on_wait: Any = None) -> None:
        self.client = client
        self.on_wait = on_wait  # simulates the human acting while the agent waits

    def verify(self, request: ActionRequest) -> VerificationResult:
        response = self.client.post(
            "/api/v1/actions/verify",
            json=request.model_dump(mode="json", exclude_none=True),
            headers=h(AGENT),
        )
        response.raise_for_status()
        return VerificationResult.model_validate(response.json())

    def get_approval(self, approval_id: UUID) -> ApprovalResult:
        response = self.client.get(f"/api/v1/approvals/{approval_id}", headers=h(AGENT))
        response.raise_for_status()
        return ApprovalResult.model_validate(response.json())

    def consume_approval(self, approval_id: UUID, action_id: UUID) -> None:
        self.client.post(
            f"/api/v1/approvals/{approval_id}/consume",
            json={"action_id": str(action_id)},
            headers=h(AGENT),
        ).raise_for_status()

    def wait_for_approval(self, approval_id: UUID, action_id: UUID, **_: Any) -> None:
        if self.on_wait is not None:
            self.on_wait(approval_id)
        approval = self.get_approval(approval_id)
        if approval.status is ApprovalState.PENDING:
            raise VerificationUnavailable("Approval wait timed out")
        if approval.status is not ApprovalState.APPROVED:
            raise ActionBlocked((f"APPROVAL_{approval.status.value.upper()}",))
        self.consume_approval(approval_id, action_id)

    def ingest_content(self, request: ContentIngressRequest) -> ContentIngressResult:
        response = self.client.post(
            "/api/v1/content/ingress", json=request.model_dump(mode="json"), headers=h(AGENT)
        )
        response.raise_for_status()
        return ContentIngressResult.model_validate(response.json())


def resolve(client: TestClient, approval_id: UUID | str, resolution: str = "approved") -> None:
    client.post(
        f"/api/v1/approvals/{approval_id}/resolve",
        json={"resolution": resolution},
        headers=h(USER),
    ).raise_for_status()


def setup_mail_session(client: TestClient) -> str:
    """read_email (low/read), archive (medium), send_email (high/external, needs approval)."""
    for tool in (
        {"name": "read_email", "category": "read", "description": "Read inbox emails"},
        {"name": "archive_email", "sensitivity": "medium", "category": "write"},
        {"name": "send_email", "sensitivity": "high", "category": "external"},
        {"name": "delete_email", "sensitivity": "high", "category": "delete"},
    ):
        client.post("/api/v1/tools/register", json=tool, headers=h(ADMIN)).raise_for_status()
    response = client.post(
        "/api/v1/sessions",
        json={
            "intent": "Read my latest email and send a short reply to the reviewer",
            "allowed_tools": ["read_email", "archive_email", "send_email"],
            "forbidden_tools": ["delete_email"],
            "allowed_destinations": ["reviewer@example.test"],
        },
        headers=h(USER),
    )
    response.raise_for_status()
    return response.json()["session_id"]
