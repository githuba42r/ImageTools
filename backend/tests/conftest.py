"""Shared pytest fixtures for backend tests."""
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.database import Base
from app.models import models  # noqa: F401 - ensure models are registered on Base


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_user(db_session: AsyncSession) -> str:
    from app.models.models import User
    user = User(id="user-1", display_name="Test User")
    db_session.add(user)
    await db_session.commit()
    return user.id


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """ASGI client over a minimal FastAPI app — avoids importing app.main.

    app.main wires in the MCP server and the websocket manager, neither of
    which is needed (or trivially importable) for endpoint-level tests. We
    register only the routers under test.
    """
    from fastapi import FastAPI
    from httpx import AsyncClient, ASGITransport
    from app.core.database import get_db
    from app.api.v1.endpoints import images, sharing
    from app.core.config import settings

    # Reset slowapi state so tests that change RATE_LIMIT_IMAGE_ACCESS via
    # monkeypatch start with a clean per-IP counter.
    from app.core.rate_limit import get_limiter, reset_for_tests
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    reset_for_tests()

    test_app = FastAPI()
    test_app.state.limiter = get_limiter()
    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    test_app.add_middleware(SlowAPIMiddleware)
    test_app.include_router(images.router, prefix=settings.API_PREFIX)
    test_app.include_router(sharing.router, prefix=settings.API_PREFIX)

    # Conditionally include routers that we'll add in later tasks. Each is
    # guarded so this fixture stays usable across the whole feature branch.
    try:
        from app.api.endpoints import presigned as presigned_module  # noqa: F401
        test_app.include_router(presigned_module.router)
    except ImportError:
        pass
    try:
        from app.api.endpoints import share_view as share_view_module  # noqa: F401
        test_app.include_router(share_view_module.router)
    except ImportError:
        pass

    async def _override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def seeded_image(db_session: AsyncSession, seeded_user) -> dict:
    from app.models.models import Image
    img = Image(
        id="test-img-1", user_id=seeded_user, original_filename="x.png",
        original_size=10, current_path="/tmp/x.png", current_size=10,
        width=10, height=10, format="PNG",
    )
    db_session.add(img)
    await db_session.commit()
    return {"id": img.id, "user_id": img.user_id}


# --- OAuth2 test fixtures -------------------------------------------------
import json
import time
from email.utils import format_datetime
from datetime import datetime, timezone, timedelta

import httpx
import jwt as _jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


@pytest.fixture(scope="session")
def oauth2_keypair():
    """Generate an RSA-2048 keypair once per test session."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return {"private_pem": private_pem, "public_pem": public_pem}


@pytest.fixture
def make_jwt(oauth2_keypair):
    """Factory: build an RS256-signed JWT with vinCreative-shaped claims."""
    def _make(
        email="philg@aspedia.net",
        fullname="Phil G",
        expires_in_seconds=3600,
        extra=None,
    ):
        exp_dt = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
        claims = {
            "user_id": "1",
            "email": email,
            "name": {"fullname": fullname} if fullname else {},
            "siteid": "test.example",
            "timestamp": format_datetime(datetime.now(timezone.utc)),
            "expires": format_datetime(exp_dt),
        }
        if extra:
            claims.update(extra)
        return _jwt.encode(claims, oauth2_keypair["private_pem"], algorithm="RS256")
    return _make


@pytest.fixture
def idp_mock_transport(oauth2_keypair):
    """httpx.MockTransport that stands in for the OAuth2 IdP.

    State is mutable via the returned dict so tests can stage a specific
    JWT or simulate provider errors.
    """
    state = {
        "next_jwt": None,                       # set per-test
        "key_pem": oauth2_keypair["public_pem"],
        "key_calls": 0,
        "token_calls": 0,
        "force_token_status": None,             # e.g. 500 to simulate IdP failure
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/get-key"):
            state["key_calls"] += 1
            return httpx.Response(200, text=state["key_pem"])
        if request.url.path.endswith("/oauth2/jwttoken"):
            state["token_calls"] += 1
            if state["force_token_status"]:
                return httpx.Response(state["force_token_status"], text="forced")
            if not state["next_jwt"]:
                return httpx.Response(400, json={"error": "no jwt staged"})
            return httpx.Response(200, json={"access_token": state["next_jwt"]})
        return httpx.Response(404)

    return {"transport": httpx.MockTransport(handler), "state": state}
