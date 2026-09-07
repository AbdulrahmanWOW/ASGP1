import logging
import re
from collections.abc import Mapping
from typing import Any

SENSITIVE_KEY_PATTERN = re.compile(
    r"(authorization|api[-_]?key|access[-_]?token|refresh[-_]?token|password|secret|private[-_]?key)",
    re.IGNORECASE,
)


def redact(value: Any, *, _depth: int = 0) -> Any:
    """Create a bounded safe representation for logs and Phase 2 audit storage."""
    if _depth >= 8:
        return "[REDACTED:MAX_DEPTH]"
    if isinstance(value, Mapping):
        return {
            str(key): (
                "[REDACTED]"
                if SENSITIVE_KEY_PATTERN.search(str(key))
                else redact(item, _depth=_depth + 1)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item, _depth=_depth + 1) for item in value[:100]]
    if isinstance(value, tuple):
        return tuple(redact(item, _depth=_depth + 1) for item in value[:100])
    if isinstance(value, str) and len(value) > 256:
        return f"{value[:256]}[TRUNCATED]"
    return value


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
