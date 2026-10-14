import argparse
import json
import os
import time
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
from asgp_sdk.client import ASGPClient

from demo.agent import DemoAgent

ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = ROOT / "demo" / "lab_data"


ADMIN_KEY = os.getenv("ASGP_DEMO_ADMIN_KEY")
USER_KEY = os.getenv("ASGP_DEMO_USER_KEY")
AGENT_KEY = os.getenv("ASGP_DEMO_AGENT_KEY")


def _post(
    base_url: str, path: str, payload: dict[str, Any], key: str | None = None
) -> dict[str, Any]:
    headers = {"X-ASGP-Key": key} if key else {}
    response = httpx.post(f"{base_url}{path}", json=payload, headers=headers, timeout=5)
    response.raise_for_status()
    return response.json()


def wait_for_api(base_url: str, timeout_seconds: float = 60) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{base_url}/api/v1/health", timeout=2)
            if response.is_success:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise RuntimeError(f"ASGP API was not ready after {timeout_seconds:.0f} seconds")


def prepare_demo(base_url: str) -> UUID:
    tools = (
        {"name": "read_file", "sensitivity": "low", "category": "read"},
        {"name": "send_mail", "sensitivity": "high", "category": "external"},
        {"name": "upload", "sensitivity": "medium", "category": "external"},
    )
    for tool in tools:
        _post(base_url, "/api/v1/tools/register", tool, ADMIN_KEY)
    session = _post(
        base_url,
        "/api/v1/sessions",
        {
            "intent": (
                "Upload the legitimate demo note to the internal review destination, "
                "then read it"
            ),
            "allowed_tools": ["read_file", "upload"],
            "forbidden_tools": ["send_mail"],
            "allowed_paths": [str(LAB_ROOT.resolve())],
            "allowed_destinations": ["review.internal"],
        },
        USER_KEY,
    )
    return UUID(session["session_id"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SDK-integrated ASGP demo agent")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    wait_for_api(base_url)
    session_id = prepare_demo(base_url)
    client = ASGPClient(base_url, api_key=AGENT_KEY)
    result = DemoAgent(
        session_id=session_id,
        verifier=client,
        content_guard=client,
        lab_root=LAB_ROOT,
    ).run()
    print(json.dumps(result.as_dict(), indent=2))


if __name__ == "__main__":
    main()
