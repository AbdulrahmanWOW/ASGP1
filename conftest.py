"""Shared pytest defaults.

Legacy functional tests exercise the pipeline without credentials, so the default test mode
disables authentication. Tests in ``backend/tests/test_auth.py`` and later phases create apps
with ``auth_mode="required"`` explicitly to prove the role checks.
"""

import os

os.environ.setdefault("ASGP_AUTH_MODE", "disabled")
os.environ.setdefault("ASGP_ENVIRONMENT", "test")

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()
