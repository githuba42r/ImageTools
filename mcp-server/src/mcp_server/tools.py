"""Transport-agnostic MCP tool implementations."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .backend import BackendClient, ImageMeta

MAX_LIST_COUNT = 50
MAX_RECENT_COUNT = 6
DEFAULT_LIST_COUNT = 10
DEFAULT_RECENT_COUNT = 1


def _clamp(value: int, lo: int, hi: int) -> tuple[int, bool]:
    clamped = max(lo, min(value, hi))
    return clamped, clamped != value


def _meta_dict(m: ImageMeta) -> dict[str, Any]:
    return asdict(m)


async def list_recent_images(
    backend: BackendClient, user_id: str, count: int = DEFAULT_LIST_COUNT,
    tag: str | None = None,
) -> dict[str, Any]:
    """Return metadata for the N most recent images, newest first."""
    clamped, was_clamped = _clamp(count, 1, MAX_LIST_COUNT)
    metas = await backend.list_user_images(user_id, clamped, tag=tag)
    return {
        "images": [_meta_dict(m) for m in metas],
        "clamped": was_clamped,
    }


async def get_image(
    backend: BackendClient, user_id: str, image_id: str
) -> dict[str, Any]:
    """Return bytes + metadata for one image. Raises LookupError if not found."""
    result = await backend.get_image(user_id, image_id)
    if result is None:
        raise LookupError(f"image not found: {image_id}")
    return {
        "meta": _meta_dict(result.meta),
        "data": result.data,
        "mime_type": result.mime_type,
    }


async def get_recent_images(
    backend: BackendClient, user_id: str, count: int = DEFAULT_RECENT_COUNT,
    tag: str | None = None,
) -> dict[str, Any]:
    """Fetch bytes + metadata for the N most recent images, newest first."""
    clamped, was_clamped = _clamp(count, 1, MAX_RECENT_COUNT)
    metas = await backend.list_user_images(user_id, clamped, tag=tag)
    images: list[dict[str, Any]] = []
    missing: list[str] = []
    for m in metas:
        result = await backend.get_image(user_id, m.id)
        if result is None:
            missing.append(m.id)
            continue
        images.append({
            "meta": _meta_dict(result.meta),
            "data": result.data,
            "mime_type": result.mime_type,
        })
    return {"images": images, "clamped": was_clamped, "missing": missing}
