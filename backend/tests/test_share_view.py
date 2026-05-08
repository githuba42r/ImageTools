"""HTTP-level tests for the /s/{token} viewer page and /s/{token}/raw bytes."""
import pytest
import sqlalchemy
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_share_root_returns_html_with_metadata(
    client: AsyncClient, seeded_image, db_session,
):
    # Create the share link via the existing API
    r = await client.post(
        f"/api/v1/images/{seeded_image['id']}/share",
        headers={"X-User-ID": seeded_image["user_id"]},
    )
    assert r.status_code == 200
    token = r.json()["url"].rsplit("/", 1)[1]

    page = await client.get(f"/s/{token}")
    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    body = page.text
    assert f"/s/{token}/raw" in body                # the <img> source
    assert "Captured:" in body
    assert "Auto-deletes:" in body


@pytest.mark.asyncio
async def test_share_raw_returns_bytes(
    client: AsyncClient, seeded_image, db_session, tmp_path,
):
    real = tmp_path / "x.png"
    real.write_bytes(b"\x89PNG\r\n\x1a\nFAKE")
    await db_session.execute(
        sqlalchemy.text("UPDATE images SET current_path = :p WHERE id = :i"),
        {"p": str(real), "i": seeded_image["id"]},
    )
    await db_session.commit()

    r = await client.post(
        f"/api/v1/images/{seeded_image['id']}/share",
        headers={"X-User-ID": seeded_image["user_id"]},
    )
    token = r.json()["url"].rsplit("/", 1)[1]
    raw = await client.get(f"/s/{token}/raw")
    assert raw.status_code == 200
    assert raw.content.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_share_root_404_for_unknown(client: AsyncClient):
    r = await client.get("/s/not-a-real-token")
    assert r.status_code == 404
