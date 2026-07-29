from email_validator import EmailNotValidError, validate_email

from freecoinalert_api.api.errors import AuthenticationError


def normalize_email(value: str) -> tuple[str, str]:
    try:
        validated_email = validate_email(
            value.strip(),
            check_deliverability=False,
        )
    except EmailNotValidError as error:
        raise AuthenticationError(
            status_code=422,
            code="AUTH_REQUEST_INVALID",
            message="The authentication request is invalid.",
        ) from error

    email = validated_email.normalized
    return email, email.casefold()

