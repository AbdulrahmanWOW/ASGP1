from pathlib import Path

from app.db.models import AuditRecord
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy import select


def phase6_app(tmp_path: Path):
    url = f"sqlite+pysqlite:///{(tmp_path / 'phase6.db').as_posix()}"
    return create_app(database_url=url, initialize_schema=True)


def setup_session(client: TestClient) -> str:
    client.post("/api/v1/tools/register", json={"name": "read_message"})
    return client.post(
        "/api/v1/sessions",
        json={"intent": "Read demo messages", "allowed_tools": ["read_message"]},
    ).json()["session_id"]


def create_events(client: TestClient, session_id: str, count: int = 3) -> None:
    for index in range(count):
        response = client.post(
            "/api/v1/actions/verify",
            json={
                "session_id": session_id,
                "tool_name": "read_message",
                "parameters": {"message_id": f"msg-{index}", "api_key": "hidden"},
            },
        )
        assert response.json()["outcome"] == "ALLOW"


def test_valid_chain_and_head_are_verified(tmp_path: Path) -> None:
    app = phase6_app(tmp_path)
    with TestClient(app) as client:
        session_id = setup_session(client)
        create_events(client, session_id)
        events = client.get(f"/api/v1/audit/{session_id}").json()
        result = client.post(f"/api/v1/audit/{session_id}/verify").json()

    assert result["valid"] is True
    assert result["event_count"] == 3
    assert result["errors"] == []
    assert [event["sequence"] for event in events] == [1, 2, 3]
    assert events[0]["previous_hash"] == "0" * 64
    assert events[1]["previous_hash"] == events[0]["entry_hash"]
    assert events[0]["safe_parameters"]["api_key"] == "[REDACTED]"


def test_modifying_interior_event_is_detected(tmp_path: Path) -> None:
    app = phase6_app(tmp_path)
    with TestClient(app) as client:
        session_id = setup_session(client)
        create_events(client, session_id)
        with app.state.services.database.session() as db:
            event = db.scalar(
                select(AuditRecord).where(
                    AuditRecord.session_id == session_id, AuditRecord.sequence == 2
                )
            )
            event.safe_parameters = {"message_id": "tampered"}
            db.commit()
        result = client.post(f"/api/v1/audit/{session_id}/verify").json()

    assert result["valid"] is False
    assert any("Entry hash mismatch" in error for error in result["errors"])


def test_deleting_last_event_is_detected_by_audit_head(tmp_path: Path) -> None:
    app = phase6_app(tmp_path)
    with TestClient(app) as client:
        session_id = setup_session(client)
        create_events(client, session_id)
        with app.state.services.database.session() as db:
            event = db.scalar(
                select(AuditRecord).where(
                    AuditRecord.session_id == session_id, AuditRecord.sequence == 3
                )
            )
            db.delete(event)
            db.commit()
        result = client.post(f"/api/v1/audit/{session_id}/verify").json()

    assert result["valid"] is False
    assert "Audit head event count mismatch" in result["errors"]
    assert "Audit head hash mismatch" in result["errors"]


def test_deleting_interior_event_breaks_sequence_and_link(tmp_path: Path) -> None:
    app = phase6_app(tmp_path)
    with TestClient(app) as client:
        session_id = setup_session(client)
        create_events(client, session_id)
        with app.state.services.database.session() as db:
            event = db.scalar(
                select(AuditRecord).where(
                    AuditRecord.session_id == session_id, AuditRecord.sequence == 2
                )
            )
            db.delete(event)
            db.commit()
        result = client.post(f"/api/v1/audit/{session_id}/verify").json()

    assert result["valid"] is False
    assert any("Sequence gap" in error for error in result["errors"])
    assert any("Previous hash mismatch" in error for error in result["errors"])


def test_pipeline_timings_are_returned_persisted_and_aggregated(tmp_path: Path) -> None:
    app = phase6_app(tmp_path)
    with TestClient(app) as client:
        session_id = setup_session(client)
        decision = client.post(
            "/api/v1/actions/verify",
            json={
                "session_id": session_id,
                "tool_name": "read_message",
                "parameters": {"message_id": "msg-1"},
            },
        ).json()
        audit = client.get(f"/api/v1/audit/{session_id}").json()
        metrics = client.get("/api/v1/metrics/pipeline").json()

    expected_stages = {
        "session_validation",
        "tool_registry",
        "cryptographic_verification",
        "policy_evaluation",
        "intent_alignment",
        "injection_analysis",
        "behavior_analysis",
        "risk_evaluation",
    }
    assert expected_stages <= decision["stage_timings_ms"].keys()
    assert all(value >= 0 for value in decision["stage_timings_ms"].values())
    assert decision["total_latency_ms"] > 0
    assert audit[0]["stage_timings_ms"] == decision["stage_timings_ms"]
    assert metrics["decision_count"] == 1
    assert metrics["average_total_latency_ms"] > 0
    assert expected_stages <= metrics["stage_averages_ms"].keys()
