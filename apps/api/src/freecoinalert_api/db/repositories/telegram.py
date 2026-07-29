import uuid
from datetime import datetime

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.telegram_connection import TelegramConnection
from freecoinalert_api.db.models.telegram_link_token import TelegramLinkToken
from freecoinalert_api.db.models.telegram_processed_update import TelegramProcessedUpdate


async def get_telegram_connection_by_user_id(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    for_update: bool = False,
) -> TelegramConnection | None:
    statement = select(TelegramConnection).where(
        TelegramConnection.user_id == user_id,
    )

    if for_update:
        statement = statement.with_for_update()

    return await session.scalar(statement)


async def get_telegram_connection_by_identifiers(
    session: AsyncSession,
    *,
    telegram_user_id: int,
    telegram_chat_id: int,
    for_update: bool = False,
) -> TelegramConnection | None:
    statement = select(TelegramConnection).where(
        or_(
            TelegramConnection.telegram_user_id == telegram_user_id,
            TelegramConnection.telegram_chat_id == telegram_chat_id,
        ),
    )

    if for_update:
        statement = statement.with_for_update()

    return await session.scalar(statement)


async def create_telegram_connection(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    telegram_user_id: int,
    telegram_chat_id: int,
    telegram_username: str | None,
    connected_at: datetime,
    last_verified_at: datetime,
) -> TelegramConnection:
    telegram_connection = TelegramConnection(
        user_id=user_id,
        telegram_user_id=telegram_user_id,
        telegram_chat_id=telegram_chat_id,
        telegram_username=telegram_username,
        status="connected",
        connected_at=connected_at,
        last_verified_at=last_verified_at,
    )
    session.add(telegram_connection)
    await session.flush()
    return telegram_connection


async def reactivate_telegram_connection(
    session: AsyncSession,
    *,
    connection_id: uuid.UUID,
    connected_at: datetime,
    last_verified_at: datetime,
    telegram_username: str | None,
) -> TelegramConnection | None:
    telegram_connection = await session.get(TelegramConnection, connection_id)

    if telegram_connection is None:
        return None

    telegram_connection.status = "connected"
    telegram_connection.connected_at = connected_at
    telegram_connection.last_verified_at = last_verified_at
    telegram_connection.telegram_username = telegram_username
    telegram_connection.degraded_at = None
    telegram_connection.disconnected_at = None
    telegram_connection.status_reason = None
    await session.flush()
    return telegram_connection


async def mark_telegram_connection_degraded(
    session: AsyncSession,
    *,
    connection_id: uuid.UUID,
    degraded_at: datetime,
    status_reason: str,
) -> TelegramConnection | None:
    telegram_connection = await session.get(TelegramConnection, connection_id)

    if telegram_connection is None:
        return None

    telegram_connection.status = "degraded"
    telegram_connection.degraded_at = degraded_at
    telegram_connection.status_reason = status_reason
    await session.flush()
    return telegram_connection


async def mark_telegram_connection_disconnected(
    session: AsyncSession,
    *,
    connection_id: uuid.UUID,
    disconnected_at: datetime,
    status_reason: str | None,
) -> TelegramConnection | None:
    telegram_connection = await session.get(TelegramConnection, connection_id)

    if telegram_connection is None:
        return None

    telegram_connection.status = "disconnected"
    telegram_connection.degraded_at = None
    telegram_connection.disconnected_at = disconnected_at
    telegram_connection.status_reason = status_reason
    await session.flush()
    return telegram_connection


async def create_telegram_link_token(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    token_hash: bytes,
    expires_at: datetime,
) -> TelegramLinkToken:
    telegram_link_token = TelegramLinkToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(telegram_link_token)
    await session.flush()
    return telegram_link_token


async def get_active_telegram_link_token_for_update(
    session: AsyncSession,
    *,
    token_hash: bytes,
    current_time: datetime,
    for_update: bool = False,
) -> TelegramLinkToken | None:
    statement = select(TelegramLinkToken).where(
        TelegramLinkToken.token_hash == token_hash,
        TelegramLinkToken.consumed_at.is_(None),
        TelegramLinkToken.revoked_at.is_(None),
        TelegramLinkToken.expires_at > current_time,
    )

    if for_update:
        statement = statement.with_for_update()

    return await session.scalar(statement)


async def get_active_telegram_link_token_by_user_id(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    current_time: datetime,
) -> TelegramLinkToken | None:
    statement = select(TelegramLinkToken).where(
        TelegramLinkToken.user_id == user_id,
        TelegramLinkToken.consumed_at.is_(None),
        TelegramLinkToken.revoked_at.is_(None),
        TelegramLinkToken.expires_at > current_time,
    )
    return await session.scalar(statement)


async def revoke_outstanding_telegram_link_tokens(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    revoked_at: datetime,
) -> int:
    statement = (
        update(TelegramLinkToken)
        .where(
            TelegramLinkToken.user_id == user_id,
            TelegramLinkToken.consumed_at.is_(None),
            TelegramLinkToken.revoked_at.is_(None),
        )
        .values(revoked_at=revoked_at)
    )
    result = await session.execute(statement)
    return result.rowcount


async def consume_telegram_link_token(
    session: AsyncSession,
    *,
    token_id: uuid.UUID,
    consumed_at: datetime,
) -> TelegramLinkToken | None:
    telegram_link_token = await session.get(TelegramLinkToken, token_id)

    if telegram_link_token is None:
        return None

    telegram_link_token.consumed_at = consumed_at
    await session.flush()
    return telegram_link_token


async def record_processed_telegram_update(
    session: AsyncSession,
    *,
    update_id: int,
    outcome: str,
    connection_id: uuid.UUID | None,
    received_at: datetime,
    processed_at: datetime,
) -> TelegramProcessedUpdate:
    telegram_processed_update = TelegramProcessedUpdate(
        update_id=update_id,
        outcome=outcome,
        connection_id=connection_id,
        received_at=received_at,
        processed_at=processed_at,
    )
    session.add(telegram_processed_update)
    await session.flush()
    return telegram_processed_update


async def get_processed_telegram_update(
    session: AsyncSession,
    *,
    update_id: int,
    for_update: bool = False,
) -> TelegramProcessedUpdate | None:
    statement = select(TelegramProcessedUpdate).where(
        TelegramProcessedUpdate.update_id == update_id,
    )

    if for_update:
        statement = statement.with_for_update()

    return await session.scalar(statement)


async def delete_processed_telegram_updates_before(
    session: AsyncSession,
    *,
    cutoff: datetime,
) -> int:
    statement = delete(TelegramProcessedUpdate).where(
        TelegramProcessedUpdate.processed_at < cutoff,
    )
    result = await session.execute(statement)
    return result.rowcount
