async def test_mcp_authorization_table_created(db_session):
    from app.models.models import McpAuthorization
    row = McpAuthorization(
        id="auth-1", user_id="u", token_hash="h", label="l"
    )
    db_session.add(row)
    await db_session.commit()
    assert row.id == "auth-1"
