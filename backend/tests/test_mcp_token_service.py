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
async def test_list_returns_only_user_tokens(db_session, seeded_user):
    from app.models.models import User
    other = User(id="user-2", display_name="Other")
    db_session.add(other)
    await db_session.commit()

    await McpTokenService.create(db_session, seeded_user, label="a")
    await McpTokenService.create(db_session, seeded_user, label="b")
    await McpTokenService.create(db_session, other.id, label="other")

    rows = await McpTokenService.list_for_user(db_session, seeded_user)
    assert {r.label for r in rows} == {"a", "b"}


@pytest.mark.asyncio
async def test_list_excludes_revoked_tokens(db_session, seeded_user):
    _, keeper = await McpTokenService.create(db_session, seeded_user, label="keep")
    _, gone = await McpTokenService.create(db_session, seeded_user, label="revoked")
    await McpTokenService.revoke(db_session, gone.id, seeded_user)

    rows = await McpTokenService.list_for_user(db_session, seeded_user)
    assert {r.label for r in rows} == {"keep"}


@pytest.mark.asyncio
async def test_revoke_rejects_cross_user_request(db_session, seeded_user):
    """Critical auth invariant: a user cannot revoke another user's token by id."""
    from app.models.models import User
    attacker = User(id="attacker", display_name="Mallory")
    db_session.add(attacker)
    await db_session.commit()

    token, row = await McpTokenService.create(db_session, seeded_user, label="victim")
    revoked = await McpTokenService.revoke(db_session, row.id, attacker.id)
    assert revoked is False

    # Token must still validate — the revoke was silently rejected.
    user_id = await McpTokenService.validate(db_session, token)
    assert user_id == seeded_user


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["", "bearer_foo", "imt", "IMT_upper"])
async def test_validate_rejects_missing_or_wrong_prefix(db_session, bad):
    assert await McpTokenService.validate(db_session, bad) is None
