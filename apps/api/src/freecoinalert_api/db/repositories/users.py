from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.user import User


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    email_normalized: str,
    password_hash: str,
) -> User:
    user = User(
        email=email,
        email_normalized=email_normalized,
        password_hash=password_hash,
    )
    session.add(user)
    await session.flush()
    return user


async def get_user_by_normalized_email(
    session: AsyncSession,
    *,
    email_normalized: str,
) -> User | None:
    statement = select(User).where(User.email_normalized == email_normalized)
    return await session.scalar(statement)
