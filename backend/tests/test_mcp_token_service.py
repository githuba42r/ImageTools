import pytest
from datetime import datetime, timezone
from app.services.mcp_token_service import McpTokenService


@pytest.mark.asyncio
async def test_create_returns_plaintext_and_stores_hash(db_session, seeded_user):
    token, row = await McpTokenService.create(db_session, seeded_user, label="laptop")
    assert token.startswith("imt_")
    assert len(token) > 20
    assert row.user_id == seeded_user
    assert row.label == "laptop"
    assert row.token_hash != token  # plaintext is not persisted


@pytest.mark.asyncio
async def test_validate_returns_user_id_for_valid_token(db_session, seeded_user):
    token, _ = await McpTokenService.create(db_session, seeded_user, label="l")
    user_id = await McpTokenService.validate(db_session, token)
    assert user_id == seeded_user


@pytest.mark.asyncio
async def test_validate_updates_last_used_at(db_session, seeded_user):
    token, row = await McpTokenService.create(db_session, seeded_user, label="l")
    assert row.last_used_at is None
    await McpTokenService.validate(db_session, token)
    await db_session.refresh(row)
    assert row.last_used_at is not None


@pytest.mark.asyncio
async def test_validate_rejects_unknown_token(db_session):
    user_id = await McpTokenService.validate(db_session, "imt_bogus")
    assert user_id is None


@pytest.mark.asyncio
async def test_validate_rejects_revoked_token(db_session, seeded_user):
    token, row = await McpTokenService.create(db_session, seeded_user, label="l")
    await McpTokenService.revoke(db_session, row.id, seeded_user)
    user_id = await McpTokenService.validate(db_session, token)
    assert user_id is None


@pytest.mark.asyncio
async def test_list_returns_user_tokens_without_hash_or_plaintext(db_session, seeded_user):
    await McpTokenService.create(db_session, seeded_user, label="a")
    await McpTokenService.create(db_session, seeded_user, label="b")
    rows = await McpTokenService.list_for_user(db_session, seeded_user)
    assert {r.label for r in rows} == {"a", "b"}
