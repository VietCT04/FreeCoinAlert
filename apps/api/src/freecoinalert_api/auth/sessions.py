import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from freecoinalert_api.core.config import Settings


def create_session_credentials(settings: Settings) -> tuple[str, bytes, str, datetime]:
    token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).digest()
    expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=settings.session_ttl_seconds,
    )
    return token, token_hash, csrf_token, expires_at
