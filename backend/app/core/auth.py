"""API-key authentication with three roles.

Roles
-----
- ``agent``: the integrated AI agent. May verify its own tool calls, submit content for
  scanning, draft intents, read and consume approvals. It can never approve, confirm intent,
  change scope, or administer the gateway.
- ``user``: the human principal (end user / approver). Confirms drafted intents, updates intent,
  resolves approvals, revokes sessions, reads the dashboard data.
- ``admin``: everything, including tool/agent/policy administration.

Keys are configured with ``ASGP_API_KEYS`` as ``role:name:key`` entries separated by commas or
semicolons. Only SHA-256 digests of the keys are kept in memory.
"""

import hashlib
import hmac
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, Request, status

logger = logging.getLogger(__name__)

AuthMode = Literal["required", "disabled"]
API_KEY_HEADER = "X-ASGP-Key"


class Role(StrEnum):
    ADMIN = "admin"
    USER = "user"
    AGENT = "agent"


@dataclass(frozen=True)
class Principal:
    name: str
    role: Role


DEV_PRINCIPAL = Principal(name="auth-disabled", role=Role.ADMIN)


def _digest(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuthConfig:
    mode: AuthMode = "required"
    _keys: dict[str, Principal] = field(default_factory=dict)

    @classmethod
    def from_spec(cls, mode: AuthMode, spec: str | None) -> "AuthConfig":
        return cls(mode=mode, _keys=parse_api_keys(spec or ""))

    @property
    def key_count(self) -> int:
        return len(self._keys)

    def authenticate(self, presented: str | None) -> Principal | None:
        if self.mode == "disabled":
            return DEV_PRINCIPAL
        if not presented:
            return None
        candidate = _digest(presented)
        for stored, principal in self._keys.items():
            if hmac.compare_digest(stored, candidate):
                return principal
        return None


def parse_api_keys(spec: str) -> dict[str, Principal]:
    keys: dict[str, Principal] = {}
    for raw in spec.replace(";", ",").split(","):
        entry = raw.strip()
        if not entry:
            continue
        parts = entry.split(":", 2)
        if len(parts) != 3 or not all(part.strip() for part in parts):
            raise ValueError("ASGP_API_KEYS entries must look like role:name:key")
        role_text, name, key = (part.strip() for part in parts)
        try:
            role = Role(role_text.lower())
        except ValueError as error:
            raise ValueError(f"Unknown API key role: {role_text}") from error
        if len(key) < 16:
            raise ValueError(f"API key for {name} must be at least 16 characters")
        digest = _digest(key)
        if digest in keys:
            raise ValueError("Duplicate API key in ASGP_API_KEYS")
        keys[digest] = Principal(name=name, role=role)
    return keys


def _presented_key(request: Request) -> str | None:
    header = request.headers.get(API_KEY_HEADER)
    if header:
        return header.strip()
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token.strip():
        return token.strip()
    return None


def current_principal(request: Request) -> Principal:
    config: AuthConfig = request.app.state.auth
    principal = config.authenticate(_presented_key(request))
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


def require_roles(*roles: Role) -> Callable[[Principal], Principal]:
    allowed = frozenset(roles) | {Role.ADMIN}

    def dependency(
        principal: Annotated[Principal, Depends(current_principal)],
    ) -> Principal:
        if principal.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{principal.role.value}' may not perform this operation",
            )
        return principal

    return dependency


AdminOnly = Annotated[Principal, Depends(require_roles(Role.ADMIN))]
HumanUser = Annotated[Principal, Depends(require_roles(Role.USER))]
AgentCaller = Annotated[Principal, Depends(require_roles(Role.AGENT))]
AgentOrUser = Annotated[Principal, Depends(require_roles(Role.AGENT, Role.USER))]
