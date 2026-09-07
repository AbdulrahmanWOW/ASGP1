from pathlib import Path
from uuid import UUID

from app.main import create_app
from asgp_sdk.contracts import (
    ActionRequest,
    ContentIngressRequest,
    ContentIngressResult,
    VerificationResult,
)
from fastapi.testclient import TestClient

from demo.agent import DemoAgent


class ClientVerifierAdapter:
    def __init__(self, client: TestClient) -> None:
        self.client = client

    def verify(self, request: ActionRequest) -> VerificationResult:
        response = self.client.post(
            "/api/v1/actions/verify", json=request.model_dump(mode="json")
        )
        response.raise_for_status()
        return VerificationResult.model_validate(response.json())

    def ingest_content(self, request: ContentIngressRequest) -> ContentIngressResult:
        response = self.client.post(
            "/api/v1/content/ingress", json=request.model_dump(mode="json")
        )
        response.raise_for_status()
        return ContentIngressResult.model_validate(response.json())


def test_demo_agent_proves_allow_block_and_escalate(tmp_path: Path) -> None:
    lab_root = tmp_path / "lab"
    (lab_root / "inbox").mkdir(parents=True)
    (lab_root / "inbox" / "legitimate.txt").write_text(
        "Quarterly review is ready.", encoding="utf-8"
    )
    app = create_app(database_url="sqlite+pysqlite:///:memory:", initialize_schema=True)
    with TestClient(app) as client:
        for tool in (
            {"name": "read_file", "sensitivity": "low"},
            {"name": "send_mail", "sensitivity": "high"},
            {"name": "upload", "sensitivity": "medium"},
        ):
            client.post("/api/v1/tools/register", json=tool).raise_for_status()
        session = client.post(
            "/api/v1/sessions",
            json={
                "intent": (
                    "Upload the legitimate note to the internal review destination, "
                    "then read it"
                ),
                "allowed_tools": ["read_file", "upload"],
                "forbidden_tools": ["send_mail"],
                "allowed_paths": [str(lab_root.resolve())],
                "allowed_destinations": ["review.internal"],
            },
        ).json()
        adapter = ClientVerifierAdapter(client)
        run = DemoAgent(
            session_id=UUID(session["session_id"]),
            verifier=adapter,
            content_guard=adapter,
            lab_root=lab_root,
        ).run()
        approvals = client.get("/api/v1/approvals").json()

    assert run.allowed_content == "Quarterly review is ready."
    assert run.blocked is True
    assert run.blocked_tool_executions == 0
    assert run.escalation.outcome.value == "ESCALATE"
    assert len(approvals) == 1
    assert approvals[0]["approval_id"] == str(run.escalation.approval_id)
