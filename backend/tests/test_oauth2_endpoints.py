import time
import urllib.parse

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.core.config import settings
from app.api.v1.endpoints import oauth2 as oauth2_endpoints
from app.api.v1.endpoints.oauth2 import STATE_COOKIE_NAME
from app.services import oauth2_service, session_service


@pytest.fixture(autouse=True)
def oauth2_settings(monkeypatch):
    monkeypatch.setattr(settings, "OAUTH2_AUTH_HOST", "https://idp.test")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_ID", "imagetools")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_SECRET", "shh")
    monkeypatch.setattr(settings, "OAUTH2_SCOPE", "auth")
    monkeypatch.setattr(settings, "INSTANCE_URL", "https://app.test")
    monkeypatch.setattr(settings, "SESSION_SECRET_KEY", "x" * 64)


@pytest_asyncio.fixture
async def client():
    app = FastAPI()
    app.include_router(oauth2_endpoints.router, prefix="/api/v1")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as ac:
        yield ac


async def test_connect_sets_state_cookie_and_redirects(client):
    r = await client.get("/api/v1/oauth2/connect")
    assert r.status_code == 302
    loc = r.headers["location"]
    assert loc.startswith("https://idp.test/oauth2/authorize?")
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query)
    assert qs["client_id"] == ["imagetools"]
    assert qs["scope"] == ["auth"]
    assert qs["redirect_uri"] == ["https://app.test/api/v1/oauth2/callback"]
    assert "state" in qs and qs["state"][0]
    # State cookie set
    assert "imagetools_oauth_state" in r.cookies
    # And the cookie's state matches the query state
    parsed = session_service.verify_state(r.cookies["imagetools_oauth_state"], max_age=300)
    assert parsed is not None
    assert parsed["s"] == qs["state"][0]
    assert parsed["r"] == "/"   # default return path


async def test_connect_honours_return_query(client):
    r = await client.get("/api/v1/oauth2/connect?return=/images")
    parsed = session_service.verify_state(r.cookies["imagetools_oauth_state"], max_age=300)
    assert parsed["r"] == "/images"


async def test_connect_rejects_absolute_url_return(client):
    r = await client.get("/api/v1/oauth2/connect?return=https://evil.com/x")
    parsed = session_service.verify_state(r.cookies["imagetools_oauth_state"], max_age=300)
    assert parsed["r"] == "/"


async def test_connect_rejects_scheme_relative_return(client):
    r = await client.get("/api/v1/oauth2/connect?return=//evil.com/x")
    parsed = session_service.verify_state(r.cookies["imagetools_oauth_state"], max_age=300)
    assert parsed["r"] == "/"


async def test_callback_happy_path_sets_session_cookie(client, idp_mock_transport, make_jwt, monkeypatch):
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    state = idp_mock_transport["state"]
    state["next_jwt"] = make_jwt(email="happy@x.test", fullname="Happy User")

    # Simulate the prior /connect by minting a state cookie ourselves
    state_token = session_service.sign_state({"s": "S1", "r": "/dashboard"})

    r = await client.get(
        "/api/v1/oauth2/callback?code=AC&state=S1",
        cookies={STATE_COOKIE_NAME: state_token},
    )
    assert r.status_code == 302
    assert r.headers["location"] == "/dashboard"
    # State cookie cleared (set with Max-Age=0)
    sc = r.headers.get_list("set-cookie")
    assert any("imagetools_oauth_state=" in h and ("Max-Age=0" in h or "max-age=0" in h.lower()) for h in sc)
    # Session cookie set
    assert "imagetools_session" in r.cookies
    payload = session_service.verify_session(r.cookies["imagetools_session"], max_age=24 * 3600)
    assert payload["u"] == "happy@x.test"
    assert payload["d"] == "Happy User"
    assert payload["exp"] > time.time()


async def test_callback_state_mismatch(client):
    state_token = session_service.sign_state({"s": "EXPECTED", "r": "/"})
    r = await client.get(
        "/api/v1/oauth2/callback?code=AC&state=WRONG",
        cookies={STATE_COOKIE_NAME: state_token},
    )
    assert r.status_code == 302
    assert "login_error=state_mismatch" in r.headers["location"]


async def test_callback_missing_state_cookie(client):
    r = await client.get("/api/v1/oauth2/callback?code=AC&state=ANY")
    assert r.status_code == 302
    assert "login_error=state_mismatch" in r.headers["location"]


async def test_callback_provider_error_passed_through(client):
    state_token = session_service.sign_state({"s": "S1", "r": "/"})
    r = await client.get(
        "/api/v1/oauth2/callback?error=access_denied",
        cookies={STATE_COOKIE_NAME: state_token},
    )
    assert r.status_code == 302
    assert "login_error=access_denied" in r.headers["location"]


async def test_callback_jwt_missing_email_surfaces_token_invalid(client, idp_mock_transport, oauth2_keypair, monkeypatch):
    import jwt as pyjwt
    from email.utils import format_datetime
    from datetime import datetime, timezone, timedelta
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    bad_claims = {
        "user_id": "1",
        "name": {"fullname": "X"},
        "expires": format_datetime(datetime.now(timezone.utc) + timedelta(hours=1)),
    }
    idp_mock_transport["state"]["next_jwt"] = pyjwt.encode(
        bad_claims, oauth2_keypair["private_pem"], algorithm="RS256"
    )
    state_token = session_service.sign_state({"s": "S1", "r": "/"})
    r = await client.get(
        "/api/v1/oauth2/callback?code=AC&state=S1",
        cookies={STATE_COOKIE_NAME: state_token},
    )
    assert r.status_code == 302
    assert "login_error=token_invalid" in r.headers["location"]


async def test_callback_idp_unreachable(client, idp_mock_transport, monkeypatch):
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    idp_mock_transport["state"]["force_token_status"] = 503
    state_token = session_service.sign_state({"s": "S1", "r": "/"})
    r = await client.get(
        "/api/v1/oauth2/callback?code=AC&state=S1",
        cookies={STATE_COOKIE_NAME: state_token},
    )
    assert r.status_code == 302
    assert "login_error=idp_unreachable" in r.headers["location"]


async def test_logout_clears_session_cookie(client):
    session_cookie = session_service.sign_session({"u": "a@b.c", "d": "A", "exp": int(time.time()) + 60})
    r = await client.post("/api/v1/oauth2/logout", cookies={"imagetools_session": session_cookie})
    assert r.status_code == 204
    sc = r.headers.get_list("set-cookie")
    assert any("imagetools_session=" in h and ("max-age=0" in h.lower() or "expires=Thu, 01 Jan 1970" in h) for h in sc)


async def test_logout_without_session_is_idempotent(client):
    r = await client.post("/api/v1/oauth2/logout")
    assert r.status_code == 204


async def test_me_with_valid_cookie_returns_identity(client):
    session_cookie = session_service.sign_session({"u": "me@x.test", "d": "Me X", "exp": int(time.time()) + 60})
    r = await client.get("/api/v1/oauth2/me", cookies={"imagetools_session": session_cookie})
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "me@x.test"
    assert body["display_name"] == "Me X"
    assert body["expires_at"] > time.time()


async def test_me_without_cookie_returns_401(client):
    r = await client.get("/api/v1/oauth2/me")
    assert r.status_code == 401
