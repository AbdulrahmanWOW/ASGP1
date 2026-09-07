from pathlib import Path

from app.main import create_app
from fastapi.testclient import TestClient


def database_url(path: Path) -> str:
    return f"sqlite+pysqlite:///{path.as_posix()}"


def test_sessions_tools_actions_decisions_and_audit_survive_restart(tmp_path: Path) -> None:
    url = database_url(tmp_path / "persistent.db")
    first_app = create_app(database_url=url, initialize_schema=True)
    with TestClient(first_app) as client:
        client.post("/api/v1/tools/register", json={"name": "read_message"})
        created = client.post(
            "/api/v1/sessions",
            json={"intent": "Read a demo message", "allowed_tools": ["read_message"]},
        ).json()
        session_id = created["session_id"]
        outcome = client.post(
            "/api/v1/actions/verify",
            json={
                "session_id": session_id,
                "tool_name": "read_message",
                "parameters": {"message_id": "msg-1"},
            },
        ).json()["outcome"]
        assert outcome == "ALLOW"

    second_app = create_app(database_url=url)
    with TestClient(second_app) as client:
        loaded = client.get(f"/api/v1/sessions/{session_id}")
        audit = client.get(f"/api/v1/audit/{session_id}")
        second_outcome = client.post(
            "/api/v1/actions/verify",
            json={
                "session_id": session_id,
                "tool_name": "read_message",
                "parameters": {"message_id": "msg-2"},
            },
        )

    assert loaded.status_code == 200
    assert loaded.json()["anchor_version"] == 1
    assert len(audit.json()) == 1
    assert second_outcome.json()["outcome"] == "ALLOW"


def test_intent_updates_create_versions_and_reject_stale_writes(tmp_path: Path) -> None:
    app = create_app(database_url=database_url(tmp_path / "versions.db"), initialize_schema=True)
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/sessions",
            json={"intent": "Read messages", "allowed_tools": ["read_message"]},
        ).json()
        session_id = created["session_id"]
        update = {
            "intent": "Read messages and write a local summary",
            "allowed_tools": ["read_message", "write_summary"],
            "expected_current_version": 1,
        }
        updated = client.put(f"/api/v1/sessions/{session_id}/intent", json=update)
        stale = client.put(f"/api/v1/sessions/{session_id}/intent", json=update)

    assert updated.status_code == 200
    assert updated.json()["anchor_version"] == 2
    assert stale.status_code == 409


def test_revoked_session_is_durably_blocked(tmp_path: Path) -> None:
    url = database_url(tmp_path / "revoke.db")
    with TestClient(create_app(database_url=url, initialize_schema=True)) as client:
        client.post("/api/v1/tools/register", json={"name": "read_message"})
        session_id = client.post(
            "/api/v1/sessions",
            json={"intent": "Read messages", "allowed_tools": ["read_message"]},
        ).json()["session_id"]
        assert client.post(f"/api/v1/sessions/{session_id}/revoke").json()["status"] == "revoked"

    with TestClient(create_app(database_url=url)) as client:
        decision = client.post(
            "/api/v1/actions/verify",
            json={"session_id": session_id, "tool_name": "read_message", "parameters": {}},
        ).json()

    assert decision["outcome"] == "BLOCK"
    assert decision["reason_codes"] == ["SESSION_NOT_ACTIVE"]
