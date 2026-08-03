from dataclasses import dataclass
from enum import StrEnum

from telegram import Bot
from telegram.error import (
    BadRequest,
    Forbidden,
    InvalidToken,
    NetworkError,
    RetryAfter,
    TimedOut,
    TelegramError,
)


class TelegramDeliveryOutcome(StrEnum):
    SENT = "sent"
    PERMANENT_FAILURE = "permanent_failure"
    TEMPORARY_FAILURE = "temporary_failure"
    RATE_LIMITED = "rate_limited"
    NOT_CONFIGURED = "not_configured"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True, slots=True)
class TelegramDeliveryResult:
    outcome: TelegramDeliveryOutcome
    provider_message_id: int | None = None
    retry_after_seconds: int | None = None


class TelegramBotClient:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_link_confirmation(self, *, chat_id: int) -> TelegramDeliveryResult:
        return await self._send_message(
            chat_id=chat_id,
            text="Telegram is connected to FreeCoinAlert. Return to the website to continue.",
        )

    async def send_safe_link_failure(
        self,
        *,
        chat_id: int,
        ownership_conflict: bool,
    ) -> TelegramDeliveryResult:
        text = (
            "Telegram could not be connected with this link. Return to FreeCoinAlert and "
            "review your connection status."
            if ownership_conflict
            else "This connection link is invalid or expired. Return to FreeCoinAlert and "
            "create a new link."
        )
        return await self._send_message(chat_id=chat_id, text=text)

    async def send_missing_link_instruction(self, *, chat_id: int) -> TelegramDeliveryResult:
        return await self._send_message(
            chat_id=chat_id,
            text=(
                "Open FreeCoinAlert in your browser and choose Connect Telegram to create a "
                "secure connection link."
            ),
        )

    async def send_test_notification(self, *, chat_id: int) -> TelegramDeliveryResult:
        return await self._send_message(
            chat_id=chat_id,
            text=(
                "FreeCoinAlert test notification\n\n"
                "Your Telegram connection is working. Cryptocurrency alerts are not enabled yet."
            ),
        )

    async def send_price_alert(
        self,
        *,
        chat_id: int,
        text: str,
    ) -> TelegramDeliveryResult:
        return await self._send_message(chat_id=chat_id, text=text)

    async def send_preset_signal(
        self,
        *,
        chat_id: int,
        text: str,
    ) -> TelegramDeliveryResult:
        return await self._send_message(chat_id=chat_id, text=text)

    async def _send_message(self, *, chat_id: int, text: str) -> TelegramDeliveryResult:
        try:
            message = await self._bot.send_message(chat_id=chat_id, text=text)
        except RetryAfter as error:
            retry_after = error.retry_after
            retry_after_seconds = (
                int(retry_after.total_seconds())
                if hasattr(retry_after, "total_seconds")
                else int(retry_after)
            )
            return TelegramDeliveryResult(
                TelegramDeliveryOutcome.RATE_LIMITED,
                retry_after_seconds=max(1, retry_after_seconds),
            )
        except (BadRequest, Forbidden):
            return TelegramDeliveryResult(TelegramDeliveryOutcome.PERMANENT_FAILURE)
        except InvalidToken:
            return TelegramDeliveryResult(TelegramDeliveryOutcome.NOT_CONFIGURED)
        except (NetworkError, TimedOut):
            return TelegramDeliveryResult(TelegramDeliveryOutcome.UNCERTAIN)
        except TelegramError:
            return TelegramDeliveryResult(TelegramDeliveryOutcome.TEMPORARY_FAILURE)

        return TelegramDeliveryResult(
            TelegramDeliveryOutcome.SENT,
            provider_message_id=message.message_id,
        )
