"""Per-IP rate limiter shared across the public-facing image routes.

Used by /i/{token} (presigned), /s/{token} (share viewer HTML), and
/s/{token}/raw (share bytes). The limit string is read from settings on
each request so test monkeypatches take effect without rebuilding the
limiter.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

_limiter: Limiter | None = None


def get_limiter() -> Limiter:
    global _limiter
    if _limiter is None:
        _limiter = Limiter(key_func=get_remote_address)
    return _limiter


def image_access_limit() -> str:
    """Return the configured rate-limit string (read each call)."""
    return settings.RATE_LIMIT_IMAGE_ACCESS


def reset_for_tests() -> None:
    """Reset the limiter state between tests that change RATE_LIMIT_IMAGE_ACCESS."""
    global _limiter
    _limiter = None
