import re
from dataclasses import dataclass
from enum import StrEnum

from telegram import Update

from freecoinalert_api.core.config import AuthenticationSettings

LINK_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}\Z")


class StartCommandKind(StrEnum):
    MISSING_TOKEN = "missing_token"
    INVALID_TOKEN = "invalid_token"
    VALID_LINK = "valid_link"


@dataclass(frozen=True, slots=True)
class StartCommand:
    kind: StartCommandKind
    token: str | None = None


def parse_start_command(
    update: Update,
    *,
    settings: AuthenticationSettings,
) -> StartCommand | None:
    message = update.effective_message

    if message is None or message.chat.type != "private" or message.from_user is None:
        return None

    message_text = message.text

    if message_text is None:
        return None

    command_and_arguments = message_text.split()

    if not command_and_arguments:
        return None

    command = command_and_arguments[0]

    if command == "/start":
        pass
    elif settings.telegram_bot_username is not None and command == (
        f"/start@{settings.telegram_bot_username}"
    ):
        pass
    else:
        return None

    if len(command_and_arguments) == 1:
        return StartCommand(StartCommandKind.MISSING_TOKEN)

    if len(command_and_arguments) != 2:
        return StartCommand(StartCommandKind.INVALID_TOKEN)

    raw_token = command_and_arguments[1]

    if LINK_TOKEN_PATTERN.fullmatch(raw_token) is None:
        return StartCommand(StartCommandKind.INVALID_TOKEN)

    return StartCommand(StartCommandKind.VALID_LINK, token=raw_token)
