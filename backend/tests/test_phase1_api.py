from app.main import create_app
from fastapi.testclient import TestClient


def make_test_app():
    return create_app(database_url="sqlite+pysqlite:///:memory:", initialize_schema=True)


def register_tool(client: TestClient, name: str) -> None:
    response = client.post(
        "/api/v1/tools/register", json={"name": name, "description": "Test tool"}
    )
    assert response.status_code == 201


def create_session(client: TestClient) -> str:
    response = client.post(
        "/api/v1/sessions",
        json={
            "intent": "Read a message and create a local summary",
            "allowed_tools": ["read_message"],
            "forbidden_tools": ["send_demo_email"],
        },
    )
    assert response.status_code == 201
    return response.json()["session_id"]


def test_allowed_and_blocked_actions_are_audited_and_redacted() -> None:
    with TestClient(make_test_app()) as client:
        register_tool(client, "read_message")
        register_tool(client, "send_demo_email")
        session_id = create_session(client)

        allowed = client.post(
            "/api/v1/actions/verify",
            json={
                "session_id": session_id,
                "tool_name": "read_message",
                "parameters": {"message_id": "msg-1", "api_key": "must-not-persist"},
            },
        )
        blocked = client.post(
            "/api/v1/actions/verify",
            json={
                "session_id": session_id,
                "tool_name": "send_demo_email",
                "parameters": {"recipient": "outside@example.test"},
            },
        )
        audit = client.get(f"/api/v1/audit/{session_id}")

    assert allowed.json()["outcome"] == "ALLOW"
    assert allowed.json()["reason_codes"] == ["TOOL_ALLOWED"]
    assert blocked.json()["outcome"] == "BLOCK"
    assert blocked.json()["reason_codes"] == ["TOOL_EXPLICITLY_FORBIDDEN"]
    events = audit.json()
    assert len(events) == 2
    assert events[0]["safe_parameters"]["api_key"] == "[REDACTED]"


def test_unregistered_tool_fails_closed() -> None:
    with TestClient(make_test_app()) as client:
        session_id = create_session(client)
        response = client.post(
            "/api/v1/actions/verify",
            json={"session_id": session_id, "tool_name": "unknown_tool", "parameters": {}},
        )

    assert response.json()["outcome"] == "BLOCK"
    assert response.json()["reason_codes"] == ["UNREGISTERED_TOOL"]


def test_conflicting_session_permissions_are_rejected() -> None:
    with TestClient(make_test_app()) as client:
        response = client.post(
            "/api/v1/sessions",
            json={
                "intent": "Conflicting permissions must fail",
                "allowed_tools": ["read_message"],
                "forbidden_tools": ["read_message"],
            },
        )

    assert response.status_code == 422


def test_dashboard_can_list_sessions_and_use_local_cors() -> None:
    with TestClient(make_test_app()) as client:
        first_id = create_session(client)
        response = client.get(
            "/api/v1/sessions",
            headers={"Origin": "http://localhost:5173"},
        )

    assert response.status_code == 200
    assert response.json()[0]["session_id"] == first_id
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
