from pathlib import Path
from uuid import uuid4

from app.main import create_app
from fastapi.testclient import TestClient


def phase3_client(tmp_path: Path, *, ttl: int = 300) -> TestClient:
    url = f"sqlite+pysqlite:///{(tmp_path / f'phase3-{ttl}.db').as_posix()}"
    return TestClient(
        create_app(
            database_url=url,
            initialize_schema=True,
            approval_ttl_seconds=ttl,
        )
    )


def setup_medium_action(client: TestClient) -> tuple[str, dict]:
    client.post(
        "/api/v1/tools/register",
        json={"name": "send_report", "sensitivity": "medium"},
    )
    session_id = client.post(
        "/api/v1/sessions",
        json={
            "intent": "Prepare and send an approved report",
            "allowed_tools": ["send_report"],
            "allowed_destinations": ["reviewer@example.test", "another@example.test"],
        },
    ).json()["session_id"]
    decision = client.post(
        "/api/v1/actions/verify",
        json={
            "session_id": session_id,
            "tool_name": "send_report",
            "parameters": {"recipient": "reviewer@example.test"},
        },
    ).json()
    return session_id, decision


def test_medium_risk_escalates_and_records_explainable_change(tmp_path: Path) -> None:
    with phase3_client(tmp_path) as client:
        session_id, decision = setup_medium_action(client)
        pending = client.get("/api/v1/approvals").json()
        risk = client.get(f"/api/v1/risk/{session_id}").json()

    assert decision["outcome"] == "ESCALATE"
    assert decision["action_risk"] == 40
    assert decision["decided_by"] == "score"
    # Session suspicion only grows from findings / hard blocks, not from tool sensitivity.
    assert decision["risk_before"] == 0
    assert decision["risk_delta"] == 0
    assert decision["risk_after"] == 0
    assert decision["approval_id"] is not None
    assert len(pending) == 1
    assert pending[0]["reason_codes"] == ["RISK_THRESHOLD_ESCALATE"]
    assert risk[0]["previous_score"] == 0
    assert risk[0]["delta"] == 0
    assert risk[0]["new_score"] == 0
    assert risk[0]["reason"] == "Tool sensitivity is medium (base 40)"


def test_approved_action_is_consumed_once_and_bound_to_action(tmp_path: Path) -> None:
    with phase3_client(tmp_path) as client:
        _, decision = setup_medium_action(client)
        approval_id = decision["approval_id"]
        action_id = decision["action_id"]
        resolved = client.post(
            f"/api/v1/approvals/{approval_id}/resolve",
            json={"resolution": "approved"},
        )
        wrong = client.post(
            f"/api/v1/approvals/{approval_id}/consume",
            json={"action_id": str(uuid4())},
        )
        consumed = client.post(
            f"/api/v1/approvals/{approval_id}/consume",
            json={"action_id": action_id},
        )
        reused = client.post(
            f"/api/v1/approvals/{approval_id}/consume",
            json={"action_id": action_id},
        )

    assert resolved.json()["status"] == "approved"
    assert wrong.status_code == 409
    assert consumed.json()["status"] == "consumed"
    assert reused.status_code == 409


def test_rejected_and_expired_approvals_cannot_be_consumed(tmp_path: Path) -> None:
    with phase3_client(tmp_path) as client:
        _, rejected_decision = setup_medium_action(client)
        rejected_id = rejected_decision["approval_id"]
        client.post(
            f"/api/v1/approvals/{rejected_id}/resolve",
            json={"resolution": "rejected"},
        )
        rejected_consume = client.post(
            f"/api/v1/approvals/{rejected_id}/consume",
            json={"action_id": rejected_decision["action_id"]},
        )
    assert rejected_consume.status_code == 409

    with phase3_client(tmp_path, ttl=-1) as client:
        _, expired_decision = setup_medium_action(client)
        expired_id = expired_decision["approval_id"]
        expired = client.get(f"/api/v1/approvals/{expired_id}")
        resolve_expired = client.post(
            f"/api/v1/approvals/{expired_id}/resolve",
            json={"resolution": "approved"},
        )
    assert expired.json()["status"] == "expired"
    assert resolve_expired.status_code == 409


def test_hard_policy_block_has_priority_over_medium_risk(tmp_path: Path) -> None:
    with phase3_client(tmp_path) as client:
        client.post(
            "/api/v1/tools/register",
            json={"name": "send_report", "sensitivity": "medium"},
        )
        session_id = client.post(
            "/api/v1/sessions",
            json={
                "intent": "Never send reports",
                "allowed_tools": ["read_message"],
                "forbidden_tools": ["send_report"],
            },
        ).json()["session_id"]
        decision = client.post(
            "/api/v1/actions/verify",
            json={"session_id": session_id, "tool_name": "send_report", "parameters": {}},
        ).json()

    assert decision["outcome"] == "BLOCK"
    assert decision["reason_codes"] == ["TOOL_EXPLICITLY_FORBIDDEN"]
    assert decision["approval_id"] is None


def test_repeated_medium_actions_escalate_without_session_poisoning(tmp_path: Path) -> None:
    """A second clean medium call still reaches a human instead of being blocked."""
    with phase3_client(tmp_path) as client:
        session_id, first = setup_medium_action(client)
        second = client.post(
            "/api/v1/actions/verify",
            json={
                "session_id": session_id,
                "tool_name": "send_report",
                "parameters": {"recipient": "another@example.test"},
            },
        ).json()

    assert first["outcome"] == "ESCALATE"
    assert second["outcome"] == "ESCALATE"
    assert second["risk_before"] == 0
    assert second["risk_after"] == 0
    assert second["action_risk"] == 40
    assert second["approval_id"] is not None
