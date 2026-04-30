"""HTTP-level tests for pin/unpin/presigned-url endpoints."""
import pytest
from datetime import datetime, timezone, timedelta
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
