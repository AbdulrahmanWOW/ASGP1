from pathlib import Path

from app.main import create_app
from fastapi.testclient import TestClient


def client_for(tmp_path: Path) -> TestClient:
    url = f"sqlite+pysqlite:///{(tmp_path / 'policies.db').as_posix()}"
    return TestClient(create_app(database_url=url, initialize_schema=True))


def setup_action(
    client: TestClient,
    *,
    allowed_paths: list[str] | None = None,
    allowed_destinations: list[str] | None = None,
) -> str:
    client.post("/api/v1/tools/register", json={"name": "transfer_data"})
    return client.post(
        "/api/v1/sessions",
        json={
            "intent": "Process demo data within approved boundaries",
            "allowed_tools": ["transfer_data"],
            "allowed_paths": allowed_paths or [],
            "allowed_destinations": allowed_destinations or [],
        },
    ).json()["session_id"]


def verify(client: TestClient, session_id: str, parameters: dict) -> dict:
    return client.post(
        "/api/v1/actions/verify",
        json={"session_id": session_id, "tool_name": "transfer_data", "parameters": parameters},
    ).json()


def test_path_and_destination_boundaries(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    with client_for(tmp_path) as client:
        session_id = setup_action(
            client,
            allowed_paths=[str(allowed)],
            allowed_destinations=["approved@example.test"],
        )
        safe = verify(
            client,
            session_id,
            {"path": str(allowed / "summary.txt"), "recipient": "approved@example.test"},
        )
        bad_path = verify(
            client,
            session_id,
            {"path": str(tmp_path / "secret.txt"), "recipient": "approved@example.test"},
        )
        bad_destination = verify(
            client,
            session_id,
            {"path": str(allowed / "summary.txt"), "recipient": "outside@example.test"},
        )

    assert safe["outcome"] == "ALLOW"
    assert bad_path["reason_codes"] == ["PATH_OUTSIDE_BOUNDARY"]
    assert bad_destination["reason_codes"] == ["DESTINATION_OUTSIDE_BOUNDARY"]


def test_structured_deny_policy_is_persisted_and_enforced(tmp_path: Path) -> None:
    with client_for(tmp_path) as client:
        session_id = setup_action(client)
        policy = client.post(
            "/api/v1/policies",
            json={
                "name": "BLOCK_LARGE_TRANSFER",
                "effect": "deny",
                "tool_name": "transfer_data",
                "rules": [{"field": "size_mb", "operator": "greater_than", "value": 10}],
            },
        )
        blocked = verify(client, session_id, {"size_mb": 11})
        allowed = verify(client, session_id, {"size_mb": 5})
        policies = client.get("/api/v1/policies")

    assert policy.status_code == 201
    assert blocked["outcome"] == "BLOCK"
    assert blocked["reason_codes"] == ["POLICY_BLOCK_LARGE_TRANSFER"]
    assert allowed["outcome"] == "ALLOW"
    assert len(policies.json()) == 1


def test_unsafe_or_unknown_policy_shape_is_rejected(tmp_path: Path) -> None:
    with client_for(tmp_path) as client:
        response = client.post(
            "/api/v1/policies",
            json={
                "name": "BAD_REGEX",
                "effect": "deny",
                "rules": [{"field": "recipient", "operator": "matches", "value": "(a+)+"}],
                "unexpected": "not allowed",
            },
        )

    assert response.status_code == 422
