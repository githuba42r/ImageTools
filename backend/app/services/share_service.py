"""In-memory temporary share link service.

Manages short-lived tokens that map to image files. Tokens are stored in
a Python dict and expire after SHARE_LINK_EXPIRY_SECONDS. A periodic
cleanup task purges expired entries. All state is intentionally lost on
restart — these are ephemeral links.
"""

import secrets
import string
import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Base62 alphabet for URL-safe tokens
_ALPHABET = string.ascii_letters + string.digits
_TOKEN_LENGTH = 16


@dataclass
class ShareEntry:
    image_id: str
    image_path: str
    media_type: str
    original_filename: str
    expires_at: datetime


# Module-level store — single process, intentionally ephemeral
_store: dict[str, ShareEntry] = {}


def create_share_link(image_id: str, image_path: str, media_type: str, original_filename: str) -> dict:
    """Create a temporary share token for an image.

    Returns dict with 'url' (relative path) and 'expires_in' (seconds).
    """
    token = "".join(secrets.choice(_ALPHABET) for _ in range(_TOKEN_LENGTH))
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.SHARE_LINK_EXPIRY_SECONDS)

    _store[token] = ShareEntry(
        image_id=image_id,
        image_path=image_path,
        media_type=media_type,
        original_filename=original_filename,
        expires_at=expires_at,
    )

    logger.info(f"Share link created for image {image_id}, token={token[:4]}..., expires={expires_at.isoformat()}")
    return {
        "url": f"/s/{token}",
        "expires_in": settings.SHARE_LINK_EXPIRY_SECONDS,
    }


def get_shared_image(token: str) -> Optional[ShareEntry]:
    """Look up a share token. Returns the entry if valid, None if expired or missing."""
    entry = _store.get(token)
    if entry is None:
        return None

    if datetime.now(timezone.utc) >= entry.expires_at:
        # Expired — remove eagerly
        del _store[token]
        return None

    return entry


def cleanup_expired() -> int:
    """Remove all expired entries. Returns count of removed entries."""
    now = datetime.now(timezone.utc)
    expired_tokens = [t for t, e in _store.items() if now >= e.expires_at]
    for token in expired_tokens:
        del _store[token]

    if expired_tokens:
        logger.info(f"Cleaned up {len(expired_tokens)} expired share link(s)")
    return len(expired_tokens)
