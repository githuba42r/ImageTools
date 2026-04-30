"""In-process backend client used by the HTTP MCP transport.

Accesses the ImageTools DB and storage directly, because it runs in the
same process as the FastAPI backend.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, AsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.image_service import ImageService
from app.core.config import settings
from app.core.url_utils import get_instance_url
from .backend import BackendClient, ImageBytes, ImageMeta, PresignedUrl


def _iso(dt) -> str:
    return dt.isoformat() if dt is not None else ""


def _mime_for(fmt: str) -> str:
    fmt = (fmt or "").lower()
    if fmt in ("jpg", "jpeg"):
        return "image/jpeg"
    return f"image/{fmt or 'png'}"


def _meta_from_image(img) -> ImageMeta:
    """Build an ImageMeta from an Image ORM instance, including pin/expiry."""
    from app.services.user_service import ANONYMOUS_USER_ID
    eff = None
    if img.user_id == ANONYMOUS_USER_ID:
        eff = ImageService.effective_expires_at(
            created_at=img.created_at,
            pin_expires_at=img.pin_expires_at,
            retention_days=settings.ANONYMOUS_IMAGE_RETENTION_DAYS,
        )
    return ImageMeta(
        id=img.id,
        original_filename=img.original_filename,
        created_at=_iso(img.created_at),
        width=img.width,
        height=img.height,
        format=img.format,
        current_size=img.current_size,
        tags=tuple(ImageService.get_tags(img)),
        pin_expires_at=_iso(img.pin_expires_at) if img.pin_expires_at else None,
        effective_expires_at=_iso(eff) if eff else None,
    )


class LocalBackendClient:
    """Uses a session factory (NOT a single session) so each call gets a fresh
    session — matches FastAPI's Depends(get_db) pattern."""

    def __init__(self, session_factory: Callable[[], AsyncContextManager[AsyncSession]]):
        self._session_factory = session_factory

    async def list_user_images(
        self, user_id: str, limit: int, tag: str | None = None,
    ) -> list[ImageMeta]:
        async with self._session_factory() as db:
            images = await ImageService.get_user_images(db, user_id, tag=tag)
        return [_meta_from_image(img) for img in images[:limit]]

    async def get_image(self, user_id: str, image_id: str) -> ImageBytes | None:
        async with self._session_factory() as db:
            img = await ImageService.get_image(db, image_id)
            if img is None or img.user_id != user_id:
                return None
            path = Path(img.current_path)
            if not path.exists():
                return None
            data = path.read_bytes()
            return ImageBytes(meta=_meta_from_image(img), data=data, mime_type=_mime_for(img.format))

    async def pin_image(self, user_id, image_id, duration_days):
        async with self._session_factory() as db:
            img = await ImageService.get_image(db, image_id)
            if img is None or img.user_id != user_id:
                return None
            duration = settings.PIN_DEFAULT_DURATION_DAYS if duration_days is None else duration_days
            updated = await ImageService.pin_image(db, image_id, duration_days=duration)
            if updated is None:
                return None
            return _meta_from_image(updated)

    async def unpin_image(self, user_id, image_id):
        async with self._session_factory() as db:
            img = await ImageService.get_image(db, image_id)
            if img is None or img.user_id != user_id:
                return None
            updated = await ImageService.unpin_image(db, image_id)
            if updated is None:
                return None
            return _meta_from_image(updated)

    async def create_presigned_url(self, user_id, image_id, ttl_days):
        from app.services.presigned_url import build_token
        from datetime import datetime as _dt, timezone as _tz
        import time as _time
        async with self._session_factory() as db:
            img = await ImageService.get_image(db, image_id)
            if img is None or img.user_id != user_id:
                return None
            ttl = settings.PIN_DEFAULT_DURATION_DAYS if ttl_days is None else ttl_days
            await ImageService.pin_image(db, image_id, duration_days=ttl)
            refreshed = await ImageService.get_image(db, image_id)
            exp = int(_time.time()) + ttl * 86400
            token = build_token(
                image_id=refreshed.id, expires_at_epoch=exp, pepper=refreshed.url_pepper,
            )
            # Local mode has no Request to pull X-Forwarded-Host from; fall
            # back to INSTANCE_URL. Documents embedding the URL will use that.
            base = settings.INSTANCE_URL.rstrip("/")
            return PresignedUrl(
                url=f"{base}/i/{token}",
                token=token,
                expires_at=_dt.fromtimestamp(exp, tz=_tz.utc).isoformat(),
                image_id=refreshed.id,
                pin_expires_at=_iso(refreshed.pin_expires_at),
            )

    async def revoke_presigned_urls(self, user_id, image_id):
        async with self._session_factory() as db:
            img = await ImageService.get_image(db, image_id)
            if img is None or img.user_id != user_id:
                return False
            updated = await ImageService.rotate_url_pepper(db, image_id)
            return updated is not None
