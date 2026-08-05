import logging

from fastapi import APIRouter, Cookie, Depends, Header, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.api.errors import AuthenticationError, authentication_error_response
from freecoinalert_api.auth.email import normalize_email
from freecoinalert_api.auth.origin import validate_authentication_origin
from freecoinalert_api.auth.passwords import (
    hash_password,
    validate_password,
    verify_dummy_password,
    verify_password,
)
from freecoinalert_api.auth.rate_limit import (
    authentication_rate_limiter,
    login_failure_key,
    login_ip_key,
    registration_ip_key,
)
from freecoinalert_api.auth.sessions import create_session_credentials
from freecoinalert_api.auth.principal import (
    AuthenticatedSession,
    SESSION_COOKIE_NAME,
    get_authenticated_session,
    require_authenticated_session,
    validate_csrf_token,
)
from freecoinalert_api.core.config import Settings, get_settings
from freecoinalert_api.db.models.user import User
from freecoinalert_api.db.repositories.auth_sessions import (
    create_auth_session,
    revoke_auth_session,
)
from freecoinalert_api.db.repositories.users import (
    create_user,
    get_user_by_normalized_email,
)
from freecoinalert_api.db.session import get_database_session
from freecoinalert_api.schemas.auth import (
    AuthenticatedUser,
    AuthenticationRequest,
    AuthenticationResponse,
)

auth_router = APIRouter(prefix="/auth", tags=["authentication"])
logger = logging.getLogger(__name__)


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    authentication_request: AuthenticationRequest,
    request: Request,
    database_session: AsyncSession = Depends(get_database_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    try:
        validate_authentication_origin(request, settings)
        await authentication_rate_limiter.consume(
            registration_ip_key(get_client_ip(request)),
            limit=100 if settings.e2e_test_mode else 5,
        )
        email, email_normalized = normalize_email(authentication_request.email)
        validate_password(authentication_request.password)

        existing_user = await get_user_by_normalized_email(
            database_session,
            email_normalized=email_normalized,
        )

        if existing_user is not None:
            raise AuthenticationError(
                status_code=409,
                code="AUTH_REGISTRATION_UNAVAILABLE",
                message="Registration is unavailable for this email.",
            )

        user = await create_user(
            database_session,
            email=email,
            email_normalized=email_normalized,
            password_hash=hash_password(authentication_request.password),
        )
        session_token, token_hash, csrf_token, expires_at = create_session_credentials(
            settings
        )
        await create_auth_session(
            database_session,
            user_id=user.id,
            token_hash=token_hash,
            csrf_token=csrf_token,
            expires_at=expires_at,
        )
        await database_session.commit()
    except IntegrityError as error:
        await database_session.rollback()
        del error
        return authentication_error_response(
            AuthenticationError(
                status_code=409,
                code="AUTH_REGISTRATION_UNAVAILABLE",
                message="Registration is unavailable for this email.",
            )
        )
    except AuthenticationError as error:
        return authentication_error_response(error)

    return authentication_success_response(
        status_code=status.HTTP_201_CREATED,
        user=user,
        csrf_token=csrf_token,
        session_token=session_token,
        settings=settings,
    )


@auth_router.post("/login")
async def login(
    authentication_request: AuthenticationRequest,
    request: Request,
    database_session: AsyncSession = Depends(get_database_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    try:
        validate_authentication_origin(request, settings)
        client_ip = get_client_ip(request)
        await authentication_rate_limiter.consume(login_ip_key(client_ip), limit=10)
        email, email_normalized = normalize_email(authentication_request.email)
        validate_password(authentication_request.password)
        user = await get_user_by_normalized_email(
            database_session,
            email_normalized=email_normalized,
        )

        if user is None:
            verify_dummy_password(authentication_request.password)
            await authentication_rate_limiter.consume(
                login_failure_key(client_ip, email_normalized),
                limit=5,
            )
            raise invalid_credentials_error()

        if not verify_password(authentication_request.password, user.password_hash):
            await authentication_rate_limiter.consume(
                login_failure_key(client_ip, email_normalized),
                limit=5,
            )
            raise invalid_credentials_error()

        await authentication_rate_limiter.clear(login_failure_key(client_ip, email_normalized))
        session_token, token_hash, csrf_token, expires_at = create_session_credentials(
            settings
        )
        await create_auth_session(
            database_session,
            user_id=user.id,
            token_hash=token_hash,
            csrf_token=csrf_token,
            expires_at=expires_at,
        )
        await database_session.commit()
    except AuthenticationError as error:
        return authentication_error_response(error)

    return authentication_success_response(
        status_code=status.HTTP_200_OK,
        user=user,
        csrf_token=csrf_token,
        session_token=session_token,
        settings=settings,
    )


@auth_router.get("/me")
async def current_user(
    authenticated_session: AuthenticatedSession = Depends(require_authenticated_session),
) -> JSONResponse:
    response_body = AuthenticationResponse(
        user=AuthenticatedUser.model_validate(
            authenticated_session.user,
            from_attributes=True,
        ),
        csrf_token=authenticated_session.csrf_token,
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response_body.model_dump(mode="json", by_alias=True),
        headers={"Cache-Control": "no-store"},
    )


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    database_session: AsyncSession = Depends(get_database_session),
) -> Response:
    authenticated_session = await get_authenticated_session(
        session_token,
        database_session,
    )

    if authenticated_session is not None:
        try:
            validate_csrf_token(csrf_token, authenticated_session.csrf_token)
        except AuthenticationError as error:
            return authentication_error_response(error)

        revoked_session = await revoke_auth_session(
            database_session,
            auth_session_id=authenticated_session.principal.session_id,
        )

        if revoked_session is not None:
            await database_session.commit()
            logger.info(
                "auth.logout.success user_id=%s session_id=%s",
                authenticated_session.principal.user_id,
                authenticated_session.principal.session_id,
            )

    response.status_code = status.HTTP_204_NO_CONTENT
    response.headers["Cache-Control"] = "no-store"
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return response


def get_client_ip(request: Request) -> str:
    if request.client is None:
        return "unknown"

    return request.client.host


def invalid_credentials_error() -> AuthenticationError:
    return AuthenticationError(
        status_code=401,
        code="AUTH_INVALID_CREDENTIALS",
        message="Email or password is incorrect.",
    )


def authentication_success_response(
    *,
    status_code: int,
    user: User,
    csrf_token: str,
    session_token: str,
    settings: Settings,
) -> JSONResponse:
    response_body = AuthenticationResponse(
        user=AuthenticatedUser.model_validate(user, from_attributes=True),
        csrf_token=csrf_token,
    )
    response = JSONResponse(
        status_code=status_code,
        content=response_body.model_dump(mode="json", by_alias=True),
        headers={"Cache-Control": "no-store"},
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        path="/",
    )
    return response
