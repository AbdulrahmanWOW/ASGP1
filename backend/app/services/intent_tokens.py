"""Signed intent tokens (DESIGN.md §6 step 1, §19 "Intent token").

After a human confirms a scope, the gateway signs ``(session, anchor version, anchor hash,
confirmed_by, expiry, token id)`` with its own Ed25519 key. SDK adapters and the MCP gateway
carry the token on every tool call; the pipeline verifies it before any other rule, so a call
can only be authorized against the exact scope a human confirmed. Anyone holding the public key
can verify a token offline.

Format: ``v1.<base64url(canonical JSON payload)>.<base64url(signature)>``.
"""

import base64
import binascii
import json
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core.canonical import canonical_json
from app.domain.intents import IntentToken
from app.domain.sessions import Session

logger = logging.getLogger(__name__)
VERSION = "v1"


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


@dataclass(frozen=True)
class TokenCheck:
    valid: bool
    code: str


class IntentTokenService:
    def __init__(self, signing_key_b64: str = "", ttl_seconds: int = 3600) -> None:
        if signing_key_b64:
            try:
                seed = base64.b64decode(signing_key_b64, validate=True)
            except (binascii.Error, ValueError) as error:
                raise ValueError("ASGP_INTENT_SIGNING_KEY must be base64") from error
            if len(seed) != 32:
                raise ValueError("ASGP_INTENT_SIGNING_KEY must decode to a 32-byte seed")
            self._key = Ed25519PrivateKey.from_private_bytes(seed)
        else:
            logger.warning(
                "ASGP_INTENT_SIGNING_KEY is not set: using an ephemeral intent signing key. "
                "Issued intent tokens become invalid when the gateway restarts."
            )
            self._key = Ed25519PrivateKey.generate()
        self._public = self._key.public_key()
        self.ttl = timedelta(seconds=ttl_seconds)

    @property
    def public_key_b64(self) -> str:
        raw = self._public.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        return base64.b64encode(raw).decode("ascii")

    def issue(self, session: Session, *, now: datetime | None = None) -> IntentToken:
        issued = now or datetime.now(UTC)
        expires = issued + self.ttl
        payload = {
            "ah": session.intent_anchor_hash,
            "cb": session.confirmed_by,
            "exp": int(expires.timestamp()),
            "iat": int(issued.timestamp()),
            "jti": secrets.token_urlsafe(12),
            "sid": str(session.session_id),
            "ver": session.anchor_version,
        }
        body = canonical_json(payload)
        signature = self._key.sign(VERSION.encode() + b"." + body)
        return IntentToken(
            token=f"{VERSION}.{_b64e(body)}.{_b64e(signature)}",
            session_id=session.session_id,
            anchor_version=session.anchor_version,
            anchor_hash=session.intent_anchor_hash,
            expires_at=datetime.fromtimestamp(payload["exp"], UTC),
            public_key=self.public_key_b64,
        )

    def verify(self, token: str | None, session: Session) -> TokenCheck:
        if not token:
            return TokenCheck(False, "INTENT_TOKEN_MISSING")
        parts = token.split(".")
        if len(parts) != 3 or parts[0] != VERSION:
            return TokenCheck(False, "INTENT_TOKEN_MALFORMED")
        try:
            body, signature = _b64d(parts[1]), _b64d(parts[2])
            self._public.verify(signature, VERSION.encode() + b"." + body)
            payload = json.loads(body)
        except InvalidSignature:
            return TokenCheck(False, "INTENT_TOKEN_INVALID_SIGNATURE")
        except (binascii.Error, ValueError):
            return TokenCheck(False, "INTENT_TOKEN_MALFORMED")
        if not isinstance(payload, dict):
            return TokenCheck(False, "INTENT_TOKEN_MALFORMED")
        if payload.get("sid") != str(session.session_id):
            return TokenCheck(False, "INTENT_TOKEN_SESSION_MISMATCH")
        expires = payload.get("exp")
        if not isinstance(expires, int) or expires <= int(datetime.now(UTC).timestamp()):
            return TokenCheck(False, "INTENT_TOKEN_EXPIRED")
        if (
            payload.get("ver") != session.anchor_version
            or payload.get("ah") != session.intent_anchor_hash
        ):
            return TokenCheck(False, "INTENT_TOKEN_STALE")
        return TokenCheck(True, "INTENT_TOKEN_VALID")
