"""REST-backed client used by the stdio MCP transport."""
from __future__ import annotations

import httpx

from .backend import BackendClient, ImageBytes, ImageMeta, PresignedUrl


def _mime_for(fmt: str) -> str:
    fmt = (fmt or "").lower()
    if fmt in ("jpg", "jpeg"):
        return "image/jpeg"
    return f"image/{fmt or 'png'}"


def _meta_from_image_response(d: dict) -> ImageMeta:
    return ImageMeta(
        id=d["id"],
        original_filename=d["original_filename"],
        created_at=d["created_at"],
        width=d["width"],
        height=d["height"],
        format=d["format"],
        current_size=d["current_size"],
        tags=tuple(d.get("tags", [])),
        pin_expires_at=d.get("pin_expires_at"),
        effective_expires_at=d.get("effective_expires_at"),
    )


class HttpBackendClient:
    def __init__(self, base_url: str, token: str, timeout: float = 30.0):
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}"}
        self._client = httpx.AsyncClient(timeout=timeout, headers=self._headers)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def list_user_images(
        self, user_id: str, limit: int, tag: str | None = None,
    ) -> list[ImageMeta]:
        params = {"tag": tag} if tag is not None else {}
        r = await self._client.get(
            f"{self._base_url}/api/v1/images/user/{user_id}",
            params=params,
        )
        r.raise_for_status()
        return [_meta_from_image_response(img) for img in r.json()[:limit]]

    async def get_image(self, user_id: str, image_id: str) -> ImageBytes | None:
        meta_r = await self._client.get(
            f"{self._base_url}/api/v1/images/{image_id}"
        )
        if meta_r.status_code == 404:
            return None
        meta_r.raise_for_status()
        meta_json = meta_r.json()
        if meta_json.get("user_id") != user_id:
            return None

        bytes_r = await self._client.get(
            f"{self._base_url}/api/v1/images/{image_id}/current"
        )
        bytes_r.raise_for_status()

        meta = _meta_from_image_response(meta_json)
        return ImageBytes(
            meta=meta,
            data=bytes_r.content,
            mime_type=_mime_for(meta.format),
        )

    async def pin_image(self, user_id, image_id, duration_days):
        body = {"duration_days": duration_days} if duration_days is not None else {}
        r = await self._client.put(
            f"{self._base_url}/api/v1/images/{image_id}/pin",
            json=body,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return _meta_from_image_response(r.json())

    async def unpin_image(self, user_id, image_id):
        r = await self._client.delete(
            f"{self._base_url}/api/v1/images/{image_id}/pin",
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return _meta_from_image_response(r.json())

    async def create_presigned_url(self, user_id, image_id, ttl_days):
        body = {"ttl_days": ttl_days} if ttl_days is not None else {}
        r = await self._client.post(
            f"{self._base_url}/api/v1/images/{image_id}/presigned-url",
            json=body,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        d = r.json()
        return PresignedUrl(
            url=d["url"], token=d["token"], expires_at=d["expires_at"],
            image_id=d["image_id"], pin_expires_at=d["pin_expires_at"],
        )

    async def revoke_presigned_urls(self, user_id, image_id):
        r = await self._client.delete(
            f"{self._base_url}/api/v1/images/{image_id}/presigned-urls",
        )
        if r.status_code == 404:
            return False
        r.raise_for_status()
        return True
