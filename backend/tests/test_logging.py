from app.core.logging import redact


def test_redact_handles_nested_sensitive_values() -> None:
    payload = {
        "recipient": "demo@example.test",
        "credentials": {"api_key": "never-log-me", "region": "local"},
        "accessToken": "also-secret",
    }

    assert redact(payload) == {
        "recipient": "demo@example.test",
        "credentials": {"api_key": "[REDACTED]", "region": "local"},
        "accessToken": "[REDACTED]",
    }


def test_redact_bounds_long_content_and_depth() -> None:
    deep: object = "value"
    for _ in range(10):
        deep = {"child": deep}

    assert redact("x" * 300).endswith("[TRUNCATED]")
    assert "MAX_DEPTH" in str(redact(deep))
