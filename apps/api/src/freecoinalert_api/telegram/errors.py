from freecoinalert_api.api.errors import AuthenticationError


class TelegramError(AuthenticationError):
    """Safe API error for authenticated Telegram connection operations."""
