# MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an MCP server to ImageTools that lets Claude Code (and other MCP clients) retrieve a user's recent screenshots over both Streamable HTTP and stdio transports, authenticated with personal access tokens minted from the web UI.

**Architecture:** One Python package `mcp-server/` containing transport-agnostic tool handlers behind a `BackendClient` protocol. The Streamable HTTP transport is mounted at `/mcp/` inside the existing FastAPI backend (shared container, in-process DB access). The stdio entry point is a separate CLI that calls the same ImageTools REST endpoints over HTTP. Auth is a long-lived personal access token stored as sha256 in a new `mcp_authorizations` table and minted from a new web UI screen.

**Tech Stack:** FastAPI, SQLAlchemy (async), SQLite, the `mcp` Python SDK (`FastMCP`, Streamable HTTP), `httpx`, Vue 3 + Pinia, `pytest` + `pytest-asyncio`.

**Spec:** `docs/superpowers/specs/2026-04-23-mcp-server-design.md`

---

## File Structure

```
backend/
├── app/
│   ├── models/models.py                           # + McpAuthorization model
│   ├── services/mcp_token_service.py              # NEW: hash/create/validate/revoke
│   ├── schemas/mcp_token.py                       # NEW: pydantic schemas
│   ├── api/v1/endpoints/mcp_tokens.py             # NEW: CRUD endpoints
│   └── main.py                                    # + mount MCP routes + token router
└── tests/                                         # NEW dir (project has no tests yet)
    ├── __init__.py
    ├── conftest.py                                # pytest fixtures (in-memory DB)
    ├── test_mcp_token_service.py
    └── test_mcp_tools.py

mcp-server/                                        # NEW top-level package
├── README.md                                      # setup docs (both transports)
├── pyproject.toml
└── src/mcp_server/
    ├── __init__.py
    ├── backend.py                                 # BackendClient protocol
    ├── backend_local.py                           # in-process impl (HTTP transport)
    ├── backend_http.py                            # REST impl (stdio transport)
    ├── tools.py                                   # shared tool handlers
    ├── server.py                                  # FastMCP instance + TokenVerifier
    ├── http_app.py                                # Starlette app + lifespan helper
    └── stdio.py                                   # stdio CLI entry point

frontend/src/components/McpTokenManager.vue        # NEW: UI for minting/revoking
frontend/src/App.vue                               # + link/section to MCP tokens
```

---

## Task 1: Set up test infrastructure and add `McpAuthorization` model

**Files:**
- Create: `backend/tests/__init__.py` (empty)
- Create: `backend/tests/conftest.py`
- Modify: `backend/app/models/models.py` (append new class)

The project has no tests today but `pytest` and `pytest-asyncio` are already in `requirements.txt`. We add a minimal `conftest.py` with an in-memory SQLite fixture. `Base.metadata.create_all` at backend startup auto-creates new tables, so no explicit migration is needed.

- [ ] **Step 1: Create `backend/tests/__init__.py`** as an empty file.

- [ ] **Step 2: Create `backend/tests/conftest.py`:**

```python
"""Shared pytest fixtures for backend tests."""
import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.database import Base
from app.models import models  # noqa: F401 - ensure models are registered on Base


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


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
```

- [ ] **Step 3: Add `McpAuthorization` to `backend/app/models/models.py`** (append at end of file):

```python
class McpAuthorization(Base):
    """
    Personal access tokens for MCP clients (e.g. Claude Code).

    Long-lived tokens minted from the web UI, presented as Bearer tokens
    to the MCP server. The plaintext token is shown once at creation;
    only the sha256 hash is persisted.
    """
    __tablename__ = "mcp_authorizations"

    id = Column(String, primary_key=True, index=True)  # UUID
    user_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String, nullable=False, unique=True, index=True)
    label = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 4: Smoke-test the model** by running pytest with a trivial import test:

Create `backend/tests/test_models_smoke.py`:
```python
import pytest

@pytest.mark.asyncio
async def test_mcp_authorization_table_created(db_session):
    from app.models.models import McpAuthorization
    row = McpAuthorization(
        id="auth-1", user_id="u", token_hash="h", label="l"
    )
    db_session.add(row)
    await db_session.commit()
    assert row.id == "auth-1"
```

Run: `cd backend && pytest tests/test_models_smoke.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit.**

```bash
git add backend/tests backend/app/models/models.py
git commit -m "feat(backend): add McpAuthorization model and pytest scaffolding"
```

---

## Task 2: Token service — hash, create, validate, revoke

**Files:**
- Create: `backend/app/services/mcp_token_service.py`
- Create: `backend/tests/test_mcp_token_service.py`

Token lifecycle: `create` generates 32 random bytes base64url-encoded (~43 chars) with an `imt_` prefix, stores sha256 hash, returns plaintext once. `validate` hashes the presented token and looks it up (rejects revoked). `revoke` sets `revoked_at`. All writes commit.

- [ ] **Step 1: Write the failing tests** at `backend/tests/test_mcp_token_service.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail.**

Run: `cd backend && pytest tests/test_mcp_token_service.py -v`
Expected: ImportError / ModuleNotFoundError for `app.services.mcp_token_service`.

- [ ] **Step 3: Implement the service** at `backend/app/services/mcp_token_service.py`:

```python
"""Personal access token lifecycle for MCP clients."""
import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import McpAuthorization

TOKEN_PREFIX = "imt_"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _generate_token() -> str:
    # 32 random bytes → 43 url-safe chars; prefix makes the token self-describing
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


