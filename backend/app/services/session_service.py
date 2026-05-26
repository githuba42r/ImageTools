"""Signed-cookie helpers for OAuth2 session and state cookies.

Both cookies are signed by SESSION_SECRET_KEY with itsdangerous.URLSafeTimedSerializer.
Distinct salts ensure a session-cookie value cannot be replayed as a state cookie.
The service is pure functions; no I/O, no DB.
"""
from typing import Optional

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import settings

_SESSION_SALT = "imagetools.session.v1"
_STATE_SALT = "imagetools.oauth2_state.v1"


def _serializer(salt: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SESSION_SECRET_KEY, salt=salt)


def sign_session(payload: dict) -> str:
    return _serializer(_SESSION_SALT).dumps(payload)


def verify_session(token: str, max_age: int) -> Optional[dict]:
    if max_age <= 0:
        return None
    try:
        return _serializer(_SESSION_SALT).loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None


def sign_state(payload: dict) -> str:
    return _serializer(_STATE_SALT).dumps(payload)


def verify_state(token: str, max_age: int) -> Optional[dict]:
    if max_age <= 0:
        return None
    try:
        return _serializer(_STATE_SALT).loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
