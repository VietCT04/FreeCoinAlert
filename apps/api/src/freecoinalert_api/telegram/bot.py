"""Central Telegram Bot construction for polling and delivery workers."""

from telegram import Bot

from freecoinalert_api.core.config import AuthenticationSettings


def create_telegram_bot(settings: AuthenticationSettings) -> Bot:
    if not settings.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required for Telegram workers.")

    return Bot(
        token=settings.telegram_bot_token,
        base_url=settings.telegram_bot_api_base_url,
        base_file_url=settings.telegram_bot_file_base_url,
    )
