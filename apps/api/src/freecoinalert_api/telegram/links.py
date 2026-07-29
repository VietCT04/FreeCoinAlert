import base64
import hashlib
import secrets


def create_link_token() -> tuple[str, bytes]:
    raw_token = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("ascii")
    token_hash = hashlib.sha256(raw_token.encode("ascii")).digest()
    return raw_token, token_hash
