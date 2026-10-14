"""Gateway configuration (JSON file). Secrets come from environment variables, never the file."""

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class UpstreamServer(BaseModel):
    """An MCP server the gateway fronts. Either a stdio command or a Streamable HTTP URL."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$", max_length=60)
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    url: str | None = None

    @model_validator(mode="after")
    def one_transport(self) -> "UpstreamServer":
        if (self.command is None) == (self.url is None):
            raise ValueError(f"Upstream '{self.name}' needs exactly one of command or url")
        return self


class ToolPolicy(BaseModel):
    """How a tool is registered in ASGP when ``register_tools`` is on."""

    model_config = ConfigDict(extra="forbid")

    sensitivity: Literal["low", "medium", "high", "critical"] = "medium"
    category: Literal["read", "write", "external", "delete", "payment", "admin", "other"] = "other"
    description: str | None = None
    path_parameters: list[str] | None = None
    destination_parameters: list[str] | None = None


class ASGPConnection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_url: str = "http://127.0.0.1:8000"
    session_id: str | None = None
    agent_key_env: str = "ASGP_AGENT_KEY"
    admin_key_env: str = "ASGP_ADMIN_KEY"
    intent_token_env: str = "ASGP_INTENT_TOKEN"
    session_id_env: str = "ASGP_SESSION_ID"
    approval_timeout_seconds: float = Field(default=120, gt=0, le=3600)
    max_blocks: int = Field(default=5, ge=1)
    timeout_seconds: float = Field(default=10, gt=0, le=120)

    def resolved_session_id(self) -> str:
        session_id = os.getenv(self.session_id_env) or self.session_id
        if not session_id:
            raise ValueError(f"Set {self.session_id_env} or asgp.session_id in the config")
        return session_id


class GatewayConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asgp: ASGPConnection = Field(default_factory=ASGPConnection)
    upstreams: list[UpstreamServer] = Field(min_length=1)
    tools: dict[str, ToolPolicy] = Field(default_factory=dict)
    register_tools: bool = False
    scan_results: bool = True

    @model_validator(mode="after")
    def unique_upstreams(self) -> "GatewayConfig":
        names = [upstream.name for upstream in self.upstreams]
        if len(names) != len(set(names)):
            raise ValueError("Upstream names must be unique")
        return self

    @classmethod
    def load(cls, path: str | Path) -> "GatewayConfig":
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