class McpTokenService:
    @staticmethod
    async def create(
        db: AsyncSession, user_id: str, label: str
    ) -> tuple[str, McpAuthorization]:
        """Create a new token. Returns (plaintext_token, row). Plaintext is
        shown to the user once and not stored anywhere else."""
        token = _generate_token()
        row = McpAuthorization(
            id=str(uuid.uuid4()),
            user_id=user_id,
            token_hash=_hash(token),
            label=label,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return token, row

    @staticmethod
    async def validate(db: AsyncSession, token: str) -> Optional[str]:
        """Return user_id if the token is valid and not revoked. Updates
        last_used_at as a side-effect."""
        if not token or not token.startswith(TOKEN_PREFIX):
            return None
        result = await db.execute(
            select(McpAuthorization).where(
                McpAuthorization.token_hash == _hash(token),
                McpAuthorization.revoked_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        await db.execute(
            update(McpAuthorization)
            .where(McpAuthorization.id == row.id)
            .values(last_used_at=datetime.now(timezone.utc))
        )
        await db.commit()
        return row.user_id

    @staticmethod
    async def revoke(db: AsyncSession, token_id: str, user_id: str) -> bool:
        """Revoke a token belonging to user_id. Returns True if revoked."""
        result = await db.execute(
            update(McpAuthorization)
            .where(
                McpAuthorization.id == token_id,
                McpAuthorization.user_id == user_id,
                McpAuthorization.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def list_for_user(
        db: AsyncSession, user_id: str
    ) -> list[McpAuthorization]:
        """List all non-revoked tokens for a user, newest first."""
        result = await db.execute(
            select(McpAuthorization)
            .where(
                McpAuthorization.user_id == user_id,
                McpAuthorization.revoked_at.is_(None),
            )
            .order_by(McpAuthorization.created_at.desc())
        )
        return list(result.scalars().all())
```

- [ ] **Step 4: Run tests to verify they pass.**

Run: `cd backend && pytest tests/test_mcp_token_service.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit.**

```bash
git add backend/app/services/mcp_token_service.py backend/tests/test_mcp_token_service.py
git commit -m "feat(backend): mcp token service with hash/create/validate/revoke"
```

---

## Task 3: MCP tokens REST API endpoints

**Files:**
- Create: `backend/app/schemas/mcp_token.py`
- Create: `backend/app/api/v1/endpoints/mcp_tokens.py`
- Modify: `backend/app/main.py` (register router)

Four endpoints, all scoped by `user_id` in the path (matches existing conventions in `users.py`, `mobile.py`, `addon.py`):
- `POST /api/v1/users/{user_id}/mcp-tokens` — create, returns plaintext token ONCE
- `GET /api/v1/users/{user_id}/mcp-tokens` — list (no plaintext, no hash)
- `DELETE /api/v1/users/{user_id}/mcp-tokens/{token_id}` — revoke

- [ ] **Step 1: Write schemas** at `backend/app/schemas/mcp_token.py`:

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class McpTokenCreate(BaseModel):
    label: str


class McpTokenCreateResponse(BaseModel):
    """Response for token creation — includes plaintext token exactly once."""
    id: str
    label: str
    token: str  # plaintext, shown once
    created_at: datetime


class McpTokenInfo(BaseModel):
    """Public info for a token (no plaintext, no hash)."""
    id: str
    label: str
    created_at: datetime
    last_used_at: Optional[datetime]
```

- [ ] **Step 2: Write endpoints** at `backend/app/api/v1/endpoints/mcp_tokens.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.mcp_token_service import McpTokenService
from app.schemas.mcp_token import (
    McpTokenCreate,
    McpTokenCreateResponse,
    McpTokenInfo,
)

router = APIRouter(prefix="/users/{user_id}/mcp-tokens", tags=["mcp-tokens"])


@router.post("", response_model=McpTokenCreateResponse)
async def create_mcp_token(
    user_id: str,
    payload: McpTokenCreate,
    db: AsyncSession = Depends(get_db),
):
    if not payload.label.strip():
        raise HTTPException(status_code=400, detail="label is required")
    token, row = await McpTokenService.create(db, user_id, payload.label.strip())
    return McpTokenCreateResponse(
        id=row.id, label=row.label, token=token, created_at=row.created_at
    )


@router.get("", response_model=list[McpTokenInfo])
async def list_mcp_tokens(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    rows = await McpTokenService.list_for_user(db, user_id)
    return [
        McpTokenInfo(
            id=r.id,
            label=r.label,
            created_at=r.created_at,
            last_used_at=r.last_used_at,
        )
        for r in rows
    ]


@router.delete("/{token_id}")
async def revoke_mcp_token(
    user_id: str,
    token_id: str,
    db: AsyncSession = Depends(get_db),
):
    ok = await McpTokenService.revoke(db, token_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="token not found or already revoked")
    return {"status": "revoked"}
```

- [ ] **Step 3: Register router in `backend/app/main.py`.**

Add the import near the other endpoint imports:
```python
from app.api.v1.endpoints import mcp_tokens
```

Add the `include_router` call alongside the existing ones (~line 115):
```python
app.include_router(mcp_tokens.router, prefix=settings.API_PREFIX, tags=["mcp-tokens"])
```

- [ ] **Step 4: Verify via manual curl** with the backend running:

```bash
# Assuming an existing user id; the frontend creates one on first visit
USER_ID=$(curl -s http://localhost:8082/api/v1/users -X POST \
  -H 'Content-Type: application/json' -d '{"display_name":"test"}' | jq -r .id)

# Create
curl -s -X POST http://localhost:8082/api/v1/users/$USER_ID/mcp-tokens \
  -H 'Content-Type: application/json' -d '{"label":"claude-code"}'
# Expected: {"id":"...","label":"claude-code","token":"imt_...","created_at":"..."}

# List
curl -s http://localhost:8082/api/v1/users/$USER_ID/mcp-tokens
# Expected: [{"id":"...","label":"claude-code",...,"last_used_at":null}]

# Revoke (use id from create output)
curl -s -X DELETE http://localhost:8082/api/v1/users/$USER_ID/mcp-tokens/<token_id>
# Expected: {"status":"revoked"}
```

- [ ] **Step 5: Commit.**

```bash
git add backend/app/schemas/mcp_token.py backend/app/api/v1/endpoints/mcp_tokens.py backend/app/main.py
git commit -m "feat(backend): REST endpoints for MCP personal access tokens"
```

---

## Task 4: Scaffold `mcp-server/` package

**Files:**
- Create: `mcp-server/pyproject.toml`
- Create: `mcp-server/README.md` (stub; filled in task 11)
- Create: `mcp-server/src/mcp_server/__init__.py` (empty)
- Create: `mcp-server/src/mcp_server/backend.py`

Add `mcp>=1.12` to the backend's `requirements.txt` too, because the HTTP transport runs inside the backend container.

- [ ] **Step 1: Add MCP SDK to `backend/requirements.txt`** (append):

```
# MCP server
mcp>=1.12.0
```

- [ ] **Step 2: Create `mcp-server/pyproject.toml`:**

```toml
[project]
name = "imagetools-mcp-server"
version = "0.1.0"
description = "MCP server for ImageTools screenshots"
requires-python = ">=3.11"
dependencies = [
  "mcp>=1.12.0",
  "httpx>=0.26.0",
]

[project.scripts]
imagetools-mcp-stdio = "mcp_server.stdio:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/mcp_server"]
```

- [ ] **Step 3: Create `mcp-server/README.md`** as a stub (expanded in Task 11):

```markdown
# ImageTools MCP Server

See `docs/superpowers/specs/2026-04-23-mcp-server-design.md` for the design.
Full setup instructions added in Task 11.
```

- [ ] **Step 4: Create `mcp-server/src/mcp_server/__init__.py`** (empty file).

- [ ] **Step 5: Create `mcp-server/src/mcp_server/backend.py` — the transport-agnostic backend abstraction:**

```python
"""Transport-agnostic abstraction over the ImageTools backend.

Two implementations:
  - backend_local.LocalBackendClient: runs in-process with the FastAPI backend,
    calls services/DB directly. Used by the HTTP transport.
  - backend_http.HttpBackendClient: calls the ImageTools REST API over HTTP.
    Used by the stdio transport.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ImageMeta:
    id: str
    original_filename: str
    created_at: str        # ISO 8601
    width: int
    height: int
    format: str            # e.g. "PNG", "JPEG"
    current_size: int


@dataclass(frozen=True)
class ImageBytes:
    meta: ImageMeta
    data: bytes
    mime_type: str         # e.g. "image/png"


class BackendClient(Protocol):
    async def list_user_images(self, user_id: str, limit: int) -> list[ImageMeta]:
        ...

    async def get_image(self, user_id: str, image_id: str) -> ImageBytes | None:
        """Return bytes + metadata, or None if not found / not owned by user."""
        ...
```

- [ ] **Step 6: Commit.**

```bash
git add mcp-server backend/requirements.txt
git commit -m "feat(mcp-server): scaffold package and BackendClient protocol"
```

---

## Task 5: Implement `LocalBackendClient` and `HttpBackendClient`

**Files:**
- Create: `mcp-server/src/mcp_server/backend_local.py`
- Create: `mcp-server/src/mcp_server/backend_http.py`

`LocalBackendClient` uses the existing `ImageService` and reads the file at `image.current_path`. `HttpBackendClient` calls the REST endpoints with a bearer token header.

- [ ] **Step 1: Implement `backend_local.py`:**

```python
"""In-process backend client used by the HTTP MCP transport.

Accesses the ImageTools DB and storage directly, because it runs in the
same process as the FastAPI backend.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, AsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.image_service import ImageService
from .backend import BackendClient, ImageBytes, ImageMeta


def _iso(dt) -> str:
    return dt.isoformat() if dt is not None else ""


def _mime_for(fmt: str) -> str:
    fmt = (fmt or "").lower()
    if fmt in ("jpg", "jpeg"):
        return "image/jpeg"
    return f"image/{fmt or 'png'}"


class LocalBackendClient:
    """Uses a session factory (NOT a single session) so each call gets a fresh
    session — matches FastAPI's Depends(get_db) pattern."""

    def __init__(self, session_factory: Callable[[], AsyncContextManager[AsyncSession]]):
        self._session_factory = session_factory

    async def list_user_images(self, user_id: str, limit: int) -> list[ImageMeta]:
        async with self._session_factory() as db:
            images = await ImageService.get_user_images(db, user_id)
        # ImageService returns newest-first already via created_at desc; take limit
        images = images[:limit]
        return [
            ImageMeta(
                id=img.id,
                original_filename=img.original_filename,
                created_at=_iso(img.created_at),
                width=img.width,
                height=img.height,
                format=img.format,
                current_size=img.current_size,
            )
            for img in images
        ]

    async def get_image(self, user_id: str, image_id: str) -> ImageBytes | None:
        async with self._session_factory() as db:
            img = await ImageService.get_image(db, image_id)
            if img is None or img.user_id != user_id:
                return None
            path = Path(img.current_path)
            if not path.exists():
                return None
            data = path.read_bytes()
            meta = ImageMeta(
                id=img.id,
                original_filename=img.original_filename,
                created_at=_iso(img.created_at),
                width=img.width,
                height=img.height,
                format=img.format,
                current_size=img.current_size,
            )
            return ImageBytes(meta=meta, data=data, mime_type=_mime_for(img.format))
```

> NOTE: If `ImageService.get_user_images` does not already order by `created_at DESC`, verify by reading `backend/app/services/image_service.py` before running. If the ordering is different, add a `.order_by(Image.created_at.desc())` in the service method or sort client-side in this file. (Sort client-side if modifying the service would affect other callers.)

- [ ] **Step 2: Implement `backend_http.py`:**

```python
"""REST-backed client used by the stdio MCP transport."""
from __future__ import annotations

import httpx

from .backend import BackendClient, ImageBytes, ImageMeta


def _mime_for(fmt: str) -> str:
    fmt = (fmt or "").lower()
    if fmt in ("jpg", "jpeg"):
        return "image/jpeg"
    return f"image/{fmt or 'png'}"


class HttpBackendClient:
    def __init__(self, base_url: str, token: str, timeout: float = 30.0):
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}"}
        self._client = httpx.AsyncClient(timeout=timeout, headers=self._headers)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def list_user_images(self, user_id: str, limit: int) -> list[ImageMeta]:
        r = await self._client.get(
            f"{self._base_url}/api/v1/images/user/{user_id}"
        )
        r.raise_for_status()
        images = r.json()[:limit]
        return [
            ImageMeta(
                id=img["id"],
                original_filename=img["original_filename"],
                created_at=img["created_at"],
                width=img["width"],
                height=img["height"],
                format=img["format"],
                current_size=img["current_size"],
            )
            for img in images
        ]

    async def get_image(self, user_id: str, image_id: str) -> ImageBytes | None:
        meta_r = await self._client.get(
            f"{self._base_url}/api/v1/images/{image_id}"
        )
        if meta_r.status_code == 404:
            return None
        meta_r.raise_for_status()
        meta_json = meta_r.json()
        if meta_json.get("user_id") != user_id:
            return None

        bytes_r = await self._client.get(
            f"{self._base_url}/api/v1/images/{image_id}/current"
        )
        bytes_r.raise_for_status()

        meta = ImageMeta(
            id=meta_json["id"],
            original_filename=meta_json["original_filename"],
            created_at=meta_json["created_at"],
            width=meta_json["width"],
            height=meta_json["height"],
            format=meta_json["format"],
            current_size=meta_json["current_size"],
        )
        return ImageBytes(
            meta=meta,
            data=bytes_r.content,
            mime_type=_mime_for(meta.format),
        )
```

- [ ] **Step 3: Commit.**

```bash
git add mcp-server/src/mcp_server/backend_local.py mcp-server/src/mcp_server/backend_http.py
git commit -m "feat(mcp-server): local and http backend client implementations"
```

---

## Task 6: Shared tool handlers + unit tests

**Files:**
- Create: `mcp-server/src/mcp_server/tools.py`
- Create: `backend/tests/test_mcp_tools.py`

The tool handlers take a `BackendClient`, a `user_id`, and tool arguments, and return structured results. They don't depend on `FastMCP` types — keeping them easy to test. The transport layer (Task 7) wraps them into FastMCP tools.

- [ ] **Step 1: Write the failing tests** at `backend/tests/test_mcp_tools.py`:

```python
import pytest
from mcp_server.backend import ImageBytes, ImageMeta
from mcp_server.tools import (
    list_recent_images,
    get_image,
    get_recent_images,
    MAX_LIST_COUNT,
    MAX_RECENT_COUNT,
)


class FakeBackend:
    def __init__(self, images: list[ImageMeta], bytes_map: dict[str, bytes]):
        self._images = images
        self._bytes = bytes_map

    async def list_user_images(self, user_id, limit):
        return self._images[:limit]

    async def get_image(self, user_id, image_id):
        for img in self._images:
            if img.id == image_id:
                data = self._bytes.get(image_id, b"")
                return ImageBytes(meta=img, data=data, mime_type="image/png")
        return None


def _img(i: int) -> ImageMeta:
    return ImageMeta(
        id=f"img-{i}",
        original_filename=f"file-{i}.png",
        created_at=f"2026-04-23T10:0{i}:00Z",
        width=100, height=100, format="PNG", current_size=1000 + i,
    )


@pytest.mark.asyncio
async def test_list_recent_clamps_count_to_max():
    backend = FakeBackend([_img(i) for i in range(100)], {})
    result = await list_recent_images(backend, "u", count=9999)
    assert len(result["images"]) == MAX_LIST_COUNT
    assert result["clamped"] is True


@pytest.mark.asyncio
async def test_list_recent_returns_newest_first():
    backend = FakeBackend([_img(3), _img(2), _img(1)], {})
    result = await list_recent_images(backend, "u", count=10)
    assert [i["id"] for i in result["images"]] == ["img-3", "img-2", "img-1"]


@pytest.mark.asyncio
async def test_get_image_returns_bytes_and_meta():
    backend = FakeBackend([_img(1)], {"img-1": b"PNGDATA"})
    result = await get_image(backend, "u", "img-1")
    assert result["meta"]["id"] == "img-1"
    assert result["data"] == b"PNGDATA"
    assert result["mime_type"] == "image/png"


@pytest.mark.asyncio
async def test_get_image_missing_raises_not_found():
    backend = FakeBackend([], {})
    with pytest.raises(LookupError):
        await get_image(backend, "u", "nope")


@pytest.mark.asyncio
async def test_get_recent_caps_count():
    backend = FakeBackend([_img(i) for i in range(10)], {f"img-{i}": b"X" for i in range(10)})
    result = await get_recent_images(backend, "u", count=999)
    assert len(result["images"]) == MAX_RECENT_COUNT
```

- [ ] **Step 2: Run tests to verify they fail.**

Run: `cd backend && PYTHONPATH=../mcp-server/src pytest tests/test_mcp_tools.py -v`
Expected: ImportError on `mcp_server.tools`.

- [ ] **Step 3: Implement `mcp-server/src/mcp_server/tools.py`:**

```python
"""Transport-agnostic MCP tool implementations."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .backend import BackendClient, ImageMeta

MAX_LIST_COUNT = 50
MAX_RECENT_COUNT = 6
DEFAULT_LIST_COUNT = 10
DEFAULT_RECENT_COUNT = 1


def _clamp(value: int, lo: int, hi: int) -> tuple[int, bool]:
    clamped = max(lo, min(value, hi))
    return clamped, clamped != value


def _meta_dict(m: ImageMeta) -> dict[str, Any]:
    return asdict(m)


async def list_recent_images(
    backend: BackendClient, user_id: str, count: int = DEFAULT_LIST_COUNT
) -> dict[str, Any]:
    """Return metadata for the N most recent images, newest first."""
    clamped, was_clamped = _clamp(count, 1, MAX_LIST_COUNT)
    metas = await backend.list_user_images(user_id, clamped)
    return {
        "images": [_meta_dict(m) for m in metas],
        "clamped": was_clamped,
    }


async def get_image(
    backend: BackendClient, user_id: str, image_id: str
) -> dict[str, Any]:
    """Return bytes + metadata for one image. Raises LookupError if not found."""
    result = await backend.get_image(user_id, image_id)
    if result is None:
        raise LookupError(f"image not found: {image_id}")
    return {
        "meta": _meta_dict(result.meta),
        "data": result.data,
        "mime_type": result.mime_type,
    }


async def get_recent_images(
    backend: BackendClient, user_id: str, count: int = DEFAULT_RECENT_COUNT
) -> dict[str, Any]:
    """Fetch bytes + metadata for the N most recent images, newest first."""
    clamped, was_clamped = _clamp(count, 1, MAX_RECENT_COUNT)
    metas = await backend.list_user_images(user_id, clamped)
    images: list[dict[str, Any]] = []
    missing: list[str] = []
    for m in metas:
        result = await backend.get_image(user_id, m.id)
        if result is None:
            missing.append(m.id)
            continue
        images.append({
            "meta": _meta_dict(result.meta),
            "data": result.data,
            "mime_type": result.mime_type,
        })
    return {"images": images, "clamped": was_clamped, "missing": missing}
```

- [ ] **Step 4: Run tests to verify they pass.**

Run: `cd backend && PYTHONPATH=../mcp-server/src pytest tests/test_mcp_tools.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit.**

```bash
git add mcp-server/src/mcp_server/tools.py backend/tests/test_mcp_tools.py
git commit -m "feat(mcp-server): transport-agnostic tool handlers with unit tests"
```

---

## Task 7: FastMCP server + TokenVerifier + mount in backend

**Files:**
- Create: `mcp-server/src/mcp_server/server.py`
- Create: `mcp-server/src/mcp_server/http_app.py`
- Modify: `backend/app/main.py`

Wire up `FastMCP` with three tools. Auth uses FastMCP's `TokenVerifier` protocol: each incoming request's bearer token is verified against `mcp_authorizations`; a successful verification returns an `AccessToken` whose `client_id` carries our `user_id`. Tools read `user_id` from the injected `Context`.

- [ ] **Step 1: Implement `mcp-server/src/mcp_server/server.py`:**

```python
"""FastMCP server wiring: tools + token verification."""
from __future__ import annotations

import base64
from typing import Any, Callable

from mcp.server.fastmcp import Context, FastMCP, Image
from mcp.server.auth.provider import AccessToken, TokenVerifier

from .backend import BackendClient
from . import tools as tool_fns


class McpTokenVerifier(TokenVerifier):
    """Validates an ImageTools personal access token against the DB.

    The callable must be async: `async def verify(token) -> str | None` where
    the return value is the user_id (or None for invalid tokens). This keeps
    the verifier decoupled from SQLAlchemy so the stdio transport can use a
    REST-based verifier if needed.
    """

    def __init__(self, verify: Callable):
        self._verify = verify

    async def verify_token(self, token: str) -> AccessToken | None:
        user_id = await self._verify(token)
        if user_id is None:
            return None
        return AccessToken(
            token=token,
            client_id=user_id,   # we repurpose client_id as user_id
            scopes=["mcp:images:read"],
            expires_at=None,
        )


def build_server(backend: BackendClient, verify_token, *, name: str = "imagetools") -> FastMCP:
    """Build a FastMCP instance wired up with our tools and (optional) auth.

    `verify_token`: async (str) -> str | None returning user_id. Pass None to
    disable auth (stdio local use only).
    """
    if verify_token is not None:
        from mcp.server.auth.settings import AuthSettings
        from pydantic import AnyHttpUrl
        mcp = FastMCP(
            name,
            json_response=True,
            token_verifier=McpTokenVerifier(verify_token),
            auth=AuthSettings(
                issuer_url=AnyHttpUrl("https://imagetools.local/"),
                resource_server_url=AnyHttpUrl("https://imagetools.local/"),
                required_scopes=["mcp:images:read"],
            ),
        )
    else:
        mcp = FastMCP(name, json_response=True)

    def _user_id(ctx: Context) -> str:
        # FastMCP populates client_id from the verified AccessToken.
        if ctx.client_id:
            return ctx.client_id
        # stdio (no auth) uses env var resolution wired at CLI layer
        raise RuntimeError("no user_id in context; auth misconfigured")

    @mcp.tool()
    async def list_recent_images(count: int = 10, ctx: Context = None) -> dict[str, Any]:
        """List metadata for the N most recent images for the authenticated user,
        newest first. Does not return image bytes — use get_image or
        get_recent_images to fetch content."""
        return await tool_fns.list_recent_images(backend, _user_id(ctx), count)

    @mcp.tool()
    async def get_image(id: str, ctx: Context = None) -> list:
        """Fetch one image by id as an MCP image content block, along with
        its metadata."""
        result = await tool_fns.get_image(backend, _user_id(ctx), id)
        return _to_mcp_content(result["data"], result["mime_type"], result["meta"])

    @mcp.tool()
    async def get_recent_images(count: int = 1, ctx: Context = None) -> list:
        """Fetch the N most recent images (up to 6) as MCP image content blocks,
        newest first, with metadata for each. For larger batches use
        list_recent_images + get_image."""
        result = await tool_fns.get_recent_images(backend, _user_id(ctx), count)
        out: list = []
        for img in result["images"]:
            out.extend(_to_mcp_content(img["data"], img["mime_type"], img["meta"]))
        return out

    return mcp


def _to_mcp_content(data: bytes, mime_type: str, meta: dict) -> list:
    """Package raw image bytes + metadata into MCP content blocks."""
    # Image() handles base64 encoding; we pass through format as lowercase.
    fmt = mime_type.split("/", 1)[1]
    img = Image(data=data, format=fmt)
    # Return both the image block and a text block describing the metadata so
    # the LLM can correlate "first image" with its filename/timestamp/size.
    return [
        img,
        (
            f"Image id={meta['id']} filename={meta['original_filename']} "
            f"created_at={meta['created_at']} size={meta['current_size']} "
            f"{meta['width']}x{meta['height']} format={meta['format']}"
        ),
    ]
```

> NOTE: `Image.data=bytes` is accepted by FastMCP (per the SDK docs). If at runtime the SDK rejects raw bytes for any format, switch to base64-encoding the bytes and constructing an `ImageContent` directly:
> ```python
> from mcp.types import ImageContent
> ImageContent(type="image", data=base64.b64encode(data).decode(), mimeType=mime_type)
> ```

- [ ] **Step 2: Implement `mcp-server/src/mcp_server/http_app.py` — the HTTP transport bootstrapper:**

```python
"""Helpers for mounting the MCP Streamable HTTP app inside the FastAPI backend."""
from __future__ import annotations

import contextlib
from typing import Callable

from mcp.server.fastmcp import FastMCP


@contextlib.asynccontextmanager
async def mcp_lifespan(mcp: FastMCP):
    """ASGI lifespan helper to run the MCP session manager."""
    async with mcp.session_manager.run():
        yield


def build_backend_mcp(session_factory, verify_token) -> FastMCP:
    """Build a FastMCP server wired to in-process DB access."""
    from .backend_local import LocalBackendClient
    from .server import build_server
    backend = LocalBackendClient(session_factory=session_factory)
    return build_server(backend, verify_token)
```

- [ ] **Step 3: Mount MCP in `backend/app/main.py`.**

Find the `lifespan` async context manager (~line 51) and extend it so the MCP session manager runs alongside existing startup/shutdown. Pattern:

```python
# Near the top-level imports
from contextlib import AsyncExitStack
from app.core.database import AsyncSessionLocal, get_db
from app.services.mcp_token_service import McpTokenService
from mcp_server.http_app import build_backend_mcp

# Inside lifespan(), replace the single-yield with a stack that also enters
# the MCP session manager:
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ...existing startup (migrate_database, scheduler, etc.)...

    async def _verify_token(token: str):
        async with AsyncSessionLocal() as db:
            return await McpTokenService.validate(db, token)

    mcp = build_backend_mcp(
        session_factory=AsyncSessionLocal,
        verify_token=_verify_token,
    )
    app.state.mcp = mcp

    async with AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        app.mount("/mcp", mcp.streamable_http_app())
        yield
    # ...existing shutdown...
```

> NOTE: You must read the existing `lifespan()` in `backend/app/main.py` before editing. Preserve the existing startup calls (migrate, scheduler, any existing `yield`). The key additions are the `build_backend_mcp(...)`, the `AsyncExitStack`, the `enter_async_context`, and the `app.mount("/mcp", mcp.streamable_http_app())` — all of which happen BEFORE `yield` so the mount is active during serving.

- [ ] **Step 4: Add `PYTHONPATH` for the mcp-server package** in the backend. Two options:
  - Option A (chosen): install the package in editable mode in the Dockerfile. Add to `backend/Dockerfile` before `CMD`:
    ```dockerfile
    COPY ../mcp-server /mcp-server
    RUN pip install -e /mcp-server
    ```
    ...actually Docker COPY cannot go up directories. Use the repo-root Dockerfile instead — there is one at `/home/philg/src/python/ImageTools/Dockerfile` that builds the whole image. Verify: `ls /home/philg/src/python/ImageTools/Dockerfile`. Add the copy + pip install there.
  - Option B: for local dev, `pip install -e ./mcp-server` in the backend venv. Document in the README (Task 11).

  Start with Option A: modify the top-level `Dockerfile` to copy and install `mcp-server` as an editable install after installing backend requirements.

  Read the top-level Dockerfile before editing. Append, after backend `pip install`:
  ```dockerfile
  COPY mcp-server /app/mcp-server
  RUN pip install -e /app/mcp-server
  ```

- [ ] **Step 5: Smoke-test the HTTP endpoint** with the backend running:

```bash
# Create a token (reuse from Task 3)
TOKEN=$(curl -s -X POST http://localhost:8082/api/v1/users/$USER_ID/mcp-tokens \
  -H 'Content-Type: application/json' -d '{"label":"smoke"}' | jq -r .token)

# Hit the MCP endpoint (initialize request from the MCP spec)
curl -s -X POST http://localhost:8082/mcp/ \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
# Expected: JSON listing the three tools.

# Invalid token
curl -s -X POST http://localhost:8082/mcp/ \
  -H 'Authorization: Bearer imt_bogus' \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
# Expected: 401 or an MCP unauthorized error.
```

- [ ] **Step 6: Commit.**

```bash
git add mcp-server/src/mcp_server/server.py mcp-server/src/mcp_server/http_app.py backend/app/main.py Dockerfile
git commit -m "feat(mcp-server): FastMCP tools + token verifier + /mcp mount"
```

---

## Task 8: stdio transport entry point

**Files:**
- Create: `mcp-server/src/mcp_server/stdio.py`

Reads `IMAGETOOLS_URL` and `IMAGETOOLS_TOKEN`, validates the token against the backend once at startup (resolves `user_id`), then runs FastMCP over stdio. Auth is disabled in the FastMCP instance itself (there is no incoming HTTP auth); the resolved `user_id` is baked in via a closure.

- [ ] **Step 1: Implement `mcp-server/src/mcp_server/stdio.py`:**

```python
"""stdio transport entry point.

Usage:
  IMAGETOOLS_URL=http://localhost:8082 IMAGETOOLS_TOKEN=imt_... \\
    python -m mcp_server.stdio
"""
from __future__ import annotations

import asyncio
import os
import sys

import httpx

from .backend_http import HttpBackendClient
from .server import build_server
from . import tools as tool_fns
from mcp.server.fastmcp import Context, FastMCP


async def _resolve_user_id(base_url: str, token: str) -> str:
    """Identify the user by calling a lightweight backend endpoint with the
    bearer token. We reuse `GET /api/v1/me` if present, else fall back to a
    dedicated /mcp-tokens/whoami endpoint added in Task 3b."""
    # Simpler: rely on the MCP /mcp/ endpoint to validate.
    # For stdio we use the REST endpoints directly, so we validate via a call
    # to a helper endpoint that returns the user_id for a token.
    async with httpx.AsyncClient(
        timeout=10.0, headers={"Authorization": f"Bearer {token}"}
    ) as client:
        r = await client.get(f"{base_url.rstrip('/')}/api/v1/mcp-tokens/whoami")
        r.raise_for_status()
        return r.json()["user_id"]


def _build_stdio_server(user_id: str, backend: HttpBackendClient) -> FastMCP:
    """FastMCP with auth disabled and user_id hardcoded from env-resolved token."""
    mcp = FastMCP("imagetools-stdio", json_response=True)

    @mcp.tool()
    async def list_recent_images(count: int = 10) -> dict:
        """List metadata for the N most recent images (newest first)."""
        return await tool_fns.list_recent_images(backend, user_id, count)

    @mcp.tool()
    async def get_image(id: str) -> list:
        """Fetch one image as an MCP image content block + metadata."""
        from .server import _to_mcp_content
        result = await tool_fns.get_image(backend, user_id, id)
        return _to_mcp_content(result["data"], result["mime_type"], result["meta"])

    @mcp.tool()
    async def get_recent_images(count: int = 1) -> list:
        """Fetch the N most recent images (up to 6) as MCP content blocks."""
        from .server import _to_mcp_content
        result = await tool_fns.get_recent_images(backend, user_id, count)
        out: list = []
        for img in result["images"]:
            out.extend(_to_mcp_content(img["data"], img["mime_type"], img["meta"]))
        return out

    return mcp


def main() -> None:
    base_url = os.environ.get("IMAGETOOLS_URL")
    token = os.environ.get("IMAGETOOLS_TOKEN")
    if not base_url or not token:
        sys.stderr.write(
            "IMAGETOOLS_URL and IMAGETOOLS_TOKEN must be set.\n"
        )
        sys.exit(2)

    async def _run():
        user_id = await _resolve_user_id(base_url, token)
        backend = HttpBackendClient(base_url=base_url, token=token)
        mcp = _build_stdio_server(user_id, backend)
        try:
            # FastMCP.run is sync and will start its own event loop, so we
            # call run_stdio_async() from within our loop instead.
            await mcp.run_stdio_async()
        finally:
            await backend.aclose()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Add a `/api/v1/mcp-tokens/whoami` endpoint** so the stdio transport can identify the user for a token.

Edit `backend/app/api/v1/endpoints/mcp_tokens.py` and add a separate router (because the main router is prefixed with `/users/{user_id}/...`):

```python
# At module top:
whoami_router = APIRouter(prefix="/mcp-tokens", tags=["mcp-tokens"])


@whoami_router.get("/whoami")
async def whoami(
    authorization: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    from fastapi import Header
    # fastapi injects headers via Header(); re-declared inline below
    pass
```

Actually use FastAPI's `Header` dependency properly — replace the above with:

```python
from fastapi import Header

whoami_router = APIRouter(prefix="/mcp-tokens", tags=["mcp-tokens"])


@whoami_router.get("/whoami")
async def whoami(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="bearer token required")
    token = authorization.split(" ", 1)[1]
    user_id = await McpTokenService.validate(db, token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="invalid or revoked token")
    return {"user_id": user_id}
```

And register the whoami router in `backend/app/main.py` alongside the other one:

```python
app.include_router(mcp_tokens.whoami_router, prefix=settings.API_PREFIX, tags=["mcp-tokens"])
```

- [ ] **Step 3: Smoke-test stdio** with the backend running:

```bash
# Install the package locally
pip install -e ./mcp-server

# Create a token (as in Task 3)
export IMAGETOOLS_URL=http://localhost:8082
export IMAGETOOLS_TOKEN=imt_...

# Send an MCP init + tools/list over stdio and observe the response
printf '%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"smoke","version":"1"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | python -m mcp_server.stdio
# Expected: two JSON-RPC responses; the second lists the three tools.
```

- [ ] **Step 4: Commit.**

```bash
git add mcp-server/src/mcp_server/stdio.py backend/app/api/v1/endpoints/mcp_tokens.py backend/app/main.py
git commit -m "feat(mcp-server): stdio transport entry point and /whoami endpoint"
```

---

## Task 9: Frontend MCP Token Manager component

**Files:**
- Create: `frontend/src/components/McpTokenManager.vue`

A modal/panel that lists existing tokens (label + created_at + last_used_at), a "New Token" button that prompts for a label, shows the plaintext token exactly once with a copy-to-clipboard button, and a per-row "Revoke" button with inline confirm.

- [ ] **Step 1: Create `frontend/src/components/McpTokenManager.vue`:**

```vue
<template>
  <div class="mcp-token-manager">
    <div class="header">
      <h3>MCP Access Tokens</h3>
      <button @click="startCreate" :disabled="creating" class="btn btn-primary">
        + New Token
      </button>
    </div>

    <p class="help-text">
      Tokens let Claude Code (and other MCP clients) read your recent
      screenshots from ImageTools. Tokens are shown once at creation — copy
      immediately. Revoke any token you no longer need.
    </p>

    <!-- Create form -->
    <div v-if="creating" class="create-form">
      <input
        v-model="newLabel"
        type="text"
        placeholder="Label (e.g. laptop claude-code)"
        @keyup.enter="submitCreate"
        ref="labelInput"
      />
      <button @click="submitCreate" :disabled="!newLabel.trim()" class="btn btn-primary">
        Create
      </button>
      <button @click="creating = false" class="btn">Cancel</button>
    </div>

    <!-- Plaintext reveal (shown once) -->
    <div v-if="plaintextToken" class="plaintext-reveal">
      <p><strong>Copy this token now — it will not be shown again.</strong></p>
      <div class="token-row">
        <code>{{ plaintextToken }}</code>
        <button @click="copyToken" class="btn btn-sm">
          {{ copied ? 'Copied' : 'Copy' }}
        </button>
      </div>
      <button @click="plaintextToken = ''" class="btn btn-sm">Done</button>
    </div>

    <!-- Token list -->
    <table v-if="tokens.length" class="token-table">
      <thead>
        <tr>
          <th>Label</th>
          <th>Created</th>
          <th>Last used</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="t in tokens" :key="t.id">
          <td>{{ t.label }}</td>
          <td>{{ formatDate(t.created_at) }}</td>
          <td>{{ t.last_used_at ? formatDate(t.last_used_at) : '—' }}</td>
          <td>
            <button
              v-if="confirmingId !== t.id"
              @click="confirmingId = t.id"
              class="btn btn-sm btn-danger"
            >Revoke</button>
            <template v-else>
              <button @click="revoke(t.id)" class="btn btn-sm btn-danger">Confirm</button>
              <button @click="confirmingId = ''" class="btn btn-sm">Cancel</button>
            </template>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else-if="!loading" class="empty">No tokens yet.</p>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue';
import { useUserStore } from '../stores/userStore';
import { storeToRefs } from 'pinia';
import axios from 'axios';

const userStore = useUserStore();
const { userId } = storeToRefs(userStore);

const tokens = ref([]);
const loading = ref(false);
const creating = ref(false);
const newLabel = ref('');
const plaintextToken = ref('');
const copied = ref(false);
const confirmingId = ref('');
const labelInput = ref(null);

const base = (path) => `/api/v1/users/${userId.value}/mcp-tokens${path}`;

const load = async () => {
  loading.value = true;
  try {
    const r = await axios.get(base(''));
    tokens.value = r.data;
  } finally {
    loading.value = false;
  }
};

const startCreate = async () => {
  creating.value = true;
  newLabel.value = '';
  await nextTick();
  labelInput.value?.focus();
};

const submitCreate = async () => {
  if (!newLabel.value.trim()) return;
  const r = await axios.post(base(''), { label: newLabel.value.trim() });
  plaintextToken.value = r.data.token;
  creating.value = false;
  newLabel.value = '';
  copied.value = false;
  await load();
};

const copyToken = async () => {
  await navigator.clipboard.writeText(plaintextToken.value);
  copied.value = true;
};

const revoke = async (id) => {
  await axios.delete(base(`/${id}`));
  confirmingId.value = '';
  await load();
};

const formatDate = (iso) => new Date(iso).toLocaleString();

onMounted(load);
</script>

<style scoped>
.mcp-token-manager { padding: 1rem; }
.header { display: flex; justify-content: space-between; align-items: center; }
.help-text { color: #666; font-size: 0.9rem; margin: 0.5rem 0 1rem; }
.create-form { display: flex; gap: 0.5rem; margin: 1rem 0; }
.create-form input { flex: 1; padding: 0.4rem 0.6rem; }
.plaintext-reveal {
  background: #fffbea; border: 1px solid #e6c200; padding: 0.75rem;
  margin: 1rem 0; border-radius: 6px;
}
.token-row { display: flex; gap: 0.5rem; align-items: center; margin: 0.5rem 0; }
.token-row code {
  flex: 1; word-break: break-all; background: #fff; padding: 0.4rem;
  border: 1px solid #ddd; border-radius: 4px;
}
.token-table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
.token-table th, .token-table td {
  padding: 0.5rem; text-align: left; border-bottom: 1px solid #eee;
}
.btn {
  padding: 0.4rem 0.75rem; border: 1px solid #ccc; background: white;
  border-radius: 4px; cursor: pointer;
}
.btn-primary { background: #4CAF50; color: white; border-color: #4CAF50; }
.btn-danger { background: #d9534f; color: white; border-color: #d9534f; }
.btn-sm { padding: 0.25rem 0.5rem; font-size: 0.85rem; }
.empty { color: #999; font-style: italic; }
</style>
```

- [ ] **Step 2: Commit.**

```bash
git add frontend/src/components/McpTokenManager.vue
git commit -m "feat(frontend): MCP token manager component"
```

---

## Task 10: Wire MCP Token Manager into the frontend

**Files:**
- Modify: `frontend/src/App.vue`

Expose the manager behind a modal opened from the existing settings menu (next to the addon management area).

- [ ] **Step 1: Import the component in `App.vue`.** Add to the imports block (~line 1414):

```javascript
import McpTokenManager from './components/McpTokenManager.vue';
```

- [ ] **Step 2: Add a state flag** (~line 1438 where other `show*Modal` refs live):

```javascript
const showMcpTokenModal = ref(false);
```

- [ ] **Step 3: Add a menu item.** Find the settings menu dropdown in the template that already contains addon / AI / preset management items. Add alongside them:

```vue
<button @click="showMcpTokenModal = true; showSettingsMenu = false" class="menu-item">
  <span class="icon">🔑</span>
  MCP Access Tokens
</button>
```

- [ ] **Step 4: Add the modal** near the other modals (e.g. near the clear-all confirm modal ~line 210):

```vue
<div v-if="showMcpTokenModal" class="modal-overlay" @click="showMcpTokenModal = false">
  <div class="modal-content modal-wide" @click.stop>
    <div class="modal-header">
      <h2>MCP Access Tokens</h2>
      <button @click="showMcpTokenModal = false" class="btn-close">×</button>
    </div>
    <McpTokenManager />
  </div>
</div>
```

- [ ] **Step 5: Smoke-test via the UI.** Start frontend + backend:

```bash
cd frontend && npm run dev    # in one shell
cd backend && uvicorn app.main:app --reload --port 8082    # in another
```

Open the web app. Open the settings menu. Click "MCP Access Tokens". Create a token with label "smoke-test". Verify the plaintext is shown once, is copyable, and appears in the list with `last_used_at = —`. Call the MCP endpoint as in Task 7 Step 5; reload the UI; `last_used_at` should now have a value. Revoke; verify it disappears from the list and subsequent MCP calls with the same token return 401.

- [ ] **Step 6: Commit.**

```bash
git add frontend/src/App.vue
git commit -m "feat(frontend): MCP token manager modal in settings menu"
```

---

## Task 11: `mcp-server/README.md` — setup docs for both transports

**Files:**
- Modify: `mcp-server/README.md`

- [ ] **Step 1: Replace the stub with real docs:**

````markdown
# ImageTools MCP Server

Exposes your recent ImageTools screenshots to Claude Code (and other MCP clients)
so you can ask the LLM to reason about them: *"use my last 2 screenshots; the
first shows the bug, the second shows the expected layout"*.

Two transports; pick whichever fits your setup.

## Streamable HTTP (for a deployed backend)

The MCP endpoint is served by the existing ImageTools backend at `/mcp/` —
nothing extra to install, no extra port to open.

1. In the ImageTools web UI, open Settings → **MCP Access Tokens** → New Token.
   Give it a label like `laptop claude-code`. Copy the `imt_…` token — it
   is shown only once.
2. Add this entry to your Claude Code MCP config
   (`~/.claude/mcp.json` or project `.mcp.json`):

```json
{
  "mcpServers": {
    "imagetools": {
      "url": "https://imagetools.example.com/mcp/",
      "headers": { "Authorization": "Bearer imt_YOUR_TOKEN_HERE" }
    }
  }
}
```

3. Restart Claude Code. Verify by asking it: *"list my 3 most recent
   ImageTools screenshots"*.

## stdio (for local dev / tunnelling)

The stdio transport runs a small Python process on your machine that calls the
ImageTools REST API.

1. Install the package (requires Python 3.11+):

```bash
pip install -e /path/to/ImageTools/mcp-server
```

2. Mint a token as above. Then configure Claude Code:

```json
{
  "mcpServers": {
    "imagetools": {
      "command": "python",
      "args": ["-m", "mcp_server.stdio"],
      "env": {
        "IMAGETOOLS_URL": "http://localhost:8082",
        "IMAGETOOLS_TOKEN": "imt_YOUR_TOKEN_HERE"
      }
    }
  }
}
```

## Tools exposed

| Tool | Args | Returns |
|---|---|---|
| `list_recent_images` | `count: int = 10` (max 50) | Metadata list, newest first |
| `get_image` | `id: str` | Image bytes + metadata |
| `get_recent_images` | `count: int = 1` (max 6) | Up to N images + metadata, newest first |

## Revoking access

From the web UI's MCP Access Tokens screen, click **Revoke** on any row.
Revocation is immediate; subsequent MCP calls with that token will fail with
401.
````

- [ ] **Step 2: Commit.**

```bash
git add mcp-server/README.md
git commit -m "docs(mcp-server): setup instructions for both transports"
```

---

## Self-Review

**Spec coverage**

| Spec requirement | Task(s) |
|---|---|
| `McpAuthorization` table (hash, label, revoked_at, last_used_at) | Task 1 |
| Token minting in web UI, shown once, persistent list, revoke | Tasks 3, 9, 10 |
| Streamable HTTP transport mounted at `/mcp/` | Tasks 4–7 |
| stdio transport | Task 8 |
| Three tools: `list_recent_images`, `get_image`, `get_recent_images` | Task 6 |
| Count clamping per spec (50 / 6) | Task 6 |
| `created_at DESC` ordering | Tasks 5 (verified), 6 |
| Auth via bearer token shared by both transports | Tasks 2, 7, 8 |
| Missing-file handling returns partial with warning | Task 6 (`missing` in response) |
| Tagging deferred | Noted in Task 11 README; no code |

**No placeholders:** All code blocks are complete and self-contained.

**Type consistency:** Tool function names match across `tools.py`, `server.py`, and `stdio.py` (`list_recent_images`, `get_image`, `get_recent_images`). `ImageMeta` / `ImageBytes` dataclasses defined in `backend.py` and used unchanged by both backend implementations and `tools.py`. `McpTokenService` method names (`create`, `validate`, `revoke`, `list_for_user`) match between the service, the endpoints, and the token verifier closure.
