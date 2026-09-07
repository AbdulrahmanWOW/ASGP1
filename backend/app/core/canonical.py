import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def action_digest(*, session_id: str, action_id: str, tool_name: str, parameters: dict) -> str:
    payload = {
        "action_id": action_id,
        "parameters": parameters,
        "session_id": session_id,
        "tool_name": tool_name,
    }
    return hashlib.sha256(canonical_json(payload)).hexdigest()


def intent_anchor_digest(
    *,
    session_id: str,
    version: int,
    intent: str,
    allowed_tools: list[str],
    forbidden_tools: list[str],
    allowed_paths: list[str],
    allowed_destinations: list[str],
) -> str:
    return hashlib.sha256(
        canonical_json(
            {
                "allowed_destinations": sorted(allowed_destinations),
                "allowed_paths": sorted(allowed_paths),
                "allowed_tools": sorted(allowed_tools),
                "forbidden_tools": sorted(forbidden_tools),
                "intent": intent,
                "session_id": session_id,
                "version": version,
            }
        )
    ).hexdigest()


def signed_action_payload(action: object) -> bytes:
    def utc_text(value: object) -> str | None:
        if value is None:
            return None
        return value.isoformat().replace("+00:00", "Z")

    return canonical_json(
        {
            "action_id": str(action.action_id),
            "agent_id": str(action.agent_id),
            "expires_at": utc_text(action.expires_at),
            "intent_anchor_hash": action.intent_anchor_hash,
            "nonce": action.nonce,
            "parameters": action.parameters,
            "scope": action.scope,
            "sequence": action.sequence,
            "session_id": str(action.session_id),
            "timestamp": utc_text(action.timestamp),
            "tool_name": action.tool_name,
        }
    )


def audit_entry_hash(
    *,
    event_id: str,
    action_id: str,
    session_id: str,
    sequence: int,
    tool_name: str,
    safe_parameters: dict,
    outcome: str,
    reason_codes: list[str],
    risk_before: int,
    risk_after: int,
    finding_codes: list[str],
    stage_timings_ms: dict[str, float],
    previous_hash: str,
    created_at: object,
) -> str:
    value = created_at
    if value.tzinfo is None:
        from datetime import UTC

        value = value.replace(tzinfo=UTC)
    timestamp = value.isoformat().replace("+00:00", "Z")
    payload = {
        "action_id": action_id,
        "created_at": timestamp,
        "event_id": event_id,
        "finding_codes": finding_codes,
        "outcome": outcome,
        "previous_hash": previous_hash,
        "reason_codes": reason_codes,
        "risk_after": risk_after,
        "risk_before": risk_before,
        "safe_parameters": safe_parameters,
        "sequence": sequence,
        "session_id": session_id,
        "stage_timings_ms": stage_timings_ms,
        "tool_name": tool_name,
    }
    return hashlib.sha256(canonical_json(payload)).hexdigest()
