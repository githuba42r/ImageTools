"""Per-IP rate-limit tests on /i/{token}, /s/{token}, /s/{token}/raw."""
import pytest
import sqlalchemy
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_share_route_rate_limited(monkeypatch, client: AsyncClient, seeded_image, db_session):
    monkeypatch.setattr("app.core.config.settings.RATE_LIMIT_IMAGE_ACCESS", "3/minute")

    r = await client.post(
        f"/api/v1/images/{seeded_image['id']}/share",
        headers={"X-User-ID": seeded_image["user_id"]},
    )
    token = r.json()["url"].rsplit("/", 1)[1]

    statuses = []
    for _ in range(5):
        statuses.append((await client.get(f"/s/{token}")).status_code)

    # First 3 should pass (200), the 4th and 5th should be 429.
    assert statuses[:3] == [200, 200, 200]
    assert 429 in statuses[3:]


@pytest.mark.asyncio
async def test_presigned_route_rate_limited(
    monkeypatch, client: AsyncClient, seeded_image, db_session, tmp_path,
):
    monkeypatch.setattr("app.core.config.settings.RATE_LIMIT_IMAGE_ACCESS", "3/minute")
    monkeypatch.setattr("app.services.presigned_url.settings.PRESIGNED_URL_SECRET", "test-secret")

    real = tmp_path / "x.png"
    real.write_bytes(b"\x89PNG\r\n\x1a\nFAKE")
    await db_session.execute(
        sqlalchemy.text("UPDATE images SET current_path = :p WHERE id = :i"),
        {"p": str(real), "i": seeded_image["id"]},
    )
    await db_session.commit()

    mint = await client.post(
        f"/api/v1/images/{seeded_image['id']}/presigned-url",
        json={"ttl_days": 30},
    )
    url = mint.json()["url"]
    path = url.split("://", 1)[1].split("/", 1)[1]
    statuses = []
    for _ in range(5):
        statuses.append((await client.get(f"/{path}")).status_code)
    assert statuses[:3] == [200, 200, 200]
    assert 429 in statuses[3:]
