# Image Tagging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Attach a freetext tag to screenshots at upload time so the ImageTools MCP server can retrieve images by tag. The browser addon and Android app expose a "current tag" with autocomplete from the user's existing tags; tags travel with each upload to the backend; MCP tools gain a `tag` filter.

**Architecture:** New `tags` JSON-array column on `images`, populated by an explicit migration. Three upload endpoints (frontend, addon, mobile) accept an optional `tag` form field. New `GET /users/{user_id}/tags` powers autocomplete. MCP `list_recent_images` and `get_recent_images` gain a `tag: str | None` arg, applied through a `BackendClient` filter that uses SQLite `json_each` locally and a query parameter remotely. Tags are stored case-preserving but matched case-insensitively.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite (`json_each`), MCP Python SDK (`FastMCP`), Vue 3, Chrome/Firefox WebExtensions, Android (Kotlin + Compose).

**Spec:** `docs/superpowers/specs/2026-04-25-image-tagging-design.md`

---

## File Structure

```
backend/
├── app/models/models.py                          # + tags column on Image
├── app/core/migrate.py                           # + tags column migration
├── app/services/image_service.py                 # + tag helpers, accept tag at upload
├── app/services/tag_service.py                   # NEW — list_user_tags aggregate
├── app/schemas/image.py                          # + tags on ImageResponse
├── app/api/v1/endpoints/images.py                # + tag form field, + PUT /tags
├── app/api/v1/endpoints/addon.py                 # + tag form field
├── app/api/v1/endpoints/mobile.py                # + tag form field
├── app/api/v1/endpoints/tags.py                  # NEW — GET /users/{uid}/tags
├── app/main.py                                   # + tags router include
└── tests/
    ├── test_tag_service.py                       # NEW
    └── test_mcp_tools.py                         # extend with tag-filter cases

mcp-server/src/mcp_server/
├── backend.py                                    # + tags on ImageMeta
├── backend_local.py                              # + tag filter via json_each
├── backend_http.py                               # + tag query param
├── tools.py                                      # + tag arg
├── server.py                                     # + tag arg on FastMCP tools
└── stdio.py                                      # + tag arg on stdio tools

browser-addons/{chrome,firefox}/
├── popup.html                                    # + current-tag input + datalist
├── popup.js                                      # + load/persist current tag
├── content.js                                    # + include tag in upload
└── background.js                                 # + include tag in upload

android-app/app/src/main/
├── java/.../ShareActivity.kt                     # + tag prompt step
├── java/.../utils/TagPreferences.kt              # NEW — current tag persistence
└── java/.../data/network/ImageToolsApi.kt        # + tag part on uploadImage

frontend/src/components/ImageCard.vue              # + render tag chips
```

---

## Task 1: Add `tags` column with explicit migration

**Files:**
- Modify: `backend/app/models/models.py`
- Modify: `backend/app/core/migrate.py`
- Modify: `backend/tests/test_models_smoke.py` (extend)

`Base.metadata.create_all` does not alter existing tables. We need an explicit migration block that adds `tags` to existing rows when missing.

- [ ] **Step 1: Add column to `Image` model** at `backend/app/models/models.py` — find the `class Image(Base):` block (line 25 area) and append, in the column block, before `created_at`:

```python
    # Free-text tags for MCP retrieval. JSON array stored as TEXT; default '[]'.
    tags = Column(Text, nullable=False, server_default="[]")
```

- [ ] **Step 2: Add migration** at `backend/app/core/migrate.py`. Read the file first; it already follows a "check column existence, ALTER TABLE if missing" pattern for prior migrations. Add a new BLOCK at the end of `migrate_database()` (just before the final commit / log):

```python
        # ------------------------------------------------------------------ #
        # BLOCK: add images.tags column for tag-based MCP retrieval          #
        # ------------------------------------------------------------------ #
        result = await conn.execute(text("PRAGMA table_info(images)"))
        cols = [row[1] for row in result.fetchall()]
        if "tags" not in cols:
            logger.info("Adding tags column to images table...")
            await conn.execute(
                text("ALTER TABLE images ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'")
            )
            migrations_applied.append("images.tags")
```

(Adapt to the exact migrate-block style — read existing blocks for consistency, e.g. how `migrations_applied` is appended.)

- [ ] **Step 3: Extend the model smoke test** at `backend/tests/test_models_smoke.py` — append a second test:

```python
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
```

- [ ] **Step 4: Run tests.**

