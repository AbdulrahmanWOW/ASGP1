from pathlib import Path

from app.main import create_app
from asgp_sdk import ActionRequest, Ed25519KeyPair
from fastapi.testclient import TestClient


def phase4_client(tmp_path: Path) -> TestClient:
    url = f"sqlite+pysqlite:///{(tmp_path / 'phase4.db').as_posix()}"
    return TestClient(create_app(database_url=url, initialize_schema=True))


def setup_identity(client: TestClient):
    keys = Ed25519KeyPair.generate()
    agent = client.post(
        "/api/v1/agents",
        json={"name": "demo-agent", "public_key": keys.public_key_base64},
    ).json()
    client.post(
        "/api/v1/tools/register",
        json={"name": "read_message", "requires_signature": True},
    )
    session = client.post(
        "/api/v1/sessions",
        json={"intent": "Read demo messages", "allowed_tools": ["read_message"]},
    ).json()
    signer = keys.signer(agent_id=agent["agent_id"])
    return agent, session, signer


def signed_action(session: dict, signer, *, message_id: str = "msg-1") -> ActionRequest:
    request = ActionRequest(
        session_id=session["session_id"],
        tool_name="read_message",
        parameters={"message_id": message_id},
    )
    return signer.sign(request, session["intent_anchor_hash"])


def submit(client: TestClient, action: ActionRequest) -> dict:
    response = client.post("/api/v1/actions/verify", json=action.model_dump(mode="json"))
    assert response.status_code == 200
    return response.json()


def test_valid_ed25519_request_is_allowed(tmp_path: Path) -> None:
    with phase4_client(tmp_path) as client:
        agent, session, signer = setup_identity(client)
        decision = submit(client, signed_action(session, signer))
        stored_agent = client.get(f"/api/v1/agents/{agent['agent_id']}").json()

    assert decision["outcome"] == "ALLOW"
    assert stored_agent["last_sequence"] == 1


def test_missing_signature_and_modified_payload_fail_closed(tmp_path: Path) -> None:
    with phase4_client(tmp_path) as client:
        _, session, signer = setup_identity(client)
        unsigned = ActionRequest(
            session_id=session["session_id"],
            tool_name="read_message",
            parameters={"message_id": "msg-1"},
        )
        missing = submit(client, unsigned)
        signed = signed_action(session, signer)
        tampered = signed.model_copy(update={"parameters": {"message_id": "secret-message"}})
        modified = submit(client, tampered)

    assert missing["reason_codes"] == ["SIGNATURE_FIELDS_MISSING"]
    assert modified["reason_codes"] == ["INVALID_SIGNATURE"]


def test_exact_replay_and_old_sequence_are_blocked(tmp_path: Path) -> None:
    with phase4_client(tmp_path) as client:
        _, session, signer = setup_identity(client)
        first = signed_action(session, signer, message_id="first")
        second = signed_action(session, signer, message_id="second")
        assert submit(client, second)["outcome"] == "ALLOW"
        old_sequence = submit(client, first)
        exact_replay = submit(client, second)

    assert old_sequence["reason_codes"] == ["REPLAY_DETECTED"]
    assert exact_replay["reason_codes"] == ["REPLAY_DETECTED"]


def test_expired_scope_and_stale_anchor_are_blocked(tmp_path: Path) -> None:
    with phase4_client(tmp_path) as client:
        _, session, signer = setup_identity(client)
        expired_signer = Ed25519KeyPair.generate()
        other_agent = client.post(
            "/api/v1/agents",
            json={"name": "expired-agent", "public_key": expired_signer.public_key_base64},
        ).json()
        expired = expired_signer.signer(
            agent_id=other_agent["agent_id"], request_lifetime_seconds=-1
        ).sign(
            ActionRequest(
                session_id=session["session_id"],
                tool_name="read_message",
                parameters={},
            ),
            session["intent_anchor_hash"],
        )
        expired_result = submit(client, expired)

        bad_scope = signed_action(session, signer).model_copy(update={"scope": "tool:send_email"})
        scope_result = submit(client, bad_scope)

        old_anchor_action = signed_action(session, signer)
        update = client.put(
            f"/api/v1/sessions/{session['session_id']}/intent",
            json={
                "intent": "Read selected demo messages",
                "allowed_tools": ["read_message"],
                "expected_current_version": 1,
            },
        )
        assert update.status_code == 200
        stale_result = submit(client, old_anchor_action)

    assert expired_result["reason_codes"] == ["REQUEST_EXPIRED"]
    assert scope_result["reason_codes"] == ["SCOPE_MISMATCH"]
    assert stale_result["reason_codes"] == ["INTENT_ANCHOR_MISMATCH"]


def test_revoked_agent_cannot_sign_new_actions(tmp_path: Path) -> None:
    with phase4_client(tmp_path) as client:
        agent, session, signer = setup_identity(client)
        client.post(f"/api/v1/agents/{agent['agent_id']}/revoke")
        result = submit(client, signed_action(session, signer))

    assert result["outcome"] == "BLOCK"
    assert result["reason_codes"] == ["AGENT_REVOKED"]


def test_invalid_public_key_is_rejected(tmp_path: Path) -> None:
    with phase4_client(tmp_path) as client:
        result = client.post(
            "/api/v1/agents",
            json={"name": "invalid-agent", "public_key": "not-a-public-key"},
        )

    assert result.status_code == 422
