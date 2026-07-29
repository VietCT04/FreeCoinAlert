from dataclasses import dataclass
from enum import StrEnum

from telegram import Bot
from telegram.error import BadRequest, Forbidden, NetworkError, TimedOut, TelegramError


class TelegramDeliveryOutcome(StrEnum):
    SENT = "sent"
    REJECTED = "rejected"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True, slots=True)
class TelegramDeliveryResult:
    outcome: TelegramDeliveryOutcome


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

    async def _send_message(self, *, chat_id: int, text: str) -> TelegramDeliveryResult:
        try:
            await self._bot.send_message(chat_id=chat_id, text=text)
        except (BadRequest, Forbidden):
            return TelegramDeliveryResult(TelegramDeliveryOutcome.REJECTED)
        except (NetworkError, TimedOut):
            return TelegramDeliveryResult(TelegramDeliveryOutcome.UNCERTAIN)
        except TelegramError:
            return TelegramDeliveryResult(TelegramDeliveryOutcome.REJECTED)

        return TelegramDeliveryResult(TelegramDeliveryOutcome.SENT)
