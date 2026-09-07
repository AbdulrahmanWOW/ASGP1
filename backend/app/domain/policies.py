import re
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PolicyOperator(StrEnum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    IN = "in"
    NOT_IN = "not_in"
    MATCHES = "matches"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"


class PolicyEffect(StrEnum):
    DENY = "deny"


class PolicyRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    field: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]*$")
    operator: PolicyOperator
    value: Any

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: Any, info: Any) -> Any:
        if info.data.get("operator") is PolicyOperator.MATCHES:
            if not isinstance(value, str) or len(value) > 120:
                raise ValueError("matches requires a string pattern of at most 120 characters")
            if re.search(r"\([^)]*[+*][^)]*\)[+*]", value):
                raise ValueError("nested regex quantifiers are not allowed")
            re.compile(value)
        return value


class PolicyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120, pattern=r"^[A-Z][A-Z0-9_]*$")
    effect: PolicyEffect
    tool_name: str | None = Field(default=None, max_length=120)
    rules: tuple[PolicyRule, ...] = Field(min_length=1)
    enabled: bool = True


class Policy(PolicyCreate):
    policy_id: UUID = Field(default_factory=uuid4)
