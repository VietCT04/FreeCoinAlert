from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from freecoinalert_api.core.config import get_settings


@lru_cache
def get_async_engine() -> AsyncEngine:
    return create_async_engine(get_settings().database_url)


@lru_cache
def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_async_engine(),
        expire_on_commit=False,
    )


async def get_database_session() -> AsyncGenerator[AsyncSession]:
    session_factory = get_async_session_factory()

    async with session_factory() as session:
        yield session
