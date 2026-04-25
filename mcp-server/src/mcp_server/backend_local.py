"""In-process backend client used by the HTTP MCP transport.

Accesses the ImageTools DB and storage directly, because it runs in the
same process as the FastAPI backend.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, AsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.image_service import ImageService
from .backend import BackendClient, ImageBytes, ImageMeta


def _iso(dt) -> str:
    return dt.isoformat() if dt is not None else ""


def _mime_for(fmt: str) -> str:
    fmt = (fmt or "").lower()
    if fmt in ("jpg", "jpeg"):
        return "image/jpeg"
    return f"image/{fmt or 'png'}"


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
        # ImageService returns newest-first via created_at desc; take limit.
        images = images[:limit]
        return [
            ImageMeta(
                id=img.id,
                original_filename=img.original_filename,
                created_at=_iso(img.created_at),
                width=img.width,
                height=img.height,
                format=img.format,
                current_size=img.current_size,
                tags=tuple(ImageService.get_tags(img)),
            )
            for img in images
        ]

    async def get_image(self, user_id: str, image_id: str) -> ImageBytes | None:
        async with self._session_factory() as db:
            img = await ImageService.get_image(db, image_id)
            if img is None or img.user_id != user_id:
                return None
            path = Path(img.current_path)
            if not path.exists():
                return None
            data = path.read_bytes()
            meta = ImageMeta(
                id=img.id,
                original_filename=img.original_filename,
                created_at=_iso(img.created_at),
                width=img.width,
                height=img.height,
                format=img.format,
                current_size=img.current_size,
                tags=tuple(ImageService.get_tags(img)),
            )
            return ImageBytes(meta=meta, data=data, mime_type=_mime_for(img.format))
