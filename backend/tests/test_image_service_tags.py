import pytest
from app.services.image_service import ImageService, normalize_tag


def test_normalize_tag_trims_and_returns_value():
    assert normalize_tag("  POS-table-service  ") == "POS-table-service"


def test_normalize_tag_returns_none_for_empty_or_whitespace():
    assert normalize_tag("") is None
    assert normalize_tag("   ") is None
    assert normalize_tag(None) is None


def test_normalize_tag_truncates_to_64_chars():
    long_tag = "a" * 100
    assert len(normalize_tag(long_tag)) == 64


async def test_get_tags_returns_empty_for_new_image(db_session, seeded_user):
    from app.models.models import Image
    img = Image(
        id="i1", user_id=seeded_user, original_filename="x.png",
        original_size=1, current_path="/tmp/x.png", current_size=1,
        width=1, height=1, format="PNG",
    )
    db_session.add(img)
    await db_session.commit()
    assert ImageService.get_tags(img) == []


async def test_set_tags_dedupes_and_preserves_case(db_session, seeded_user):
    from app.models.models import Image
    img = Image(
        id="i1", user_id=seeded_user, original_filename="x.png",
        original_size=1, current_path="/tmp/x.png", current_size=1,
        width=1, height=1, format="PNG",
    )
    db_session.add(img)
    await db_session.commit()
    ImageService.set_tags(img, ["POS", "pos", "  POS  "])
    await db_session.commit()
    await db_session.refresh(img)
    # Case preserved on the first occurrence; case-insensitive dedupe.
    assert ImageService.get_tags(img) == ["POS"]
