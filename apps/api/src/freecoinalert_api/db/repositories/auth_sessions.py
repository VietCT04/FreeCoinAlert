import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.auth_session import AuthSession
from freecoinalert_api.db.models.user import User


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


async def get_active_session_and_user_by_token_hash(
    session: AsyncSession,
    *,
    token_hash: bytes,
    current_time: datetime,
) -> tuple[AuthSession, User] | None:
    statement = select(AuthSession, User).join(
        User,
        AuthSession.user_id == User.id,
    ).where(
        AuthSession.token_hash == token_hash,
        AuthSession.revoked_at.is_(None),
        AuthSession.expires_at > current_time,
    )
    result = await session.execute(statement)
    return result.one_or_none()


async def get_active_session_by_id(
    session: AsyncSession,
    *,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    current_time: datetime,
) -> AuthSession | None:
    return await session.scalar(
        select(AuthSession).where(
            AuthSession.id == session_id,
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > current_time,
        )
    )


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
