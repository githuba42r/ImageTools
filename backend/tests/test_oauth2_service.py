import time

import httpx
import pytest

from app.core.config import settings
from app.services import oauth2_service


@pytest.fixture(autouse=True)
def reset_key_cache():
    oauth2_service._PUBLIC_KEY_CACHE["key"] = None
    oauth2_service._PUBLIC_KEY_CACHE["fetched_at"] = 0
    yield


@pytest.fixture(autouse=True)
def oauth2_settings(monkeypatch):
    monkeypatch.setattr(settings, "OAUTH2_AUTH_HOST", "https://idp.test")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_ID", "imagetools")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_SECRET", "shh")
    monkeypatch.setattr(settings, "OAUTH2_SCOPE", "auth")
    monkeypatch.setattr(settings, "OAUTH2_PUBLIC_KEY_CACHE_SECONDS", 3600)


@pytest.mark.asyncio
async def test_exchange_code_returns_jwt(idp_mock_transport, make_jwt, monkeypatch):
    state = idp_mock_transport["state"]
    state["next_jwt"] = make_jwt()
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    token = await oauth2_service.exchange_code("abc-code", "https://app/api/v1/oauth2/callback")
    assert token == state["next_jwt"]
    assert state["token_calls"] == 1


@pytest.mark.asyncio
async def test_exchange_code_idp_5xx_raises(idp_mock_transport, monkeypatch):
    state = idp_mock_transport["state"]
    state["force_token_status"] = 500
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    with pytest.raises(httpx.HTTPStatusError):
        await oauth2_service.exchange_code("abc-code", "https://app/cb")


@pytest.mark.asyncio
async def test_fetch_public_key_caches(idp_mock_transport, monkeypatch):
    state = idp_mock_transport["state"]
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    k1 = await oauth2_service.fetch_public_key()
    k2 = await oauth2_service.fetch_public_key()
    assert k1 == k2 == state["key_pem"]
    assert state["key_calls"] == 1   # second call was a cache hit


@pytest.mark.asyncio
async def test_fetch_public_key_force_refresh_bypasses_cache(idp_mock_transport, monkeypatch):
    state = idp_mock_transport["state"]
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    await oauth2_service.fetch_public_key()
    await oauth2_service.fetch_public_key(force_refresh=True)
    assert state["key_calls"] == 2


@pytest.mark.asyncio
async def test_fetch_public_key_respects_ttl(idp_mock_transport, monkeypatch):
    state = idp_mock_transport["state"]
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    monkeypatch.setattr(settings, "OAUTH2_PUBLIC_KEY_CACHE_SECONDS", 0)  # always expire
    await oauth2_service.fetch_public_key()
    await oauth2_service.fetch_public_key()
    assert state["key_calls"] == 2


@pytest.mark.asyncio
async def test_verify_jwt_valid_returns_identity(idp_mock_transport, make_jwt, monkeypatch):
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    token = make_jwt(email="user@x.test", fullname="User X")
    claims = await oauth2_service.verify_jwt(token)
    assert claims["email"] == "user@x.test"
    assert claims["fullname"] == "User X"
    assert claims["expires_epoch"] > time.time()


@pytest.mark.asyncio
async def test_verify_jwt_missing_email_raises(idp_mock_transport, oauth2_keypair, monkeypatch):
    import jwt as pyjwt
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    # Build a JWT with no email
    from email.utils import format_datetime
    from datetime import datetime, timezone, timedelta
    claims = {
        "user_id": "1",
        "name": {"fullname": "Nameless"},
        "expires": format_datetime(datetime.now(timezone.utc) + timedelta(hours=1)),
    }
    token = pyjwt.encode(claims, oauth2_keypair["private_pem"], algorithm="RS256")
    with pytest.raises(ValueError, match="email"):
        await oauth2_service.verify_jwt(token)


@pytest.mark.asyncio
async def test_verify_jwt_expired_raises(idp_mock_transport, make_jwt, monkeypatch):
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    token = make_jwt(expires_in_seconds=-10)
    with pytest.raises(ValueError, match="expired"):
        await oauth2_service.verify_jwt(token)


@pytest.mark.asyncio
async def test_verify_jwt_retries_on_signature_failure(idp_mock_transport, oauth2_keypair, monkeypatch):
    """First decode fails (stale key), force-refresh, second decode succeeds."""
    import jwt as pyjwt
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from email.utils import format_datetime
    from datetime import datetime, timezone, timedelta

    # Generate a SECOND keypair: cached public key is the old one, but the JWT is signed by the new one.
    new_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    new_private_pem = new_private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    new_public_pem = new_private.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    # Token is signed by the NEW key
    claims = {
        "user_id": "1",
        "email": "rot@x.test",
        "name": {"fullname": "Rot User"},
        "expires": format_datetime(datetime.now(timezone.utc) + timedelta(hours=1)),
    }
    token = pyjwt.encode(claims, new_private_pem, algorithm="RS256")

    # IdP key endpoint starts serving the OLD key, then flips to the NEW key on the second call
    state = idp_mock_transport["state"]
    # Prime cache with OLD key
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    await oauth2_service.fetch_public_key()  # caches old key
    # Now flip IdP to serve the new key
    state["key_pem"] = new_public_pem

    out = await oauth2_service.verify_jwt(token)
    assert out["email"] == "rot@x.test"
    # Two key fetches total: one to prime, one forced after signature failure
    assert state["key_calls"] == 2
