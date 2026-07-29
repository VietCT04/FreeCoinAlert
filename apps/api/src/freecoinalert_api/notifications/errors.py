from freecoinalert_api.telegram.errors import TelegramError


class NotificationError(TelegramError):
    """Safe API error for notification queue operations."""
