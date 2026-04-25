"""REST-backed client used by the stdio MCP transport."""
from __future__ import annotations

import httpx

from .backend import BackendClient, ImageBytes, ImageMeta


def _mime_for(fmt: str) -> str:
    fmt = (fmt or "").lower()
    if fmt in ("jpg", "jpeg"):
        return "image/jpeg"
    return f"image/{fmt or 'png'}"


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
        images = r.json()[:limit]
        return [
            ImageMeta(
                id=img["id"],
                original_filename=img["original_filename"],
                created_at=img["created_at"],
                width=img["width"],
                height=img["height"],
                format=img["format"],
                current_size=img["current_size"],
                tags=tuple(img.get("tags", [])),
            )
            for img in images
        ]

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

        meta = ImageMeta(
            id=meta_json["id"],
            original_filename=meta_json["original_filename"],
            created_at=meta_json["created_at"],
            width=meta_json["width"],
            height=meta_json["height"],
            format=meta_json["format"],
            current_size=meta_json["current_size"],
            tags=tuple(meta_json.get("tags", [])),
        )
        return ImageBytes(
            meta=meta,
            data=bytes_r.content,
            mime_type=_mime_for(meta.format),
        )