Run: `cd backend && pytest tests/test_models_smoke.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit.**

```bash
git add backend/app/models/models.py backend/app/core/migrate.py backend/tests/test_models_smoke.py
git commit -m "feat(backend): add tags column to images with migration"
```

---

## Task 2: `ImageService` tag helpers + tag normalisation

**Files:**
- Modify: `backend/app/services/image_service.py`
- Create: `backend/tests/test_image_service_tags.py`

Add helpers `get_tags(image)`, `set_tags(image, tags)`, and normalisation
`normalize_tag(tag) -> str | None`. Update `save_uploaded_image(...)` to
accept an optional `tag` parameter and store as `[tag]` after normalisation.

- [ ] **Step 1: Write the tests** at `backend/tests/test_image_service_tags.py`:

```python
import pytest
from app.services.image_service import ImageService, normalize_tag


def test_normalize_tag_trims_and_returns_value():
    assert normalize_tag("  POS-table-service  ") == "POS-table-service"


def test_normalize_tag_returns_none_for_empty_or_whitespace():
    assert normalize_tag("") is None
    assert normalize_tag("   ") is None
    assert normalize_tag(None) is None


def test_normalize_tag_truncates_to_64_chars():
    long_tag = "a" * 100
    assert len(normalize_tag(long_tag)) == 64


@pytest.mark.asyncio
async def test_get_tags_returns_empty_for_new_image(db_session, seeded_user):
    from app.models.models import Image
    img = Image(
        id="i1", user_id=seeded_user, original_filename="x.png",
        original_size=1, current_path="/tmp/x.png", current_size=1,
        width=1, height=1, format="PNG",
    )
    db_session.add(img)
    await db_session.commit()
    assert ImageService.get_tags(img) == []


@pytest.mark.asyncio
async def test_set_tags_dedupes_and_preserves_case(db_session, seeded_user):
    from app.models.models import Image
    img = Image(
        id="i1", user_id=seeded_user, original_filename="x.png",
        original_size=1, current_path="/tmp/x.png", current_size=1,
        width=1, height=1, format="PNG",
    )
    db_session.add(img)
    await db_session.commit()
    ImageService.set_tags(img, ["POS", "pos", "  POS  "])
    await db_session.commit()
    await db_session.refresh(img)
    # Case preserved on the first occurrence; case-insensitive dedupe.
    assert ImageService.get_tags(img) == ["POS"]
```

- [ ] **Step 2: Run, expect failures.**

Run: `cd backend && pytest tests/test_image_service_tags.py -v`
Expected: ImportError on `normalize_tag`.

- [ ] **Step 3: Implement helpers** in `backend/app/services/image_service.py`. Add at module top after imports:

```python
import json

MAX_TAG_LENGTH = 64


def normalize_tag(tag):
    """Return a trimmed tag string, or None if empty after trim. Truncates to
    MAX_TAG_LENGTH characters."""
    if tag is None:
        return None
    trimmed = tag.strip()
    if not trimmed:
        return None
    return trimmed[:MAX_TAG_LENGTH]
