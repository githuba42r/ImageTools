"""Tests for InternalAuthMiddleware behaviour in OAuth2 vs Authelia modes.

When OAuth2 mode is active, OAuth2SessionMiddleware populates
request.state.remote_user / remote_name from the signed session cookie.
InternalAuthMiddleware must NOT read or overwrite those values from
Remote-User/Remote-Name request headers — Authelia isn't in front of the
backend in OAuth2 mode, and trusting those headers would let a client spoof
identity.

The X-Internal-Auth defense-in-depth path is independent of identity source
and must still be enforced when REQUIRE_INTERNAL_AUTH is on.
"""
import pytest
import pytest_asyncio
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.middleware.internal_auth import InternalAuthMiddleware


def _build_app():
    app = FastAPI()
    app.add_middleware(InternalAuthMiddleware)

    @app.get("/probe")
    async def probe(request: Request):
        return {
            "remote_user": getattr(request.state, "remote_user", None),
            "remote_name": getattr(request.state, "remote_name", None),
        }

    return app


async def test_oauth2_off_reads_authelia_headers(monkeypatch):
    monkeypatch.setattr(settings, "OAUTH2_AUTH_HOST", "")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_ID", "")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "REQUIRE_INTERNAL_AUTH", False)

    transport = ASGITransport(app=_build_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/probe",
            headers={"Remote-User": "alice", "Remote-Name": "Alice"},
        )
    assert r.status_code == 200
    assert r.json() == {"remote_user": "alice", "remote_name": "Alice"}


async def test_oauth2_on_does_not_overwrite_existing_request_state(monkeypatch):
    """When OAuth2 mode is on, InternalAuthMiddleware must NOT read or overwrite remote_user/name."""
    monkeypatch.setattr(settings, "OAUTH2_AUTH_HOST", "https://idp.test")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_ID", "cid")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_SECRET", "sec")
    monkeypatch.setattr(settings, "REQUIRE_INTERNAL_AUTH", False)

    # Simulate a prior middleware (e.g. OAuth2SessionMiddleware) having set state.
    # Starlette's add_middleware/decorator both PREPEND to user_middleware, so the
    # LAST one registered is the OUTERMOST. Register InternalAuthMiddleware first
    # so it ends up innermost; pre_set added via the decorator becomes outermost
    # and runs BEFORE InternalAuthMiddleware sees the request.
    app = FastAPI()
    app.add_middleware(InternalAuthMiddleware)

    @app.middleware("http")
    async def pre_set(request: Request, call_next):
        request.state.remote_user = "from-oauth2@x.test"
        request.state.remote_name = "From OAuth2"
        return await call_next(request)

    @app.get("/probe")
    async def probe(request: Request):
        return {
            "remote_user": getattr(request.state, "remote_user", None),
            "remote_name": getattr(request.state, "remote_name", None),
        }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Inject Authelia headers — they MUST NOT overwrite the pre-set state
        r = await ac.get(
            "/probe",
            headers={"Remote-User": "spoof@x.test", "Remote-Name": "Spoofer"},
        )
    assert r.status_code == 200
    assert r.json() == {"remote_user": "from-oauth2@x.test", "remote_name": "From OAuth2"}


async def test_internal_auth_secret_still_enforced_in_oauth2_mode(monkeypatch):
    """Defense-in-depth path is independent of identity-source mode."""
    monkeypatch.setattr(settings, "OAUTH2_AUTH_HOST", "https://idp.test")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_ID", "cid")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_SECRET", "sec")
    monkeypatch.setattr(settings, "REQUIRE_INTERNAL_AUTH", True)
    monkeypatch.setattr(settings, "INTERNAL_AUTH_SECRET", "shared-secret")

    transport = ASGITransport(app=_build_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/probe")
        assert r.status_code == 403
        r = await ac.get("/probe", headers={"X-Internal-Auth": "shared-secret"})
        assert r.status_code == 200


async def test_oauth2_callback_path_bypasses_internal_auth_in_hardened_mode(monkeypatch):
    """Even with REQUIRE_INTERNAL_AUTH=true, the OAuth2 endpoints must be reachable
    so the browser callback redirect works."""
    monkeypatch.setattr(settings, "REQUIRE_INTERNAL_AUTH", True)
    monkeypatch.setattr(settings, "INTERNAL_AUTH_SECRET", "shared-secret")

    app = FastAPI()
    app.add_middleware(InternalAuthMiddleware)

    @app.get("/api/v1/oauth2/callback")
    async def callback_stub():
        return {"ok": True}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v1/oauth2/callback")
    assert r.status_code == 200
