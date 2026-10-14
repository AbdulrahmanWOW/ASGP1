import pytest
from app.core.auth import AuthConfig, Role, parse_api_keys
from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient
from pydantic import ValidationError

ADMIN = "admin-key-0123456789abcdef"
USER = "user-key-0123456789abcdef"
AGENT = "agent-key-0123456789abcdef"
KEYS = f"admin:ops:{ADMIN},user:alice:{USER};agent:demo-agent:{AGENT}"


def auth_client() -> TestClient:
    return TestClient(
        create_app(
            database_url="sqlite+pysqlite:///:memory:",
            initialize_schema=True,
            auth_mode="required",
            api_keys=KEYS,
        )
    )


def h(key: str) -> dict[str, str]:
    return {"X-ASGP-Key": key}


def setup_escalation(client: TestClient) -> dict:
    client.post(
        "/api/v1/tools/register",
        json={"name": "send_report", "sensitivity": "medium"},
        headers=h(ADMIN),
    ).raise_for_status()
    session = client.post(
        "/api/v1/sessions",
        json={
            "intent": "Send the approved report",
            "allowed_tools": ["send_report"],
            "allowed_destinations": ["reviewer@example.test"],
        },
        headers=h(USER),
    )
    session.raise_for_status()
    decision = client.post(
        "/api/v1/actions/verify",
        json={
            "session_id": session.json()["session_id"],
            "tool_name": "send_report",
            "parameters": {"recipient": "reviewer@example.test"},
        },
        headers=h(AGENT),
    )
    decision.raise_for_status()
    return decision.json() | {"session_id": session.json()["session_id"]}


def test_key_spec_parsing_and_validation() -> None:
    keys = parse_api_keys(KEYS)
    assert {principal.role for principal in keys.values()} == {Role.ADMIN, Role.USER, Role.AGENT}
    assert all(len(digest) == 64 for digest in keys)  # only digests are stored
    for bad in ("user:alice", "root:x:0123456789abcdef", "user:alice:short"):
        with pytest.raises(ValueError):
            parse_api_keys(bad)
    with pytest.raises(ValueError):
        parse_api_keys(f"user:a:{USER},agent:b:{USER}")


def test_missing_or_wrong_key_is_rejected_but_health_is_public() -> None:
    with auth_client() as client:
        assert client.get("/api/v1/health").status_code == 200
        assert client.get("/api/v1/sessions").status_code == 401
        assert client.get("/api/v1/sessions", headers=h("not-a-real-key-123456")).status_code == 401
        bearer = client.get("/api/v1/sessions", headers={"Authorization": f"Bearer {USER}"})
    assert bearer.status_code == 200


def test_agent_cannot_approve_its_own_escalation_but_user_can() -> None:
    with auth_client() as client:
        decision = setup_escalation(client)
        approval_id = decision["approval_id"]
        by_agent = client.post(
            f"/api/v1/approvals/{approval_id}/resolve",
            json={"resolution": "approved"},
            headers=h(AGENT),
        )
        by_user = client.post(
            f"/api/v1/approvals/{approval_id}/resolve",
            json={"resolution": "approved"},
            headers=h(USER),
        )
        consumed_by_user = client.post(
            f"/api/v1/approvals/{approval_id}/consume",
            json={"action_id": decision["action_id"]},
            headers=h(USER),
        )
        consumed_by_agent = client.post(
            f"/api/v1/approvals/{approval_id}/consume",
            json={"action_id": decision["action_id"]},
            headers=h(AGENT),
        )
        audit = client.get(f"/api/v1/audit/{decision['session_id']}", headers=h(USER)).json()

    assert decision["outcome"] == "ESCALATE"
    assert by_agent.status_code == 403
    assert by_user.status_code == 200
    assert by_user.json()["resolved_by"] == "alice"
    assert consumed_by_user.status_code == 403  # only the agent runtime consumes
    assert consumed_by_agent.json()["status"] == "consumed"
    assert audit[0]["actor"] == "demo-agent"


def test_agent_cannot_change_scope_or_administer() -> None:
    with auth_client() as client:
        decision = setup_escalation(client)
        session_id = decision["session_id"]
        attempts = {
            "create_session": client.post(
                "/api/v1/sessions",
                json={"intent": "anything at all", "allowed_tools": ["send_report"]},
                headers=h(AGENT),
            ),
            "update_intent": client.put(
                f"/api/v1/sessions/{session_id}/intent",
                json={
                    "intent": "send anything anywhere",
                    "allowed_tools": ["send_report"],
                    "allowed_destinations": ["attacker@example.test"],
                    "expected_current_version": 1,
                },
                headers=h(AGENT),
            ),
            "revoke": client.post(f"/api/v1/sessions/{session_id}/revoke", headers=h(AGENT)),
            "register_tool": client.post(
                "/api/v1/tools/register", json={"name": "rm_rf"}, headers=h(AGENT)
            ),
            "create_policy": client.post(
                "/api/v1/policies",
                json={
                    "name": "X_POLICY",
                    "effect": "deny",
                    "rules": [{"field": "a", "operator": "equals", "value": 1}],
                },
                headers=h(AGENT),
            ),
            "list_sessions": client.get("/api/v1/sessions", headers=h(AGENT)),
        }
        user_register = client.post(
            "/api/v1/tools/register", json={"name": "rm_rf"}, headers=h(USER)
        )
        user_verify = client.post(
            "/api/v1/actions/verify",
            json={"session_id": session_id, "tool_name": "send_report", "parameters": {}},
            headers=h(USER),
        )
        agent_reads_own_session = client.get(f"/api/v1/sessions/{session_id}", headers=h(AGENT))

    assert {name: response.status_code for name, response in attempts.items()} == {
        name: 403 for name in attempts
    }
    assert user_register.status_code == 403  # tool registry is admin-only
    assert user_verify.status_code == 403  # humans do not submit tool calls
    assert agent_reads_own_session.status_code == 200


def test_disabled_auth_is_refused_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", auth_mode="disabled")
    assert AuthConfig.from_spec("disabled", "").authenticate(None).role is Role.ADMIN
    assert AuthConfig.from_spec("required", "").authenticate(None) is None
