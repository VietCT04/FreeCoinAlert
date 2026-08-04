"""Guarded helpers for the isolated end-to-end environment."""

from freecoinalert_api.core.config import AuthenticationSettings, Settings


def require_e2e_mode(settings: AuthenticationSettings | Settings) -> None:
    if not settings.e2e_test_mode:
        raise RuntimeError("E2E-only code requires E2E_TEST_MODE=true.")

    if isinstance(settings, Settings):
        database_name = settings.database_url.split("?", 1)[0].rsplit("/", 1)[-1]
        if not database_name.endswith("_e2e"):
            raise RuntimeError("E2E-only code requires a database name ending in _e2e.")
