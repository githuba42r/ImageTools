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

    test_app = FastAPI()
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
