import base64
import json
import secrets
import threading
from datetime import UTC, datetime, timedelta
from uuid import UUID

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from asgp_sdk.contracts import ActionRequest


def _canonical_payload(action: ActionRequest) -> bytes:
    def utc_text(value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat().replace("+00:00", "Z")

    payload = {
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
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


class Ed25519KeyPair:
    def __init__(self, private_key: Ed25519PrivateKey) -> None:
        self._private_key = private_key

    @classmethod
    def generate(cls) -> "Ed25519KeyPair":
        return cls(Ed25519PrivateKey.generate())

    @property
    def public_key_base64(self) -> str:
        raw = self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return base64.b64encode(raw).decode("ascii")

    def signer(self, agent_id: UUID, *, request_lifetime_seconds: int = 60) -> "ActionSigner":
        return ActionSigner(
            agent_id,
            self._private_key,
            request_lifetime_seconds=request_lifetime_seconds,
        )


class ActionSigner:
    def __init__(
        self,
        agent_id: UUID | str,
        private_key: Ed25519PrivateKey,
        *,
        request_lifetime_seconds: int = 60,
    ) -> None:
        self.agent_id = UUID(str(agent_id))
        self._private_key = private_key
        self._lifetime = timedelta(seconds=request_lifetime_seconds)
        self._sequence = 0
        self._lock = threading.Lock()

    def sign(self, request: ActionRequest, intent_anchor_hash: str) -> ActionRequest:
        with self._lock:
            self._sequence += 1
            sequence = self._sequence
        now = datetime.now(UTC)
        envelope = request.model_copy(
            update={
                "agent_id": self.agent_id,
                "intent_anchor_hash": intent_anchor_hash,
                "scope": f"tool:{request.tool_name}",
                "timestamp": now,
                "expires_at": now + self._lifetime,
                "nonce": secrets.token_urlsafe(24),
                "sequence": sequence,
                "signature": None,
            }
        )
        signature = self._private_key.sign(_canonical_payload(envelope))
        return envelope.model_copy(
            update={"signature": base64.b64encode(signature).decode("ascii")}
        )
