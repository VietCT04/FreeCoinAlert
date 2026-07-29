import hashlib
import hmac
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Cookie, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.api.errors import AuthenticationError
from freecoinalert_api.db.models.user import User
from freecoinalert_api.db.repositories.auth_sessions import (
    get_active_session_and_user_by_token_hash,
)
from freecoinalert_api.db.session import get_database_session

SESSION_COOKIE_NAME = "freecoinalert_session"
SESSION_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}")
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    user_id: UUID
    session_id: UUID


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    principal: AuthenticatedPrincipal
    user: User
    csrf_token: str


async def get_authenticated_session(
    session_token: str | None,
    database_session: AsyncSession,
) -> AuthenticatedSession | None:
    if session_token is None or SESSION_TOKEN_PATTERN.fullmatch(session_token) is None:
        return None

    token_hash = hashlib.sha256(session_token.encode("utf-8")).digest()
    session_and_user = await get_active_session_and_user_by_token_hash(
        database_session,
        token_hash=token_hash,
        current_time=datetime.now(timezone.utc),
    )

    if session_and_user is None:
        return None

    auth_session, user = session_and_user
    return AuthenticatedSession(
        principal=AuthenticatedPrincipal(
            user_id=user.id,
            session_id=auth_session.id,
        ),
        user=user,
        csrf_token=auth_session.csrf_token,
    )


async def require_authenticated_session(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    database_session: AsyncSession = Depends(get_database_session),
) -> AuthenticatedSession:
    authenticated_session = await get_authenticated_session(
        session_token,
        database_session,
    )

    if authenticated_session is None:
        logger.info("auth.session.rejected")
        raise AuthenticationError(
            status_code=401,
            code="AUTHENTICATION_REQUIRED",
            message="Authentication is required.",
            clear_session_cookie=True,
        )

    return authenticated_session


async def require_authenticated_principal(
    authenticated_session: AuthenticatedSession = Depends(require_authenticated_session),
) -> AuthenticatedPrincipal:
    return authenticated_session.principal


async def require_csrf_protected_principal(
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    authenticated_session: AuthenticatedSession = Depends(require_authenticated_session),
) -> AuthenticatedPrincipal:
    validate_csrf_token(csrf_token, authenticated_session.csrf_token)
    return authenticated_session.principal


def validate_csrf_token(
    supplied_token: str | None,
    session_csrf_token: str,
) -> None:
    if supplied_token is None or not hmac.compare_digest(
        supplied_token,
        session_csrf_token,
    ):
        raise AuthenticationError(
            status_code=403,
            code="AUTH_CSRF_INVALID",
            message="The CSRF token is invalid.",
        )
