import argparse
import json
import time
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
from asgp_sdk.client import ASGPClient

from demo.agent import DemoAgent

ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = ROOT / "demo" / "lab_data"


def _post(base_url: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = httpx.post(f"{base_url}{path}", json=payload, timeout=5)
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
        {"name": "read_file", "sensitivity": "low"},
        {"name": "send_mail", "sensitivity": "high"},
        {"name": "upload", "sensitivity": "medium"},
    )
    for tool in tools:
        _post(base_url, "/api/v1/tools/register", tool)
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
    )
    return UUID(session["session_id"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SDK-integrated ASGP demo agent")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    wait_for_api(base_url)
    session_id = prepare_demo(base_url)
    result = DemoAgent(
        session_id=session_id,
        verifier=ASGPClient(base_url),
        lab_root=LAB_ROOT,
    ).run()
    print(json.dumps(result.as_dict(), indent=2))


if __name__ == "__main__":
    main()
