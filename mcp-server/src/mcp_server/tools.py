"""Transport-agnostic MCP tool implementations."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .backend import BackendClient, ImageMeta, PresignedUrl

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


async def pin_image(
    backend: BackendClient, user_id: str, image_id: str,
    duration_days: int | None = None,
) -> dict[str, Any]:
    """Pin an image to delay auto-cleanup. Re-pinning extends an existing pin (never shortens).

    Use this BEFORE embedding an image URL in a generated document. If you also call
    get_presigned_url, that already bumps the pin — explicit pin_image is only needed
    when you keep an image alive without minting a URL (e.g. you'll call download_image).
    """
    meta = await backend.pin_image(user_id, image_id, duration_days)
    if meta is None:
        raise LookupError(f"image not found: {image_id}")
    return {"meta": _meta_dict(meta)}


async def unpin_image(
    backend: BackendClient, user_id: str, image_id: str,
) -> dict[str, Any]:
    """Unpin an image (return it to the normal retention schedule)."""
    meta = await backend.unpin_image(user_id, image_id)
    if meta is None:
        raise LookupError(f"image not found: {image_id}")
    return {"meta": _meta_dict(meta)}


async def get_presigned_url(
    backend: BackendClient, user_id: str, image_id: str,
    ttl_days: int | None = None,
) -> dict[str, Any]:
    """Mint a long-lived HMAC-signed URL the agent can embed in a generated document.

    Side effect: bumps pin_expires_at to >= URL expiry, so the embedded link stays valid.
    The URL uses the web UI's hostname.
    Returns {url, token, expires_at, image_id, pin_expires_at}.
    """
    out = await backend.create_presigned_url(user_id, image_id, ttl_days)
    if out is None:
        raise LookupError(f"image not found: {image_id}")
    return {
        "url": out.url, "token": out.token,
        "expires_at": out.expires_at, "image_id": out.image_id,
        "pin_expires_at": out.pin_expires_at,
    }


async def download_image(
    backend: BackendClient, user_id: str, image_id: str,
) -> dict[str, Any]:
    """Download an image's bytes + metadata. Alias of `get_image` for prompt clarity."""
    return await get_image(backend, user_id, image_id)


async def revoke_presigned_urls(
    backend: BackendClient, user_id: str, image_id: str,
) -> dict[str, Any]:
    """Revoke ALL outstanding presigned URLs for this image.

    Implementation: rotates the image's url_pepper. Use this when a draft
    document referencing the screenshot is finalized, or when a screenshot is
    replaced and old links must stop resolving.
    """
    ok = await backend.revoke_presigned_urls(user_id, image_id)
    if not ok:
        raise LookupError(f"image not found: {image_id}")
    return {"image_id": image_id, "revoked": True}