```

Add to the `ImageService` class:

```python
    @staticmethod
    def get_tags(image) -> list[str]:
        if not image.tags:
            return []
        try:
            return list(json.loads(image.tags))
        except (json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def set_tags(image, tags) -> None:
        """Set tags on an image. Normalises each tag, dedupes
        case-insensitively (first occurrence wins for casing)."""
        seen_lower = set()
        unique = []
        for raw in tags:
            normalized = normalize_tag(raw)
            if normalized is None:
                continue
            key = normalized.lower()
            if key in seen_lower:
                continue
            seen_lower.add(key)
            unique.append(normalized)
        image.tags = json.dumps(unique)
```

- [ ] **Step 4: Update `save_uploaded_image`** to accept an optional `tag` parameter. Find the function signature and add `tag: str | None = None` as a keyword-only argument. After the image is created, call `ImageService.set_tags(image, [tag])` only if `normalize_tag(tag)` returns a non-None value.

- [ ] **Step 5: Run tests.**

Run: `cd backend && pytest tests/test_image_service_tags.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit.**

```bash
git add backend/app/services/image_service.py backend/tests/test_image_service_tags.py
git commit -m "feat(backend): tag helpers on ImageService with case-insensitive dedupe"
```

---

## Task 3: Upload endpoints accept `tag`, response carries `tags`

**Files:**
- Modify: `backend/app/schemas/image.py`
- Modify: `backend/app/api/v1/endpoints/images.py`
- Modify: `backend/app/api/v1/endpoints/addon.py`
- Modify: `backend/app/api/v1/endpoints/mobile.py`

- [ ] **Step 1: Add `tags` to `ImageResponse`** in `backend/app/schemas/image.py`:

```python
    tags: list[str] = []
```

- [ ] **Step 2: Update each upload endpoint to accept an optional `tag` form field.** For each of `images.py` (`POST /images`), `addon.py` (`POST /upload`), `mobile.py` (`POST /upload`):

Add a `tag: Optional[str] = Form(None)` parameter to the function signature
(matching the existing form-field style). Pass it to
`ImageService.save_uploaded_image(..., tag=tag)`. Ensure `Form` is imported
in each file (it usually already is for `file: UploadFile = File(...)`).

- [ ] **Step 3: Update every place that constructs an `ImageResponse`** (probably 4–6 sites in `images.py` plus the addon/mobile responses) to include `tags=ImageService.get_tags(image)`. Search with `grep -n 'ImageResponse(' backend/app/api/v1/endpoints/`.

- [ ] **Step 4: Smoke-import test.**

Run: `cd backend && python -c "from app.main import app; print('ok')"`
Expected: `ok`.

- [ ] **Step 5: Commit.**

```bash
git add backend/app/schemas/image.py backend/app/api/v1/endpoints/images.py backend/app/api/v1/endpoints/addon.py backend/app/api/v1/endpoints/mobile.py
git commit -m "feat(backend): upload endpoints accept tag, ImageResponse carries tags"
```

---

## Task 4: `GET /users/{user_id}/tags` endpoint

**Files:**
- Create: `backend/app/services/tag_service.py`
- Create: `backend/app/api/v1/endpoints/tags.py`
- Modify: `backend/app/main.py` (register router)
- Create: `backend/tests/test_tag_service.py`

- [ ] **Step 1: Write the test** at `backend/tests/test_tag_service.py`:

```python
import json
import pytest
from datetime import datetime, timedelta, timezone
from app.models.models import Image
from app.services.tag_service import TagService


@pytest.mark.asyncio
async def test_list_user_tags_orders_by_recent_use(db_session, seeded_user):
    now = datetime.now(timezone.utc)
    # Older "alpha"
    db_session.add(Image(
        id="i1", user_id=seeded_user, original_filename="a.png",
        original_size=1, current_path="/tmp/a", current_size=1,
        width=1, height=1, format="PNG",
        tags=json.dumps(["alpha"]),
        created_at=now - timedelta(days=2),
    ))
    # Newer "beta"
    db_session.add(Image(
        id="i2", user_id=seeded_user, original_filename="b.png",
        original_size=1, current_path="/tmp/b", current_size=1,
        width=1, height=1, format="PNG",
        tags=json.dumps(["beta"]),
        created_at=now - timedelta(days=1),
    ))
    # Newest, two tags
    db_session.add(Image(
        id="i3", user_id=seeded_user, original_filename="c.png",
        original_size=1, current_path="/tmp/c", current_size=1,
        width=1, height=1, format="PNG",
        tags=json.dumps(["beta", "gamma"]),
        created_at=now,
    ))
    await db_session.commit()

    tags = await TagService.list_user_tags(db_session, seeded_user)
    names = [t["tag"] for t in tags]
    # beta and gamma both share newest; alpha comes last.
    assert "beta" in names and "gamma" in names and "alpha" in names
    assert names[-1] == "alpha"
```

- [ ] **Step 2: Run, expect failure.**

Run: `cd backend && pytest tests/test_tag_service.py -v`
Expected: ImportError on `app.services.tag_service`.

- [ ] **Step 3: Implement `TagService`** at `backend/app/services/tag_service.py`:

```python
"""Aggregate user tag lookups for autocomplete."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TagService:
    @staticmethod
    async def list_user_tags(db: AsyncSession, user_id: str) -> list[dict]:
        """Return distinct tags the user has used, ordered by most recent use.

        Uses SQLite's json_each to flatten the JSON array column.
        """
        result = await db.execute(
            text(
                """
                SELECT je.value AS tag, MAX(i.created_at) AS last_used_at
                FROM images AS i, json_each(i.tags) AS je
                WHERE i.user_id = :user_id
                GROUP BY je.value
                ORDER BY MAX(i.created_at) DESC
                """
            ),
            {"user_id": user_id},
        )
        rows = result.fetchall()
        return [{"tag": r[0], "last_used_at": r[1]} for r in rows]
```

- [ ] **Step 4: Implement endpoint** at `backend/app/api/v1/endpoints/tags.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.tag_service import TagService

router = APIRouter(prefix="/users/{user_id}/tags", tags=["tags"])


@router.get("")
async def list_user_tags(user_id: str, db: AsyncSession = Depends(get_db)):
    """List distinct tags this user has used, ordered by most recent use."""
    return await TagService.list_user_tags(db, user_id)
```

- [ ] **Step 5: Register router in `backend/app/main.py`** alongside the others. Add the import at the top:

```python
from app.api.v1.endpoints import tags
```

And the include after the mcp_tokens lines:

```python
app.include_router(tags.router, prefix=settings.API_PREFIX, tags=["tags"])
```

- [ ] **Step 6: Run test.**

Run: `cd backend && pytest tests/test_tag_service.py -v`
Expected: 1 passed.

- [ ] **Step 7: Commit.**

```bash
git add backend/app/services/tag_service.py backend/app/api/v1/endpoints/tags.py backend/app/main.py backend/tests/test_tag_service.py
git commit -m "feat(backend): GET /users/{uid}/tags for autocomplete"
```

---

## Task 5: `PUT /images/{id}/tags` endpoint

**Files:**
- Modify: `backend/app/api/v1/endpoints/images.py`

This endpoint isn't strictly required for v1 (no UI consumer yet) but is in the spec and unblocks future tag-edit UI without another backend touch.

- [ ] **Step 1: Add Pydantic schema for the body.** In `backend/app/schemas/image.py`:

```python
class ImageTagsUpdate(BaseModel):
    tags: list[str]
```

- [ ] **Step 2: Add the endpoint** in `backend/app/api/v1/endpoints/images.py`:

```python
@router.put("/{image_id}/tags", response_model=ImageResponse)
async def update_image_tags(
    image_id: str,
    payload: ImageTagsUpdate,
    db: AsyncSession = Depends(get_db),
):
    image = await ImageService.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    ImageService.set_tags(image, payload.tags)
    await db.commit()
    await db.refresh(image)
    return ImageResponse(
        id=image.id, user_id=image.user_id,
        original_filename=image.original_filename,
        original_size=image.original_size,
        current_size=image.current_size,
        width=image.width, height=image.height, format=image.format,
        thumbnail_url=f"{settings.API_PREFIX}/images/{image.id}/thumbnail",
        image_url=f"{settings.API_PREFIX}/images/{image.id}/current",
        created_at=image.created_at, updated_at=image.updated_at,
        tags=ImageService.get_tags(image),
    )
```

Add `from app.schemas.image import ImageTagsUpdate` if not already imported.

- [ ] **Step 3: Smoke import.**

Run: `cd backend && python -c "from app.main import app; print('ok')"`

- [ ] **Step 4: Commit.**

```bash
git add backend/app/schemas/image.py backend/app/api/v1/endpoints/images.py
git commit -m "feat(backend): PUT /images/{id}/tags for future tag-edit UI"
```

---

## Task 6: MCP `BackendClient` carries tags + filter

**Files:**
- Modify: `mcp-server/src/mcp_server/backend.py`
- Modify: `mcp-server/src/mcp_server/backend_local.py`
- Modify: `mcp-server/src/mcp_server/backend_http.py`

- [ ] **Step 1: Extend `ImageMeta`** in `mcp-server/src/mcp_server/backend.py`:

```python
@dataclass(frozen=True)
class ImageMeta:
    id: str
    original_filename: str
    created_at: str
    width: int
    height: int
    format: str
    current_size: int
    tags: tuple[str, ...] = ()
```

(Tuple, not list, because the dataclass is frozen.)

- [ ] **Step 2: Extend the Protocol signatures** in the same file:

```python
class BackendClient(Protocol):
    async def list_user_images(
        self, user_id: str, limit: int, tag: str | None = None
    ) -> list[ImageMeta]: ...

    async def get_image(self, user_id: str, image_id: str) -> ImageBytes | None: ...
```

- [ ] **Step 3: Update `backend_local.py`** to honour the `tag` filter and populate `tags` in `ImageMeta`. The simplest place to add the filter is in a custom SQL query since `ImageService.get_user_images` doesn't support filtering. Add (or call) a helper that filters using `json_each`:

```python
    async def list_user_images(
        self, user_id: str, limit: int, tag: str | None = None,
    ) -> list[ImageMeta]:
        async with self._session_factory() as db:
            if tag is None:
                images = (await ImageService.get_user_images(db, user_id))[:limit]
            else:
                from sqlalchemy import text
                result = await db.execute(
                    text(
                        """
                        SELECT DISTINCT i.* FROM images i, json_each(i.tags) je
                        WHERE i.user_id = :user_id
                          AND lower(je.value) = lower(:tag)
                        ORDER BY i.created_at DESC
                        LIMIT :limit
                        """
                    ),
                    {"user_id": user_id, "tag": tag, "limit": limit},
                )
                from app.models.models import Image
                images = [Image(**dict(row._mapping)) for row in result]
        return [self._meta(img) for img in images]

    def _meta(self, img) -> ImageMeta:
        from app.services.image_service import ImageService
        return ImageMeta(
            id=img.id,
            original_filename=img.original_filename,
            created_at=_iso(img.created_at),
            width=img.width,
            height=img.height,
            format=img.format,
            current_size=img.current_size,
            tags=tuple(ImageService.get_tags(img)),
        )
```

Replace the existing inline `ImageMeta(...)` constructor calls with `self._meta(img)` to keep tag population consistent.

`get_image` likewise: when constructing `meta`, set `tags=tuple(ImageService.get_tags(img))`.

- [ ] **Step 4: Update `backend_http.py`** — pass `tag` as a query param and read `tags` from the JSON response:

```python
    async def list_user_images(
        self, user_id: str, limit: int, tag: str | None = None,
    ) -> list[ImageMeta]:
        params = {}
        if tag is not None:
            params["tag"] = tag
        r = await self._client.get(
            f"{self._base_url}/api/v1/images/user/{user_id}",
            params=params,
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
                tags=tuple(img.get("tags", [])),
            )
            for img in images
        ]
```

`get_image` likewise: read `tags` from `meta_json` and pass `tags=tuple(meta_json.get("tags", []))` into the `ImageMeta`.

- [ ] **Step 5: Smoke-import.**

Run: `cd /home/philg/src/python/ImageTools && PYTHONPATH=mcp-server/src python -c "from mcp_server.backend_http import HttpBackendClient; print('ok')"`

- [ ] **Step 6: Commit.**

```bash
git add mcp-server/src/mcp_server/backend.py mcp-server/src/mcp_server/backend_local.py mcp-server/src/mcp_server/backend_http.py
git commit -m "feat(mcp-server): backend clients carry tags and accept tag filter"
```

---

## Task 7: Backend list-images endpoint accepts `tag` query param

**Files:**
- Modify: `backend/app/api/v1/endpoints/images.py`
- Modify: `backend/app/services/image_service.py`

The HTTP backend client (Task 6) calls `GET /api/v1/images/user/{user_id}?tag=…`. Today that endpoint does not honour `tag`. Add the filter.

- [ ] **Step 1: Extend `ImageService.get_user_images`** with an optional `tag` parameter (default `None`). When set, apply the same `json_each` filter as `LocalBackendClient`:

```python
    @staticmethod
    async def get_user_images(
        db: AsyncSession, user_id: str, *, tag: str | None = None,
    ):
        if tag is None:
            result = await db.execute(
                select(Image)
                .where(Image.user_id == user_id)
                .order_by(Image.created_at.desc())
            )
            return list(result.scalars().all())
        result = await db.execute(
            text("""
                SELECT DISTINCT i.* FROM images i, json_each(i.tags) je
                WHERE i.user_id = :user_id AND lower(je.value) = lower(:tag)
                ORDER BY i.created_at DESC
            """),
            {"user_id": user_id, "tag": tag},
        )
        return [Image(**dict(row._mapping)) for row in result]
```

(Keep the existing un-tagged path intact — read the function before editing to minimise churn.)

- [ ] **Step 2: Accept `tag` query param** at `backend/app/api/v1/endpoints/images.py` in the `GET /user/{user_id}` handler (around line 59):

```python
@router.get("/user/{user_id}", response_model=List[ImageResponse])
async def get_user_images(
    user_id: str,
    tag: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    images = await ImageService.get_user_images(db, user_id, tag=tag)
    ...
```

- [ ] **Step 3: Smoke-import.**

Run: `cd backend && python -c "from app.main import app; print('ok')"`

- [ ] **Step 4: Commit.**

```bash
git add backend/app/services/image_service.py backend/app/api/v1/endpoints/images.py
git commit -m "feat(backend): GET /images/user/{uid} accepts tag filter"
```

---

## Task 8: MCP tool handlers + FastMCP signatures accept `tag`

**Files:**
- Modify: `mcp-server/src/mcp_server/tools.py`
- Modify: `mcp-server/src/mcp_server/server.py`
- Modify: `mcp-server/src/mcp_server/stdio.py`
- Modify: `backend/tests/test_mcp_tools.py`

- [ ] **Step 1: Extend tests first** in `backend/tests/test_mcp_tools.py`. Update the `FakeBackend` to honour `tag`:

```python
class FakeBackend:
    def __init__(self, images, bytes_map=None):
        self._images = images
        self._bytes = bytes_map or {}

    async def list_user_images(self, user_id, limit, tag=None):
        imgs = self._images
        if tag is not None:
            t = tag.lower()
            imgs = [i for i in imgs if any(x.lower() == t for x in i.tags)]
        return imgs[:limit]

    async def get_image(self, user_id, image_id):
        for img in self._images:
            if img.id == image_id:
                return ImageBytes(meta=img, data=self._bytes.get(image_id, b""), mime_type="image/png")
        return None
```

(Keep existing tests; just update the constructor and add `tag` to the
`list_user_images` signature.)

Add a new test:

```python
@pytest.mark.asyncio
async def test_list_recent_filters_by_tag():
    a = ImageMeta(id="a", original_filename="a.png", created_at="2026-04-25T10:01:00Z",
                  width=1, height=1, format="PNG", current_size=1, tags=("pos",))
    b = ImageMeta(id="b", original_filename="b.png", created_at="2026-04-25T10:02:00Z",
                  width=1, height=1, format="PNG", current_size=1, tags=("kiosk",))
    c = ImageMeta(id="c", original_filename="c.png", created_at="2026-04-25T10:03:00Z",
                  width=1, height=1, format="PNG", current_size=1, tags=("POS",))
    backend = FakeBackend([c, b, a])
    result = await list_recent_images(backend, "u", count=10, tag="pos")
    assert [i["id"] for i in result["images"]] == ["c", "a"]
```

- [ ] **Step 2: Run, expect failures** (signatures don't accept `tag` yet).

- [ ] **Step 3: Update `tools.py`**:

```python
async def list_recent_images(
    backend: BackendClient, user_id: str, count: int = DEFAULT_LIST_COUNT,
    tag: str | None = None,
) -> dict[str, Any]:
    clamped, was_clamped = _clamp(count, 1, MAX_LIST_COUNT)
    metas = await backend.list_user_images(user_id, clamped, tag=tag)
    return {"images": [_meta_dict(m) for m in metas], "clamped": was_clamped}


async def get_recent_images(
    backend: BackendClient, user_id: str, count: int = DEFAULT_RECENT_COUNT,
    tag: str | None = None,
) -> dict[str, Any]:
    clamped, was_clamped = _clamp(count, 1, MAX_RECENT_COUNT)
    metas = await backend.list_user_images(user_id, clamped, tag=tag)
    images, missing = [], []
    for m in metas:
        result = await backend.get_image(user_id, m.id)
        if result is None:
            missing.append(m.id)
            continue
        images.append({"meta": _meta_dict(result.meta), "data": result.data, "mime_type": result.mime_type})
    return {"images": images, "clamped": was_clamped, "missing": missing}
```

`_meta_dict(m)` continues to use `asdict(m)`, which will now include `tags`.

- [ ] **Step 4: Update `server.py` tool sigs.** (Recall: no `from __future__ import annotations` because mcp 1.12.4 chokes on string annotations.) Make `tag` Optional with `None` default:

```python
@mcp.tool()
async def list_recent_images(count: int = 10, tag: Optional[str] = None) -> dict[str, Any]:
    """... When tag is set, only images whose tags contain `tag`
    (case-insensitive) are returned."""
    return await tool_fns.list_recent_images(backend, _user_id(), count, tag=tag)


@mcp.tool()
async def get_recent_images(count: int = 1, tag: Optional[str] = None) -> list:
    """... When tag is set, only tag-matching images are fetched."""
    result = await tool_fns.get_recent_images(backend, _user_id(), count, tag=tag)
    out: list = []
    for img in result["images"]:
        out.extend(_to_mcp_content(img["data"], img["mime_type"], img["meta"]))
    return out
```

- [ ] **Step 5: Same for `stdio.py`.** Mirror the signatures with `tag: Optional[str] = None`.

- [ ] **Step 6: Run all backend tests.**

Run: `cd backend && PYTHONPATH=../mcp-server/src pytest -v`
Expected: previous count + 1 new (tag-filter) test all pass.

- [ ] **Step 7: Commit.**

```bash
git add mcp-server/src/mcp_server/tools.py mcp-server/src/mcp_server/server.py mcp-server/src/mcp_server/stdio.py backend/tests/test_mcp_tools.py
git commit -m "feat(mcp-server): tag filter on list_recent_images and get_recent_images"
```

---

## Task 9: Browser addons — current-tag input, autocomplete, persistence (Chrome + Firefox)

**Files** (mirror in both `browser-addons/chrome/` and `browser-addons/firefox/`):
- Modify: `popup.html`
- Modify: `popup.js`
- Modify: `content.js` (selection-capture upload path)
- Modify: `background.js` (full-page upload path)

- [ ] **Step 1: Add the input + datalist to `popup.html`.** Place above the existing capture buttons (read the file first to find a reasonable spot):

```html
<div class="tag-row">
  <label for="current-tag">Tag uploads as:</label>
  <input id="current-tag" type="text" list="tag-suggestions"
         placeholder="(none)" maxlength="64" autocomplete="off" />
  <button id="clear-tag" type="button" title="Clear current tag">×</button>
  <datalist id="tag-suggestions"></datalist>
</div>
```

Add scoped CSS for the row:

```css
.tag-row { display: flex; gap: 6px; align-items: center; margin: 8px 0; }
.tag-row input { flex: 1; padding: 4px 6px; }
.tag-row button { padding: 0 8px; }
```

- [ ] **Step 2: Wire up `popup.js`.** At the top of the existing initialisation, add:

```javascript
const TAG_KEY = 'imagetools_current_tag';

async function loadCurrentTag() {
  const { [TAG_KEY]: tag } = await browser.storage.local.get(TAG_KEY);
  document.getElementById('current-tag').value = tag || '';
}

async function persistCurrentTag(tag) {
  if (tag) {
    await browser.storage.local.set({ [TAG_KEY]: tag });
  } else {
    await browser.storage.local.remove(TAG_KEY);
  }
}

async function refreshTagSuggestions() {
  try {
    // Fetch from the connected backend; the popup already knows the user_id
    // via the existing connection state — reuse that helper.
    const userId = await getUserId();
    const baseUrl = await getBaseUrl();
    if (!userId || !baseUrl) return;
    const r = await fetch(`${baseUrl}/api/v1/users/${userId}/tags`);
    if (!r.ok) return;
    const tags = await r.json();
    const dl = document.getElementById('tag-suggestions');
    dl.innerHTML = '';
    for (const { tag } of tags) {
      const opt = document.createElement('option');
      opt.value = tag;
      dl.appendChild(opt);
    }
  } catch (e) {
    /* network errors here are non-fatal — leave suggestions empty */
  }
}

document.getElementById('current-tag').addEventListener('change', e => {
  persistCurrentTag(e.target.value.trim());
});
document.getElementById('clear-tag').addEventListener('click', () => {
  document.getElementById('current-tag').value = '';
  persistCurrentTag('');
});
```

Call `loadCurrentTag()` and `refreshTagSuggestions()` from the existing
init function (the function that already runs on `DOMContentLoaded`).

`getUserId()` and `getBaseUrl()`: read the file to find existing helpers
(probably they already exist for the addon-connection state). If not,
inline the storage reads.

(Chrome uses `chrome.storage.local` and Firefox uses `browser.storage.local` — `browser` is polyfilled in modern Chrome via `webextension-polyfill` or via the existing addon's wrapper. Read the file to match the existing pattern.)

- [ ] **Step 3: Include the tag in upload payloads.** Find every place that builds the multipart upload (probably in `background.js` and possibly `content.js`). Pattern:

```javascript
async function buildUploadFormData(blob, filename) {
  const fd = new FormData();
  fd.append('file', blob, filename);
  const { imagetools_current_tag } = await browser.storage.local.get('imagetools_current_tag');
  if (imagetools_current_tag) {
    fd.append('tag', imagetools_current_tag);
  }
  return fd;
}
```

Replace the existing manual `FormData` construction with the helper, or
inline the `fd.append('tag', ...)` block at every existing upload site.

- [ ] **Step 4: Repeat all of Step 1–3 for the Firefox addon** at `browser-addons/firefox/`. The two addons have near-identical source so the diff should be the same. If anything diverges, follow the existing addon's pattern for that file.

- [ ] **Step 5: Manual smoke-test.** Load the addon as an unpacked extension, set a tag, upload an image, confirm via the backend (curl `/api/v1/images/user/{uid}` and check `tags` field is populated).

- [ ] **Step 6: Commit.**

```bash
git add browser-addons/chrome browser-addons/firefox
git commit -m "feat(browser-addons): current-tag input with autocomplete attached to uploads"
```

---

## Task 10: Android — tag input + autocomplete + persistence

**Files:**
- Modify: `android-app/app/src/main/java/com/imagetools/mobile/ShareActivity.kt`
- Create: `android-app/app/src/main/java/com/imagetools/mobile/utils/TagPreferences.kt`
- Modify: `android-app/app/src/main/java/com/imagetools/mobile/data/network/ImageToolsApi.kt`

`ShareActivity` is the Compose-based share-target activity that handles incoming images. The current flow uploads immediately. We need a confirmation step that collects/edits a tag before upload, with autocomplete from the backend.

- [ ] **Step 1: Add `tag` to the API method.** In `ImageToolsApi.kt`:

```kotlin
@Multipart
@POST("api/v1/mobile/upload")
suspend fun uploadImage(
    @Part("long_term_secret") longTermSecret: RequestBody,
    @Part file: MultipartBody.Part,
    @Part("latitude") latitude: RequestBody? = null,
    @Part("longitude") longitude: RequestBody? = null,
    @Part("altitude") altitude: RequestBody? = null,
    @Part("tag") tag: RequestBody? = null
): Response<...>

// Plus: GET /api/v1/users/{user_id}/tags
@GET("api/v1/users/{user_id}/tags")
suspend fun listUserTags(@Path("user_id") userId: String): Response<List<TagDto>>
```

Add `data class TagDto(val tag: String, val last_used_at: String?)` in the same models package as `QRCodeData.kt`.

- [ ] **Step 2: Add `TagPreferences`** at `utils/TagPreferences.kt`, mirroring `PairingPreferences.kt`:

```kotlin
package com.imagetools.mobile.utils

import android.content.Context
import android.content.SharedPreferences

class TagPreferences(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("imagetools_tags", Context.MODE_PRIVATE)

    var currentTag: String?
        get() = prefs.getString(KEY_CURRENT_TAG, null)?.takeIf { it.isNotBlank() }
        set(value) {
            prefs.edit().apply {
                if (value.isNullOrBlank()) remove(KEY_CURRENT_TAG)
                else putString(KEY_CURRENT_TAG, value.trim())
                apply()
            }
        }

    companion object {
        private const val KEY_CURRENT_TAG = "current_tag"
    }
}
```

- [ ] **Step 3: Insert a tag-collection step in `ShareActivity`.** Replace the direct `checkPermissionAndUpload(...)` call with a Compose screen that shows the image preview, an `OutlinedTextField` for the tag with a dropdown of suggestions fetched from the API, a "Clear tag" button, and an "Upload" button. Suggestions are populated once on screen entry.

```kotlin
// Pseudocode for the Compose flow added inside setContent { ... }
val prefs = remember { TagPreferences(this) }
var tag by remember { mutableStateOf(prefs.currentTag ?: "") }
var suggestions by remember { mutableStateOf<List<String>>(emptyList()) }

LaunchedEffect(Unit) {
    suggestions = try {
        RetrofitClient.getApi().listUserTags(userId).body().orEmpty().map { it.tag }
    } catch (e: Exception) { emptyList() }
}

Column { 
    Text("Tag:")
    OutlinedTextField(
        value = tag, onValueChange = { tag = it },
        modifier = Modifier.fillMaxWidth(), singleLine = true,
    )
    LazyColumn { items(suggestions.filter { it.startsWith(tag, ignoreCase = true) }) { s ->
        Text(s, modifier = Modifier.clickable { tag = s }.padding(8.dp))
    }}
    Button(onClick = {
        prefs.currentTag = tag
        checkPermissionAndUpload(imageUris)
    }) { Text("Upload") }
}
```

(Adapt to the existing `ShareActivity` Compose structure — read the file first to understand the existing `setContent { … }` block.)

- [ ] **Step 4: Pass the tag into `uploadImageSync`.** Find the existing `uploadImage(...)` call site (line ~665 in `ShareActivity.kt`) and add a `tag` part:

```kotlin
val tagBody = TagPreferences(this).currentTag
    ?.toRequestBody("text/plain".toMediaTypeOrNull())
val response = RetrofitClient.getApi().uploadImage(
    longTermSecret = ...,
    file = ...,
    latitude = ...,
    longitude = ...,
    altitude = ...,
    tag = tagBody,
)
```

- [ ] **Step 5: Build the APK.**

Run: `cd android-app && ./gradlew assembleRelease`
Expected: BUILD SUCCESSFUL.

(If the Android build environment isn't set up, mark this task DONE_WITH_CONCERNS and ask the operator to build manually.)

- [ ] **Step 6: Commit.**

```bash
git add android-app
git commit -m "feat(android): per-upload tag with autocomplete and SharedPreferences persistence"
```

---

## Task 11: Frontend — render tag chips on image cards

**Files:**
- Modify: `frontend/src/components/ImageCard.vue`

- [ ] **Step 1: Render tags.** Find the section in `ImageCard.vue` that displays `image.original_filename` (somewhere in the `<template>`). Add a tag-chip row beneath:

```vue
<div v-if="image.tags && image.tags.length" class="tag-chips">
  <span v-for="t in image.tags" :key="t" class="tag-chip">{{ t }}</span>
</div>
```

Add scoped CSS:

```css
.tag-chips { display: flex; flex-wrap: wrap; gap: 0.25rem; margin-top: 0.25rem; }
.tag-chip {
  font-size: 0.75rem; padding: 0.15rem 0.5rem;
  background: #eef; color: #336; border-radius: 999px;
}
```

- [ ] **Step 2: `npm run build`.**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 3: Commit.**

```bash
git add frontend/src/components/ImageCard.vue
git commit -m "feat(frontend): render tag chips on image cards"
```

---

## Self-Review

**Spec coverage**

| Spec requirement | Task |
|---|---|
| `images.tags` JSON column with explicit migration | Task 1 |
| Upload endpoints accept `tag` form field | Task 3 |
| Tag list endpoint for autocomplete | Task 4 |
| `PUT /tags` for forward compat | Task 5 |
| MCP `BackendClient` filter + tags in metadata | Task 6 |
| Backend list-images `tag` query param | Task 7 |
| MCP tools `tag` arg | Task 8 |
| Browser addon current-tag input + autocomplete | Task 9 |
| Android tag input + autocomplete | Task 10 |
| Frontend tag chips | Task 11 |
| Case-insensitive matching | Task 6, 7, 8 (`lower(je.value) = lower(:tag)` and Python `.lower()`) |

**No placeholders.** All tasks include complete code blocks; no "TODO" / "TBD".

**Type consistency.** `ImageMeta.tags` is `tuple[str, ...]` everywhere; tool functions all use `tag: str | None = None` (Python) and `tag: Optional[str] = None` (FastMCP, where the future-import-annotations footgun forbids PEP 604).
