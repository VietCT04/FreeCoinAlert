import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from freecoinalert_api.db.models.auth_session import AuthSession


async def create_auth_session(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    token_hash: bytes,
    csrf_token: str,
    expires_at: datetime,
) -> AuthSession:
    auth_session = AuthSession(
        user_id=user_id,
        token_hash=token_hash,
        csrf_token=csrf_token,
        expires_at=expires_at,
    )
    session.add(auth_session)
    await session.flush()
    return auth_session


async def get_active_session_by_token_hash(
    session: AsyncSession,
    *,
    token_hash: bytes,
) -> AuthSession | None:
    statement = select(AuthSession).where(
        AuthSession.token_hash == token_hash,
        AuthSession.revoked_at.is_(None),
        AuthSession.expires_at > func.now(),
    )
    return await session.scalar(statement)


async def revoke_auth_session(
    session: AsyncSession,
    *,
    auth_session_id: uuid.UUID,
) -> AuthSession | None:
    auth_session = await session.get(AuthSession, auth_session_id)

    if auth_session is None or auth_session.revoked_at is not None:
        return None

    auth_session.revoked_at = datetime.now(timezone.utc)
    await session.flush()
    return auth_session
