from freecoinalert_api.api.errors import AuthenticationError


class SignalError(AuthenticationError):
    """Safe API error for signal catalog and subscription operations."""
