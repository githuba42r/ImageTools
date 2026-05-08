"""Unit tests for the new MCP tool functions (pin/unpin/presigned/download/revoke)."""
import pytest
from unittest.mock import AsyncMock

from mcp_server.tools import (
    pin_image, unpin_image, get_presigned_url, download_image, revoke_presigned_urls,
)
from mcp_server.backend import ImageMeta, ImageBytes, PresignedUrl


def _meta(image_id="i1", pin=None):
    return ImageMeta(
        id=image_id,
        original_filename="x.png",
        created_at="2026-04-30T00:00:00+00:00",
        width=1, height=1, format="PNG", current_size=1,
        tags=(),
        pin_expires_at=pin,
        effective_expires_at=None,
    )


@pytest.mark.asyncio
async def test_pin_default_duration():
    backend = AsyncMock()
    backend.pin_image.return_value = _meta(pin="2026-07-29T00:00:00+00:00")
    out = await pin_image(backend, user_id="u1", image_id="i1")
    backend.pin_image.assert_awaited_once_with("u1", "i1", None)
    assert out["meta"]["pin_expires_at"] == "2026-07-29T00:00:00+00:00"


@pytest.mark.asyncio
async def test_pin_passes_duration():
    backend = AsyncMock()
    backend.pin_image.return_value = _meta(pin="2026-05-30T00:00:00+00:00")
    await pin_image(backend, user_id="u1", image_id="i1", duration_days=30)
    backend.pin_image.assert_awaited_once_with("u1", "i1", 30)


@pytest.mark.asyncio
async def test_pin_raises_lookup_error_when_missing():
    backend = AsyncMock()
    backend.pin_image.return_value = None
    with pytest.raises(LookupError):
        await pin_image(backend, user_id="u1", image_id="missing")


@pytest.mark.asyncio
async def test_unpin_calls_backend():
    backend = AsyncMock()
    backend.unpin_image.return_value = _meta(pin=None)
    out = await unpin_image(backend, user_id="u1", image_id="i1")
    assert out["meta"]["pin_expires_at"] is None


@pytest.mark.asyncio
async def test_get_presigned_url_returns_full_payload():
    backend = AsyncMock()
    backend.create_presigned_url.return_value = PresignedUrl(
        url="https://imagetools.example/i/abc.def",
        token="abc.def",
        expires_at="2026-07-29T00:00:00+00:00",
        image_id="i1",
        pin_expires_at="2026-07-29T00:00:00+00:00",
    )
    out = await get_presigned_url(backend, user_id="u1", image_id="i1", ttl_days=90)
    assert out["url"].startswith("https://imagetools.example/i/")
    assert out["token"] == "abc.def"
    assert out["expires_at"] == "2026-07-29T00:00:00+00:00"
    assert out["pin_expires_at"] == "2026-07-29T00:00:00+00:00"


@pytest.mark.asyncio
async def test_download_image_alias_for_get_image():
    backend = AsyncMock()
    backend.get_image.return_value = ImageBytes(
        meta=_meta(), data=b"\x89PNG\r\n", mime_type="image/png",
    )
    out = await download_image(backend, user_id="u1", image_id="i1")
    assert out["mime_type"] == "image/png"
    assert out["data"].startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_revoke_calls_backend_and_returns_revoked():
    backend = AsyncMock()
    backend.revoke_presigned_urls.return_value = True
    out = await revoke_presigned_urls(backend, user_id="u1", image_id="i1")
    assert out == {"image_id": "i1", "revoked": True}


@pytest.mark.asyncio
async def test_revoke_raises_lookup_error_when_missing():
    backend = AsyncMock()
    backend.revoke_presigned_urls.return_value = False
    with pytest.raises(LookupError):
        await revoke_presigned_urls(backend, user_id="u1", image_id="missing")
