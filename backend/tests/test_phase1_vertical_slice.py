import pytest
from app.main import create_app
from asgp_sdk import (
    ActionBlocked,
    ActionRequest,
    VerificationResult,
    protect_tool,
)
from fastapi.testclient import TestClient

from demo.tools import CountedDemoTools


class TestClientVerifier:
    """Connect the real SDK wrapper to the real API without opening a network port."""

    __test__ = False

    def __init__(self, client: TestClient) -> None:
        self.client = client

    def verify(self, request: ActionRequest) -> VerificationResult:
        response = self.client.post("/api/v1/actions/verify", json=request.model_dump(mode="json"))
        response.raise_for_status()
        return VerificationResult.model_validate(response.json())


def test_real_sdk_to_api_vertical_slice_allows_and_blocks_before_execution() -> None:
    app = create_app(database_url="sqlite+pysqlite:///:memory:", initialize_schema=True)
    tools = CountedDemoTools()

    with TestClient(app) as client:
        for name in ("read_message", "send_demo_email"):
            assert (
                client.post(
                    "/api/v1/tools/register", json={"name": name, "description": "Demo"}
                ).status_code
                == 201
            )

        session_response = client.post(
            "/api/v1/sessions",
            json={
                "intent": "Read messages but never send external email",
                "allowed_tools": ["read_message"],
                "forbidden_tools": ["send_demo_email"],
            },
        )
        session_id = session_response.json()["session_id"]
        verifier = TestClientVerifier(client)
        protected_read = protect_tool(
            session_id=session_id, verifier=verifier, name="read_message"
        )(tools.read_message)
        protected_send = protect_tool(
            session_id=session_id, verifier=verifier, name="send_demo_email"
        )(tools.send_demo_email)

        assert protected_read("msg-1") == "Demo message msg-1"
        with pytest.raises(ActionBlocked):
            protected_send("outside@example.test", "sensitive demo content")

        audit = client.get(f"/api/v1/audit/{session_id}").json()

    assert tools.executions == {"read_message": 1}
    assert [event["outcome"] for event in audit] == ["ALLOW", "BLOCK"]
    assert audit[1]["reason_codes"] == ["TOOL_EXPLICITLY_FORBIDDEN"]
