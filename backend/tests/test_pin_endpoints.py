"""HTTP-level tests for pin/unpin/presigned-url endpoints."""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_put_pin_sets_expiry(client: AsyncClient, seeded_image):
    r = await client.put(f"/api/v1/images/{seeded_image['id']}/pin", json={"duration_days": 30})
    assert r.status_code == 200
    pin = datetime.fromisoformat(r.json()["pin_expires_at"].rstrip("Z"))
    delta = pin - datetime.utcnow()
    assert timedelta(days=29, hours=23) < delta < timedelta(days=30, hours=1)


@pytest.mark.asyncio
async def test_put_pin_default_duration(client: AsyncClient, seeded_image):
    r = await client.put(f"/api/v1/images/{seeded_image['id']}/pin", json={})
    assert r.status_code == 200
    pin = datetime.fromisoformat(r.json()["pin_expires_at"].rstrip("Z"))
    delta = pin - datetime.utcnow()
    assert timedelta(days=89, hours=23) < delta < timedelta(days=90, hours=1)


@pytest.mark.asyncio
async def test_put_pin_extends_not_shortens(client: AsyncClient, seeded_image):
    await client.put(f"/api/v1/images/{seeded_image['id']}/pin", json={"duration_days": 60})
    r = await client.put(f"/api/v1/images/{seeded_image['id']}/pin", json={"duration_days": 10})
    pin = datetime.fromisoformat(r.json()["pin_expires_at"].rstrip("Z"))
    delta = pin - datetime.utcnow()
    assert timedelta(days=59) < delta < timedelta(days=61)


@pytest.mark.asyncio
async def test_put_pin_rejects_zero(client: AsyncClient, seeded_image):
    r = await client.put(f"/api/v1/images/{seeded_image['id']}/pin", json={"duration_days": 0})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_put_pin_404_for_unknown(client: AsyncClient):
    r = await client.put("/api/v1/images/missing/pin", json={"duration_days": 30})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_pin_clears(client: AsyncClient, seeded_image):
    await client.put(f"/api/v1/images/{seeded_image['id']}/pin", json={"duration_days": 30})
    r = await client.delete(f"/api/v1/images/{seeded_image['id']}/pin")
    assert r.status_code == 200
    assert r.json()["pin_expires_at"] is None


@pytest.mark.asyncio
async def test_delete_pin_404_for_unknown(client: AsyncClient):
    r = await client.delete("/api/v1/images/missing/pin")
    assert r.status_code == 404


# --- Presigned URL mint + serve ------------------------------------------- #

@pytest.mark.asyncio
async def test_mint_url_returns_absolute_with_request_host_and_bumps_pin(
    client: AsyncClient, seeded_image, monkeypatch,
):
    monkeypatch.setattr("app.services.presigned_url.settings.PRESIGNED_URL_SECRET", "test-secret")
    r = await client.post(
        f"/api/v1/images/{seeded_image['id']}/presigned-url",
        json={"ttl_days": 30},
        headers={"x-forwarded-host": "imagetools.example.com", "x-forwarded-proto": "https"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["url"].startswith("https://imagetools.example.com/i/")
    pin = datetime.fromisoformat(body["pin_expires_at"].rstrip("Z"))
    delta = pin - datetime.utcnow()
    assert timedelta(days=29, hours=23) < delta < timedelta(days=30, hours=1)


@pytest.mark.asyncio
async def test_mint_url_404_for_unknown(client: AsyncClient):
    r = await client.post("/api/v1/images/missing/presigned-url", json={"ttl_days": 7})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_i_serves_bytes(
    client: AsyncClient, seeded_image, db_session, tmp_path, monkeypatch,
):
    monkeypatch.setattr("app.services.presigned_url.settings.PRESIGNED_URL_SECRET", "test-secret")
    real = tmp_path / "x.png"
    real.write_bytes(b"\x89PNG\r\n\x1a\nFAKE")
    # Update the seeded image to point at the real file we just wrote.
    import sqlalchemy
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
    # Strip the host part — AsyncClient is bound to base_url=http://test
    path = url.split("://", 1)[1].split("/", 1)[1]
    r = await client.get(f"/{path}")
    assert r.status_code == 200
    assert r.content.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_get_i_404_for_invalid_token(client: AsyncClient):
    r = await client.get("/i/not-a-real-token")
    assert r.status_code == 404


# --- Pepper rotation: revoke all presigned URLs for an image -------------- #

@pytest.mark.asyncio
async def test_rotate_pepper_invalidates_existing_url(
    client: AsyncClient, seeded_image, db_session, tmp_path, monkeypatch,
):
    monkeypatch.setattr("app.services.presigned_url.settings.PRESIGNED_URL_SECRET", "test-secret")
    real = tmp_path / "x.png"
    real.write_bytes(b"\x89PNG\r\n\x1a\nFAKE")
    import sqlalchemy
    await db_session.execute(
        sqlalchemy.text("UPDATE images SET current_path = :p WHERE id = :i"),
        {"p": str(real), "i": seeded_image["id"]},
    )
    await db_session.commit()

    # Mint a URL — confirm it works.
    mint = await client.post(
        f"/api/v1/images/{seeded_image['id']}/presigned-url", json={"ttl_days": 30},
    )
    url = mint.json()["url"]
    path = url.split("://", 1)[1].split("/", 1)[1]
    assert (await client.get(f"/{path}")).status_code == 200

    # Revoke. The previously-minted URL must now 404.
    rev = await client.delete(f"/api/v1/images/{seeded_image['id']}/presigned-urls")
    assert rev.status_code == 200
    assert (await client.get(f"/{path}")).status_code == 404

    # And a freshly-minted URL must work again.
    mint2 = await client.post(
        f"/api/v1/images/{seeded_image['id']}/presigned-url", json={"ttl_days": 30},
    )
    path2 = mint2.json()["url"].split("://", 1)[1].split("/", 1)[1]
    assert (await client.get(f"/{path2}")).status_code == 200


@pytest.mark.asyncio
async def test_rotate_pepper_404_for_unknown(client: AsyncClient):
    r = await client.delete("/api/v1/images/missing/presigned-urls")
    assert r.status_code == 404
