async def test_mcp_authorization_table_created(db_session):
    from app.models.models import McpAuthorization
    row = McpAuthorization(
        id="auth-1", user_id="u", token_hash="h", label="l"
    )
    db_session.add(row)
    await db_session.commit()
    assert row.id == "auth-1"


async def test_image_tags_default_empty(db_session, seeded_user):
    import json
    from app.models.models import Image
    img = Image(
        id="img-1", user_id=seeded_user, original_filename="x.png",
        original_size=10, current_path="/tmp/x.png", current_size=10,
        width=1, height=1, format="PNG",
    )
    db_session.add(img)
    await db_session.commit()
    await db_session.refresh(img)
    assert json.loads(img.tags) == []
