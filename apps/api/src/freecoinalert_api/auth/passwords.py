from pwdlib import PasswordHash

from freecoinalert_api.api.errors import AuthenticationError

MINIMUM_PASSWORD_LENGTH = 15
MAXIMUM_PASSWORD_LENGTH = 128

_password_hash = PasswordHash.recommended()
_dummy_password_hash = (
    "$argon2id$v=19$m=65536,t=3,p=4$ZHVtbXktc2FsdC1mb3ItZnJlZWNvaW5hbGVydA$"
    "MmT2c8YtaCK1mU14F6YQoCLG2r3b1zvgfgVUjvHKKYQ"
)


def validate_password(password: str) -> None:
    if MINIMUM_PASSWORD_LENGTH <= len(password) <= MAXIMUM_PASSWORD_LENGTH:
        return

    raise AuthenticationError(
        status_code=422,
        code="AUTH_REQUEST_INVALID",
        message="The authentication request is invalid.",
    )


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def verify_dummy_password(password: str) -> None:
    _password_hash.verify(password, _dummy_password_hash)

