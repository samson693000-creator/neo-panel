import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

PREFIX = "enc::"

def _build_key() -> bytes:
    if settings.encryption_key:
        raw = settings.encryption_key.encode()
        try:
            Fernet(raw)
            return raw
        except (ValueError, TypeError):
            pass
        digest = hashlib.sha256(raw).digest()
    else:
        digest = hashlib.sha256(settings.secret_key.encode()).digest()
    return base64.urlsafe_b64encode(digest)

_fernet = Fernet(_build_key())

def encrypt(value: str) -> str:
    if value is None:
        return ""
    return PREFIX + _fernet.encrypt(value.encode()).decode()

def decrypt(value: str) -> str:
    if not value:
        return ""
    if not value.startswith(PREFIX):
        return value
    try:
        return _fernet.decrypt(value[len(PREFIX):].encode()).decode()
    except InvalidToken:
        return ""

def mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * 8}{value[-4:]}"
