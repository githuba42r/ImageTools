"""Tests for pin_image, unpin_image, effective_expires_at, and pin-aware cleanup."""
import pytest
from datetime import datetime, timedelta, timezone

from app.models.models import Image
from app.services.image_service import ImageService


def _make_image(user_id: str, image_id: str = "img-1") -> Image:
    return Image(
        id=image_id, user_id=user_id, original_filename="x.png",
        original_size=1, current_path="/tmp/x.png", current_size=1,
        width=1, height=1, format="PNG",
    )


# --- pin_image / unpin_image ----------------------------------------------- #

@pytest.mark.asyncio
async def test_pin_sets_expiry_for_unpinned(db_session, seeded_user):
    img = _make_image(seeded_user)
    db_session.add(img)
    await db_session.commit()
    before = datetime.utcnow()
    await ImageService.pin_image(db_session, img.id, duration_days=30)
    await db_session.refresh(img)
    delta = img.pin_expires_at - before
    assert timedelta(days=29, hours=23) < delta < timedelta(days=30, hours=1)


@pytest.mark.asyncio
async def test_pin_extends_a_shorter_existing_pin(db_session, seeded_user):
    img = _make_image(seeded_user)
    img.pin_expires_at = datetime.utcnow() + timedelta(days=10)
    db_session.add(img)
    await db_session.commit()
    await ImageService.pin_image(db_session, img.id, duration_days=30)
    await db_session.refresh(img)
    delta = img.pin_expires_at - datetime.utcnow()
    assert timedelta(days=29, hours=23) < delta < timedelta(days=30, hours=1)


@pytest.mark.asyncio
async def test_pin_does_not_shorten_a_longer_existing_pin(db_session, seeded_user):
    img = _make_image(seeded_user)
    img.pin_expires_at = datetime.utcnow() + timedelta(days=60)
    db_session.add(img)
    await db_session.commit()
    await ImageService.pin_image(db_session, img.id, duration_days=10)
    await db_session.refresh(img)
    delta = img.pin_expires_at - datetime.utcnow()
    assert timedelta(days=59) < delta < timedelta(days=61)


@pytest.mark.asyncio
async def test_pin_rejects_bad_duration(db_session, seeded_user):
    img = _make_image(seeded_user)
    db_session.add(img)
    await db_session.commit()
    with pytest.raises(ValueError):
        await ImageService.pin_image(db_session, img.id, duration_days=0)
    with pytest.raises(ValueError):
        await ImageService.pin_image(db_session, img.id, duration_days=10_000)


@pytest.mark.asyncio
async def test_unpin_clears_pin_expires_at(db_session, seeded_user):
    img = _make_image(seeded_user)
    img.pin_expires_at = datetime.utcnow() + timedelta(days=10)
    db_session.add(img)
    await db_session.commit()
    await ImageService.unpin_image(db_session, img.id)
    await db_session.refresh(img)
    assert img.pin_expires_at is None


@pytest.mark.asyncio
async def test_pin_returns_none_for_missing(db_session):
    assert await ImageService.pin_image(db_session, "missing", duration_days=7) is None
    assert await ImageService.unpin_image(db_session, "missing") is None


# --- effective_expires_at -------------------------------------------------- #

def test_effective_expires_at_uses_future_pin():
    now = datetime.utcnow()
    eff = ImageService.effective_expires_at(
        created_at=now - timedelta(days=2),
        pin_expires_at=now + timedelta(days=10),
        retention_days=30,
    )
    assert eff == (now + timedelta(days=10)) + timedelta(days=30)


def test_effective_expires_at_ignores_past_pin():
    now = datetime.utcnow()
    eff = ImageService.effective_expires_at(
        created_at=now - timedelta(days=2),
        pin_expires_at=now - timedelta(days=1),
        retention_days=30,
    )
    assert eff == (now - timedelta(days=2)) + timedelta(days=30)
