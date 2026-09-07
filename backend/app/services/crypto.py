import base64
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from sqlalchemy.exc import IntegrityError

from app.core.canonical import signed_action_payload
from app.domain.actions import ActionRequest
from app.domain.agents import AgentStatus
from app.domain.sessions import Session
from app.domain.tools import ToolDefinition
from app.services.store import DatabaseStore, ReplayError


@dataclass(frozen=True)
class CryptoResult:
    valid: bool
    code: str


class RequestCryptoVerifier:
    def __init__(
        self,
        store: DatabaseStore,
        *,
        clock_skew_seconds: int = 30,
        max_lifetime_seconds: int = 300,
    ) -> None:
        self.store = store
        self.clock_skew = timedelta(seconds=clock_skew_seconds)
        self.max_lifetime = timedelta(seconds=max_lifetime_seconds)

    def verify(self, action: ActionRequest, session: Session, tool: ToolDefinition) -> CryptoResult:
        envelope_values = (
            action.agent_id,
            action.intent_anchor_hash,
            action.scope,
            action.timestamp,
            action.expires_at,
            action.nonce,
            action.sequence,
            action.signature,
        )
        if not tool.requires_signature and not any(value is not None for value in envelope_values):
            return CryptoResult(True, "SIGNATURE_NOT_REQUIRED")
        if any(value is None for value in envelope_values):
            return CryptoResult(False, "SIGNATURE_FIELDS_MISSING")

        if action.intent_anchor_hash != session.intent_anchor_hash:
            return CryptoResult(False, "INTENT_ANCHOR_MISMATCH")
        if action.scope != f"tool:{action.tool_name}":
            return CryptoResult(False, "SCOPE_MISMATCH")
        if action.timestamp.tzinfo is None or action.expires_at.tzinfo is None:
            return CryptoResult(False, "NAIVE_TIMESTAMP")
        now = datetime.now(UTC)
        if action.timestamp > now + self.clock_skew:
            return CryptoResult(False, "TIMESTAMP_IN_FUTURE")
        if action.expires_at <= now:
            return CryptoResult(False, "REQUEST_EXPIRED")
        lifetime = action.expires_at - action.timestamp
        if lifetime <= timedelta(0) or lifetime > self.max_lifetime:
            return CryptoResult(False, "INVALID_REQUEST_LIFETIME")

        agent = self.store.get_agent(action.agent_id)
        if agent is None:
            return CryptoResult(False, "UNKNOWN_AGENT")
        if agent.status is not AgentStatus.ACTIVE:
            return CryptoResult(False, "AGENT_REVOKED")
        try:
            public_bytes = base64.b64decode(agent.public_key, validate=True)
            signature = base64.b64decode(action.signature, validate=True)
            Ed25519PublicKey.from_public_bytes(public_bytes).verify(
                signature, signed_action_payload(action)
            )
        except (InvalidSignature, ValueError):
            return CryptoResult(False, "INVALID_SIGNATURE")

        try:
            self.store.claim_signed_request(
                agent_id=action.agent_id,
                nonce=action.nonce,
                sequence=action.sequence,
                action_id=action.action_id,
                expires_at=action.expires_at,
            )
        except (ReplayError, IntegrityError):
            return CryptoResult(False, "REPLAY_DETECTED")
        return CryptoResult(True, "SIGNATURE_VALID")
