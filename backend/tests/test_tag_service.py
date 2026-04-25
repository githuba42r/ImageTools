import json
import pytest
from datetime import datetime, timedelta, timezone
from app.models.models import Image
from app.services.tag_service import TagService


async def test_list_user_tags_orders_by_recent_use(db_session, seeded_user):
    now = datetime.now(timezone.utc)
    # Older "alpha"
    db_session.add(Image(
        id="i1", user_id=seeded_user, original_filename="a.png",
        original_size=1, current_path="/tmp/a", current_size=1,
        width=1, height=1, format="PNG",
        tags=json.dumps(["alpha"]),
        created_at=now - timedelta(days=2),
    ))
    # Newer "beta"
    db_session.add(Image(
        id="i2", user_id=seeded_user, original_filename="b.png",
        original_size=1, current_path="/tmp/b", current_size=1,
        width=1, height=1, format="PNG",
        tags=json.dumps(["beta"]),
        created_at=now - timedelta(days=1),
    ))
    # Newest, two tags
    db_session.add(Image(
        id="i3", user_id=seeded_user, original_filename="c.png",
        original_size=1, current_path="/tmp/c", current_size=1,
        width=1, height=1, format="PNG",
        tags=json.dumps(["beta", "gamma"]),
        created_at=now,
    ))
    await db_session.commit()

    tags = await TagService.list_user_tags(db_session, seeded_user)
    names = [t["tag"] for t in tags]
    assert "beta" in names and "gamma" in names and "alpha" in names
    # alpha is the oldest, so it sorts last (DESC by max created_at).
    assert names[-1] == "alpha"
