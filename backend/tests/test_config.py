import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_api_prefix_is_normalized() -> None:
    assert Settings(api_prefix="/api/v1/").api_prefix == "/api/v1"


def test_invalid_api_prefix_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(api_prefix="api/v1")
