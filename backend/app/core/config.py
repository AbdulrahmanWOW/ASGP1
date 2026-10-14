import os
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

AlignmentProviderName = Literal["lexical", "hashing", "sentence-transformers"]
JudgeName = Literal["none", "ollama"]


class Settings(BaseModel):
    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    api_prefix: str = Field(default="/api/v1", pattern=r"^/[a-zA-Z0-9/_-]+$")
    database_url: str = "postgresql+psycopg://asgp:change-me@127.0.0.1:5432/asgp"
    allowed_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    )
    # Authentication (Phase 1.1)
    auth_mode: Literal["required", "disabled"] = "required"
    api_keys: str = ""
    # Risk / run termination (Phase 1.3)
    max_blocks_per_session: int = Field(default=5, ge=1, le=1000)
    # Hybrid pipeline (Phase 2)
    alignment_provider: AlignmentProviderName = "lexical"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    judge: JudgeName = "none"
    ollama_url: str = "http://127.0.0.1:11434"
    judge_model: str = "qwen2.5:3b"
    judge_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    require_intent_token: bool = False
    intent_signing_key: str = ""
    intent_token_ttl_seconds: int = Field(default=3600, ge=60, le=7 * 24 * 3600)

    @field_validator("api_prefix")
    @classmethod
    def normalize_api_prefix(cls, value: str) -> str:
        return value.rstrip("/")

    @model_validator(mode="after")
    def production_requires_auth(self) -> "Settings":
        if self.environment == "production" and self.auth_mode == "disabled":
            raise ValueError("ASGP_AUTH_MODE=disabled is not allowed in production")
        return self

    @classmethod
    def from_environment(cls) -> "Settings":
        env = os.getenv
        return cls(
            environment=env("ASGP_ENVIRONMENT", "development"),
            log_level=env("ASGP_LOG_LEVEL", "INFO").upper(),
            api_prefix=env("ASGP_API_PREFIX", "/api/v1"),
            database_url=env(
                "ASGP_DATABASE_URL",
                "postgresql+psycopg://asgp:change-me@127.0.0.1:5432/asgp",
            ),
            allowed_origins=tuple(
                origin.strip()
                for origin in env(
                    "ASGP_ALLOWED_ORIGINS",
                    "http://localhost:5173,http://127.0.0.1:5173,"
                    "http://localhost:4173,http://127.0.0.1:4173",
                ).split(",")
                if origin.strip()
            ),
            auth_mode=env("ASGP_AUTH_MODE", "required").lower(),
            api_keys=env("ASGP_API_KEYS", ""),
            max_blocks_per_session=int(env("ASGP_MAX_BLOCKS_PER_SESSION", "5")),
            alignment_provider=env("ASGP_ALIGNMENT_PROVIDER", "lexical").lower(),
            embedding_model=env(
                "ASGP_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
            ),
            judge=env("ASGP_JUDGE", "none").lower(),
            ollama_url=env("ASGP_OLLAMA_URL", "http://127.0.0.1:11434"),
            judge_model=env("ASGP_JUDGE_MODEL", "qwen2.5:3b"),
            judge_timeout_seconds=float(env("ASGP_JUDGE_TIMEOUT_SECONDS", "10")),
            require_intent_token=env("ASGP_REQUIRE_INTENT_TOKEN", "false").lower()
            in {"1", "true", "yes"},
            intent_signing_key=env("ASGP_INTENT_SIGNING_KEY", ""),
            intent_token_ttl_seconds=int(env("ASGP_INTENT_TOKEN_TTL_SECONDS", "3600")),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_environment()
