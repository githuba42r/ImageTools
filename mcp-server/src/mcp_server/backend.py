"""Transport-agnostic abstraction over the ImageTools backend.

Two implementations:
  - backend_local.LocalBackendClient: runs in-process with the FastAPI backend,
    calls services/DB directly. Used by the HTTP transport.
  - backend_http.HttpBackendClient: calls the ImageTools REST API over HTTP.
    Used by the stdio transport.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ImageMeta:
    id: str
    original_filename: str
    created_at: str        # ISO 8601
    width: int
    height: int
    format: str            # e.g. "PNG", "JPEG"
    current_size: int
    tags: tuple[str, ...] = ()
    pin_expires_at: str | None = None       # ISO-8601, or None
    effective_expires_at: str | None = None


@dataclass(frozen=True)
class ImageBytes:
    meta: ImageMeta
    data: bytes
    mime_type: str         # e.g. "image/png"


@dataclass(frozen=True)
class PresignedUrl:
    url: str
    token: str
    expires_at: str
    image_id: str
    pin_expires_at: str


class BackendClient(Protocol):
    async def list_user_images(
        self, user_id: str, limit: int, tag: str | None = None
    ) -> list[ImageMeta]: ...

    async def get_image(self, user_id: str, image_id: str) -> ImageBytes | None:
        """Return bytes + metadata, or None if not found / not owned by user."""
        ...

    async def pin_image(
        self, user_id: str, image_id: str, duration_days: int | None
    ) -> ImageMeta | None: ...

    async def unpin_image(self, user_id: str, image_id: str) -> ImageMeta | None: ...

    async def create_presigned_url(
        self, user_id: str, image_id: str, ttl_days: int | None
    ) -> PresignedUrl | None: ...

    async def revoke_presigned_urls(
        self, user_id: str, image_id: str
    ) -> bool: ...
