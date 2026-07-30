from freecoinalert_api.api.errors import AuthenticationError


class AlertError(AuthenticationError):
    """Safe API error for one-time price alert operations."""
