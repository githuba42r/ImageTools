import pytest
from mcp_server.backend import ImageBytes, ImageMeta
from mcp_server.tools import (
    list_recent_images,
    get_image,
    get_recent_images,
    MAX_LIST_COUNT,
    MAX_RECENT_COUNT,
)


class FakeBackend:
    def __init__(self, images: list[ImageMeta], bytes_map: dict[str, bytes]):
        self._images = images
        self._bytes = bytes_map

    async def list_user_images(self, user_id, limit):
        return self._images[:limit]

    async def get_image(self, user_id, image_id):
        for img in self._images:
            if img.id == image_id:
                data = self._bytes.get(image_id, b"")
                return ImageBytes(meta=img, data=data, mime_type="image/png")
        return None


def _img(i: int) -> ImageMeta:
    return ImageMeta(
        id=f"img-{i}",
        original_filename=f"file-{i}.png",
        created_at=f"2026-04-23T10:0{i}:00Z",
        width=100, height=100, format="PNG", current_size=1000 + i,
    )


@pytest.mark.asyncio
async def test_list_recent_clamps_count_to_max():
    backend = FakeBackend([_img(i) for i in range(100)], {})
    result = await list_recent_images(backend, "u", count=9999)
    assert len(result["images"]) == MAX_LIST_COUNT
    assert result["clamped"] is True


@pytest.mark.asyncio
async def test_list_recent_returns_newest_first():
    backend = FakeBackend([_img(3), _img(2), _img(1)], {})
    result = await list_recent_images(backend, "u", count=10)
    assert [i["id"] for i in result["images"]] == ["img-3", "img-2", "img-1"]


@pytest.mark.asyncio
async def test_get_image_returns_bytes_and_meta():
    backend = FakeBackend([_img(1)], {"img-1": b"PNGDATA"})
    result = await get_image(backend, "u", "img-1")
    assert result["meta"]["id"] == "img-1"
    assert result["data"] == b"PNGDATA"
    assert result["mime_type"] == "image/png"


@pytest.mark.asyncio
async def test_get_image_missing_raises_not_found():
    backend = FakeBackend([], {})
    with pytest.raises(LookupError):
        await get_image(backend, "u", "nope")


@pytest.mark.asyncio
async def test_get_recent_caps_count():
    backend = FakeBackend([_img(i) for i in range(10)], {f"img-{i}": b"X" for i in range(10)})
    result = await get_recent_images(backend, "u", count=999)
    assert len(result["images"]) == MAX_RECENT_COUNT
