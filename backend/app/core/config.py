import os
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, field_validator


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

    @field_validator("api_prefix")
    @classmethod
    def normalize_api_prefix(cls, value: str) -> str:
        return value.rstrip("/")

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            environment=os.getenv("ASGP_ENVIRONMENT", "development"),
            log_level=os.getenv("ASGP_LOG_LEVEL", "INFO").upper(),
            api_prefix=os.getenv("ASGP_API_PREFIX", "/api/v1"),
            database_url=os.getenv(
                "ASGP_DATABASE_URL",
                "postgresql+psycopg://asgp:change-me@127.0.0.1:5432/asgp",
            ),
            allowed_origins=tuple(
                origin.strip()
                for origin in os.getenv(
                    "ASGP_ALLOWED_ORIGINS",
                    "http://localhost:5173,http://127.0.0.1:5173,"
                    "http://localhost:4173,http://127.0.0.1:4173",
                ).split(",")
                if origin.strip()
            ),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_environment()
