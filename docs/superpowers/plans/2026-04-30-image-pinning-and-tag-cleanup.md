# MCP Image Pinning + HMAC Presigned URLs + Share Viewer + Tag Cleanup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give AI agents (via the MCP server) three coupled capabilities — pin an image to delay deletion, mint a long-lived HMAC-signed URL for embedding in generated documents, and download image bytes — and surface pin state to humans in the web UI (badge + unpin with confirmation). Also upgrade the existing 5-minute share link to render an HTML viewer page (image + tags + capture date + effective expiry), expose a matching "Copy Document Link" action in the gallery, and fix the tag-filter chips so orphan tags disappear from the UI.

**Architecture:**
- **Pinning is MCP-only.** Agents call `pin_image` / `unpin_image` / `get_presigned_url` / `download_image`. The web UI never offers a "pin" button — it shows a 📌 badge and an Unpin-with-confirmation override. Re-pinning is **idempotent and never shortens** an existing pin: `pin_expires_at = max(existing, now + duration_days)`.
- **Pin state** is one nullable column `pin_expires_at` on `images`. The cleanup scheduler treats `max(pin_expires_at, created_at) + retention_days` as the effective deletion timestamp.
- **Presigned URLs are stateless HMAC tokens** — no DB table, no scheduled cleanup. URL form: `{web_ui_host}/i/{base64url(image_id|exp_epoch)}.{hmac_sha256_hex}`. Server verifies HMAC + expiry, then serves bytes. Hostname comes from `get_instance_url(request)` (X-Forwarded-Host → Host → `INSTANCE_URL`).
- **HMAC keyed by `PRESIGNED_URL_SECRET` AND a per-image `url_pepper`.** The pepper is a 16-byte random hex on every `Image` row, server-side only (never in the URL). Rotating an image's pepper invalidates *all* outstanding presigned URLs for that image — this is the **revocation mechanism**: `revoke_presigned_urls` MCP tool / `DELETE /images/{id}/presigned-urls` REST / "Invalidate document links" web menu action. Use it when a draft document referencing the screenshot is finalized, or when a screenshot is replaced and the old URL must stop resolving.
- **Minting a URL bumps the pin.** `POST /images/{id}/presigned-url` calls `pin_image(duration_days=ttl_days)` so the agent gets one-call retention + URL.
- **Download** is the existing MCP `get_image` tool exposed under a clearer name (`download_image`).
- **Share-link viewer.** Existing `/s/{token}` route now returns an HTML page (image in a frame, tag chips, capture date, effective expiry that respects pin state). Raw bytes move to `/s/{token}/raw` so the page's `<img>` resolves. The 5-minute TTL and in-memory dict storage are **unchanged** — per the original 2026-03-24 design, vanish-on-restart is part of the security model, and the new HMAC presigned URLs already cover the "survives restart" use case. The viewer reads image metadata (tags, capture date, pin/expiry) fresh from the `Image` row at view time.
- **Rate limiting.** Per-IP token-bucket limits via `slowapi` on every public-facing image route — `/i/{token}` (presigned), `/s/{token}` (share viewer HTML), `/s/{token}/raw` (share bytes). Default 60 req/min per IP, configurable. Goal is abuse / scraping deterrence, not strong protection.
- **Tag-display cleanup** is a frontend cache fix: `loadUserTags()` after `deleteImage`. Backend tag list endpoint already excludes orphans.

**Tech Stack:** FastAPI, SQLAlchemy (async), SQLite, the `mcp` Python SDK (`FastMCP`), Pydantic v2, Vue 3 + Pinia, `pytest` + `pytest-asyncio`. HMAC via `hmac` + `hashlib` from the stdlib.

---

## Decision Points (review before implementation)

1. **Default pin duration: 90 days.** `PIN_DEFAULT_DURATION_DAYS` setting. Hard cap `PIN_MAX_DURATION_DAYS=3650`.
2. **Re-pinning extends, never shortens.** `pin_image(duration_days=N)` sets `pin_expires_at = max(existing, now + N)`. `unpin_image` clears it.
3. **Presigned URL = stateless HMAC.** Form: `/i/{payload_b64}.{sig_hex}`, payload = `base64url("{image_id}|{exp_epoch}")`. Verified with `hmac.compare_digest`. No DB writes for URLs, no cleanup task, no revocation list (revoke = unpin + change `PRESIGNED_URL_SECRET`).
4. **HMAC secret:** `PRESIGNED_URL_SECRET` setting. If blank at startup, the backend generates an ephemeral random secret and logs a warning — URLs become invalid across restarts. Production deployments must set the secret in `.env`.
5. **URL hostname** = `get_instance_url(request)` (existing helper). The mint endpoint takes the request, so the URL embeds the public web-UI host.
6. **Mint also bumps pin.** `POST /images/{id}/presigned-url` calls `pin_image(ttl_days)` on the same image. The agent gets one tool call for both.
7. **Auto-cleanup remains anonymous-only.** Pinning works for any user; deletion only fires for `ANONYMOUS_USER_ID`. UI hides "Auto-deletes" tooltip line for non-anonymous users.
8. **Effective expiration formula:** `eff = max(pin_expires_at, created_at) + ANONYMOUS_IMAGE_RETENTION_DAYS`; past pins are ignored.
9. **Share-link viewer page** is HTML; existing programmatic users that fetch `/s/{token}` for raw bytes break. The fix is the new `/s/{token}/raw` route. **Migration risk:** check if any external consumers rely on `/s/{token}` returning bytes — none in this repo (it's only used by the web UI's "Copy Share Link" button, which currently just displays the URL). Acceptable.
10. **Share links stay in-memory.** Earlier draft of this plan added DB persistence; we dropped it after re-reading the 2026-03-24 spec — the 5-minute TTL is coupled with vanish-on-restart as part of the security model, and HMAC presigned URLs already cover the "needs to outlive a restart" case.
11. **Rate limit defaults: 60 req/min per IP** on `/i/{token}`, `/s/{token}`, `/s/{token}/raw`. Configurable via `RATE_LIMIT_IMAGE_ACCESS` setting. Excessive burst returns HTTP 429.
12. **Per-image url_pepper for revocation.** Cheapest mechanism that lets a user invalidate just the URLs for one image without rotating the global secret. Random 16-byte hex; backfilled for existing rows; included in HMAC; rotated by `revoke_presigned_urls`. Trade-off: each `/i/{token}` request now does one DB lookup (read the image to fetch its pepper) before HMAC verify. With rate limiting at 60/min/IP, the lookup cost is bounded.

---

## File Structure

### Backend

| File | Disposition | Responsibility |
|------|-------------|----------------|
| `backend/app/models/models.py` | Modify | Add `pin_expires_at` and `url_pepper` to `Image` |
| `backend/app/core/migrate.py` | Modify | Migrations for `images.pin_expires_at` AND `images.url_pepper` |
| `backend/app/core/config.py` | Modify | Pin + presigned-URL settings + rate-limit settings |
| `backend/app/schemas/schemas.py` | Modify | Pin fields on `ImageResponse`; new `PinRequest`, `PresignedUrlRequest`, `PresignedUrlResponse` |
| `backend/app/services/image_service.py` | Modify | `pin_image`, `unpin_image`, `rotate_url_pepper`, `effective_expires_at`, `to_response` helper |
| `backend/app/services/presigned_url.py` | Create | `build_token` + `decode_token_unverified` + `verify_token` (HMAC, no DB; pepper-aware) |
| `backend/app/services/user_service.py` | Modify | `cleanup_anonymous_old_images` honours pin |
| `backend/app/services/share_service.py` | Unchanged | Stays in-memory — see Decision Point #10 |
| `backend/app/core/migrate.py` | Modify | Migration for `images.pin_expires_at` |
| `backend/app/core/rate_limit.py` | Create | `slowapi`-based limiter; one shared `Limiter` instance |
| `backend/app/api/v1/endpoints/images.py` | Modify | `PUT/DELETE /images/{id}/pin`; `POST /images/{id}/presigned-url`; `DELETE /images/{id}/presigned-urls` (revoke all) |
| `backend/app/api/endpoints/presigned.py` | Create | `GET /i/{token}` HMAC-verified image serve, rate-limited |
| `backend/app/api/endpoints/share_view.py` | Create or Modify existing | `/s/{token}` HTML, `/s/{token}/raw` bytes — both rate-limited |
| `backend/app/main.py` | Modify | Register the new routers + the `slowapi` exception handler |
| `backend/requirements.txt` | Modify | Add `slowapi` |
| `backend/tests/test_image_pinning.py` | Create | Pin helpers + cleanup |
| `backend/tests/test_presigned_url.py` | Create | HMAC mint/verify + endpoints |
| `backend/tests/test_share_view.py` | Create | Share viewer HTML + raw routes |
| `backend/tests/test_rate_limit.py` | Create | Rate limiting on the three image routes |

### MCP server

| File | Disposition | Responsibility |
|------|-------------|----------------|
| `mcp-server/src/mcp_server/backend.py` | Modify | Extend Protocol + `ImageMeta` with pin fields; add `PresignedUrl` dataclass |
| `mcp-server/src/mcp_server/backend_http.py` | Modify | Implement `pin_image`, `unpin_image`, `create_presigned_url` |
| `mcp-server/src/mcp_server/backend_local.py` | Modify | Same against in-process services |
| `mcp-server/src/mcp_server/tools.py` | Modify | `pin_image`, `unpin_image`, `get_presigned_url`, `download_image` |
| `mcp-server/src/mcp_server/server.py` | Modify | Register the four tools with FastMCP |
| `mcp-server/tests/test_tools_pin.py` | Create | Tool unit tests |

### Frontend

| File | Disposition | Responsibility |
|------|-------------|----------------|
| `frontend/src/services/api.js` | Modify | `unpinImage` + `createDocumentLink` |
| `frontend/src/stores/imageStore.js` | Modify | `unpinImage` action; refresh tags after delete |
| `frontend/src/components/ImageCard.vue` | Modify | Pin badge, expiration tooltip, Unpin (with confirmation), "Copy Document Link" menu action |

---

## Task 1 — `pin_expires_at` and `url_pepper` columns on `Image`

**Files:** Modify `backend/app/models/models.py:25-47`

- [ ] **Step 1:** Add `import secrets` to the file imports (alongside the existing imports). Then in `class Image(Base):`, after the `tags` column (line 45), append:

```python
    # MCP-only pinning. When non-null and in the future, the image is
    # exempt from auto-cleanup until pin_expires_at + retention_days.
    pin_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Per-image pepper folded into the HMAC of presigned URLs. Rotating this
    # value invalidates every outstanding /i/{token} URL for THIS image only,
    # without affecting any other image. Random 16-byte hex; never appears in
    # the URL itself; never returned in API responses.
    url_pepper = Column(String, nullable=False, default=lambda: secrets.token_hex(16))
```

- [ ] **Step 2:** Run: `cd backend && ./venv/bin/python -c "from app.models.models import Image; print('pin_expires_at' in Image.__table__.columns, 'url_pepper' in Image.__table__.columns)"`
Expected: `True True`.

- [ ] **Step 3:** Commit: `git add backend/app/models/models.py && git commit -m "feat(backend): add pin_expires_at and url_pepper columns to Image"`

---

## Task 2 — Migrations for `images.pin_expires_at` and `images.url_pepper`

**Files:** Modify `backend/app/core/migrate.py` (after the existing tags migration block)

- [ ] **Step 1:** Append both migration blocks:

```python
        # ------------------------------------------------------------------ #
        # BLOCK: add images.pin_expires_at for MCP image pinning             #
        # ------------------------------------------------------------------ #
        result = await conn.execute(text("PRAGMA table_info(images)"))
        cols = [row[1] for row in result.fetchall()]
        if "pin_expires_at" not in cols:
            logger.info("Adding pin_expires_at column to images table...")
            await conn.execute(text("ALTER TABLE images ADD COLUMN pin_expires_at DATETIME"))
            migrations_applied.append("images.pin_expires_at")

        # ------------------------------------------------------------------ #
        # BLOCK: add images.url_pepper for per-image presigned-URL revocation #
        # ------------------------------------------------------------------ #
        result = await conn.execute(text("PRAGMA table_info(images)"))
        cols = [row[1] for row in result.fetchall()]
        if "url_pepper" not in cols:
            logger.info("Adding url_pepper column to images table and backfilling...")
            # SQLite ALTER TABLE ADD COLUMN with NOT NULL requires a default.
            # We use the empty string as the placeholder default, then backfill.
            await conn.execute(
                text("ALTER TABLE images ADD COLUMN url_pepper VARCHAR NOT NULL DEFAULT ''")
            )
            # Backfill: SQLite's randomblob(16) gives 16 cryptographically random
            # bytes; lower(hex(...)) renders to a 32-char hex string. Each row
            # gets its own value because randomblob is evaluated per-row.
            await conn.execute(
                text("UPDATE images SET url_pepper = lower(hex(randomblob(16))) WHERE url_pepper = ''")
            )
            migrations_applied.append("images.url_pepper (with backfill)")
```

- [ ] **Step 2:** Run migration: `cd backend && ./venv/bin/python -c "import asyncio; from app.core.migrate import migrate_database; asyncio.run(migrate_database())"`
Expected: log lines for both migrations.

- [ ] **Step 3:** Verify: `sqlite3 backend/storage/imagetools.db "PRAGMA table_info(images);" | grep -E 'pin_expires|url_pepper'` and `sqlite3 backend/storage/imagetools.db "SELECT id, length(url_pepper) FROM images LIMIT 5;"`
Expected: both columns present; every existing row has `length(url_pepper) = 32`.

- [ ] **Step 4:** Commit: `git add backend/app/core/migrate.py && git commit -m "feat(backend): migrations for images.pin_expires_at and images.url_pepper"`

---

## Task 3 — Settings

**Files:** Modify `backend/app/core/config.py:24-25`

- [ ] **Step 1:** After `ANONYMOUS_IMAGE_RETENTION_DAYS`, add:

```python
    PIN_DEFAULT_DURATION_DAYS: int = 90      # Default duration for MCP-issued pins
    PIN_MAX_DURATION_DAYS: int = 3650        # Hard cap on pin duration (~10 years)
    # HMAC secret for presigned image URLs. If blank, the backend generates an
    # ephemeral random secret at startup and logs a warning — URLs invalidate
    # across restarts. Production must set this in .env.
    PRESIGNED_URL_SECRET: str = ""
    # Per-IP rate limit applied to /i/{token}, /s/{token}, /s/{token}/raw.
    # slowapi syntax: "<count>/<period>" (e.g. "60/minute", "10/second").
    RATE_LIMIT_IMAGE_ACCESS: str = "60/minute"
```

- [ ] **Step 2:** In `backend/app/main.py`, near the top of the FastAPI startup hook (after `settings` import), add an ephemeral-secret bootstrap:

```python
import secrets as _secrets
from app.core.config import settings

if not settings.PRESIGNED_URL_SECRET:
    settings.PRESIGNED_URL_SECRET = _secrets.token_hex(32)
    logger = logging.getLogger(__name__)
    logger.warning(
        "PRESIGNED_URL_SECRET is not set. Generated an ephemeral secret; "
        "previously-minted URLs will be invalidated on restart. "
        "Set PRESIGNED_URL_SECRET in .env for stable URLs."
    )
```

(If the file already imports `secrets`, drop the alias. Place the block where the rest of the startup config lives — verify it executes before the routers handle requests.)

- [ ] **Step 3:** Add `slowapi` to `backend/requirements.txt` (one new line):

```
slowapi>=0.1.9
```

Then install: `cd backend && ./venv/bin/pip install slowapi>=0.1.9`. Verify: `./venv/bin/python -c "import slowapi; print(slowapi.__version__)"`.

- [ ] **Step 4:** Verify settings load: `cd backend && ./venv/bin/python -c "from app.core.config import settings; print(settings.PIN_DEFAULT_DURATION_DAYS, repr(settings.PRESIGNED_URL_SECRET), settings.RATE_LIMIT_IMAGE_ACCESS)"`
Expected: `90 '' '60/minute'` (PRESIGNED_URL_SECRET is empty until startup bootstrap fills it).

- [ ] **Step 5:** Commit: `git add backend/app/core/config.py backend/app/main.py backend/requirements.txt && git commit -m "feat(backend): pin, presigned-URL, and rate-limit settings; slowapi dep"`

---

## Task 4 — Pin / unpin helpers + `effective_expires_at` (TDD, with extend semantic)

**Files:**
- Create: `backend/tests/test_image_pinning.py`
- Modify: `backend/app/services/image_service.py`

- [ ] **Step 1: Failing tests**

```python
import pytest
from datetime import datetime, timedelta, timezone
from app.models.models import Image
from app.services.image_service import ImageService


def _make_image(user_id: str, image_id: str = "img-1") -> Image:
    return Image(
        id=image_id, user_id=user_id, original_filename="x.png",
        original_size=1, current_path="/tmp/x.png", current_size=1,
        width=1, height=1, format="PNG",
    )


async def test_pin_sets_expiry_for_unpinned(db_session, seeded_user):
    img = _make_image(seeded_user); db_session.add(img); await db_session.commit()
    before = datetime.now(timezone.utc)
    await ImageService.pin_image(db_session, img.id, duration_days=30)
    await db_session.refresh(img)
    delta = img.pin_expires_at - before
    assert timedelta(days=29, hours=23) < delta < timedelta(days=30, hours=1)


async def test_pin_extends_a_shorter_existing_pin(db_session, seeded_user):
    img = _make_image(seeded_user)
    img.pin_expires_at = datetime.now(timezone.utc) + timedelta(days=10)
    db_session.add(img); await db_session.commit()
    await ImageService.pin_image(db_session, img.id, duration_days=30)
    await db_session.refresh(img)
    delta = img.pin_expires_at - datetime.now(timezone.utc)
    assert timedelta(days=29, hours=23) < delta < timedelta(days=30, hours=1)


async def test_pin_does_not_shorten_a_longer_existing_pin(db_session, seeded_user):
    img = _make_image(seeded_user)
    img.pin_expires_at = datetime.now(timezone.utc) + timedelta(days=60)
    db_session.add(img); await db_session.commit()
    await ImageService.pin_image(db_session, img.id, duration_days=10)
    await db_session.refresh(img)
    delta = img.pin_expires_at - datetime.now(timezone.utc)
    assert timedelta(days=59) < delta < timedelta(days=61)


async def test_pin_rejects_bad_duration(db_session, seeded_user):
    img = _make_image(seeded_user); db_session.add(img); await db_session.commit()
    with pytest.raises(ValueError):
        await ImageService.pin_image(db_session, img.id, duration_days=0)
    with pytest.raises(ValueError):
        await ImageService.pin_image(db_session, img.id, duration_days=10_000)


async def test_unpin_clears_pin_expires_at(db_session, seeded_user):
    img = _make_image(seeded_user)
    img.pin_expires_at = datetime.now(timezone.utc) + timedelta(days=10)
    db_session.add(img); await db_session.commit()
    await ImageService.unpin_image(db_session, img.id)
    await db_session.refresh(img)
    assert img.pin_expires_at is None


async def test_pin_returns_none_for_missing(db_session):
    assert await ImageService.pin_image(db_session, "missing", duration_days=7) is None
    assert await ImageService.unpin_image(db_session, "missing") is None


def test_effective_expires_at_uses_future_pin():
    now = datetime.now(timezone.utc)
    eff = ImageService.effective_expires_at(
        created_at=now - timedelta(days=2),
        pin_expires_at=now + timedelta(days=10),
        retention_days=30,
    )
    assert eff == (now + timedelta(days=10)) + timedelta(days=30)


def test_effective_expires_at_ignores_past_pin():
    now = datetime.now(timezone.utc)
    eff = ImageService.effective_expires_at(
        created_at=now - timedelta(days=2),
        pin_expires_at=now - timedelta(days=1),
        retention_days=30,
    )
    assert eff == (now - timedelta(days=2)) + timedelta(days=30)
```

- [ ] **Step 2:** Run: `cd backend && ./venv/bin/pytest tests/test_image_pinning.py -v`
Expected: all 8 fail (helpers don't exist yet).

- [ ] **Step 3: Implement** — append to `class ImageService:` in `backend/app/services/image_service.py`. Add `from datetime import datetime, timedelta, timezone` and `from app.core.config import settings` to the imports if missing.

```python
    @staticmethod
    async def pin_image(db, image_id: str, duration_days: int):
        """Pin or extend a pin. Sets pin_expires_at = max(existing, now + duration_days).

        Re-pinning never shortens. unpin_image clears it.
        """
        if duration_days < 1 or duration_days > settings.PIN_MAX_DURATION_DAYS:
            raise ValueError(
                f"duration_days must be between 1 and {settings.PIN_MAX_DURATION_DAYS}"
            )
        image = await ImageService.get_image(db, image_id)
        if image is None:
            return None
        target = datetime.now(timezone.utc) + timedelta(days=duration_days)
        if image.pin_expires_at is None or image.pin_expires_at < target:
            image.pin_expires_at = target
            await db.commit()
            await db.refresh(image)
        return image

    @staticmethod
    async def unpin_image(db, image_id: str):
        image = await ImageService.get_image(db, image_id)
        if image is None:
            return None
        image.pin_expires_at = None
        await db.commit()
        await db.refresh(image)
        return image

    @staticmethod
    def effective_expires_at(created_at, pin_expires_at, retention_days: int):
        anchor = created_at
        if pin_expires_at is not None and pin_expires_at > datetime.now(timezone.utc):
            anchor = pin_expires_at
        return anchor + timedelta(days=retention_days)
```

- [ ] **Step 4:** Run tests: `cd backend && ./venv/bin/pytest tests/test_image_pinning.py -v`
Expected: 8 passed.

- [ ] **Step 5:** Commit: `git add backend/app/services/image_service.py backend/tests/test_image_pinning.py && git commit -m "feat(backend): pin/unpin helpers with extend-only semantic + effective_expires_at"`

---

## Task 5 — Cleanup respects pin (TDD)

**Files:**
- Modify: `backend/app/services/user_service.py:102-157`
- Append to: `backend/tests/test_image_pinning.py`

- [ ] **Step 1: Append failing tests**

```python
import sqlalchemy
from app.services.user_service import UserService, ANONYMOUS_USER_ID


async def _backdate(db_session, image_id, *, created_days_ago, pin_in_days=None):
    params = {"c": (datetime.now(timezone.utc) - timedelta(days=created_days_ago)).isoformat(), "i": image_id}
    sql = "UPDATE images SET created_at = :c"
    if pin_in_days is not None:
        sql += ", pin_expires_at = :p"
        params["p"] = (datetime.now(timezone.utc) + timedelta(days=pin_in_days)).isoformat()
    sql += " WHERE id = :i"
    await db_session.execute(sqlalchemy.text(sql), params)
    await db_session.commit()


async def test_cleanup_skips_pinned_anonymous_image(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.user_service.settings.STORAGE_PATH", str(tmp_path))
    img = _make_image(ANONYMOUS_USER_ID, image_id="pinned-old")
    db_session.add(img); await db_session.commit()
    await _backdate(db_session, "pinned-old", created_days_ago=100, pin_in_days=30)
    assert await UserService.cleanup_anonymous_old_images(db_session, days=30) == 0
    assert await ImageService.get_image(db_session, "pinned-old") is not None


async def test_cleanup_deletes_unpinned_old_anonymous(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.user_service.settings.STORAGE_PATH", str(tmp_path))
    img = _make_image(ANONYMOUS_USER_ID, image_id="old-unpinned")
    db_session.add(img); await db_session.commit()
    await _backdate(db_session, "old-unpinned", created_days_ago=100)
    assert await UserService.cleanup_anonymous_old_images(db_session, days=30) == 1
    assert await ImageService.get_image(db_session, "old-unpinned") is None
```

- [ ] **Step 2:** Run only the cleanup-skip test to confirm failure.

Run: `cd backend && ./venv/bin/pytest tests/test_image_pinning.py::test_cleanup_skips_pinned_anonymous_image -v`
Expected: fail.

- [ ] **Step 3: Update the cleanup query**

In `backend/app/services/user_service.py`, replace the `select(Image).where(...)` block in `cleanup_anonymous_old_images` (lines 113–117) with:

```python
        from sqlalchemy import or_
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await db.execute(
            select(Image)
            .where(Image.user_id == ANONYMOUS_USER_ID)
            .where(Image.created_at < cutoff)
            .where(or_(Image.pin_expires_at.is_(None), Image.pin_expires_at < cutoff))
        )
        old_images = result.scalars().all()
```

- [ ] **Step 4:** Run: `cd backend && ./venv/bin/pytest tests/test_image_pinning.py -v`
Expected: 10 passed.

- [ ] **Step 5:** Commit: `git add backend/app/services/user_service.py backend/tests/test_image_pinning.py && git commit -m "feat(backend): cleanup honours pin_expires_at"`

---

## Task 6 — Schemas

**Files:** Modify `backend/app/schemas/schemas.py:27-47`

- [ ] **Step 1:** Replace `class ImageResponse(BaseModel):` and append the new request/response models:

```python
class ImageResponse(BaseModel):
    id: str
    user_id: str
    original_filename: str
    original_size: int
    current_size: int
    width: int
    height: int
    format: str
    thumbnail_url: str
    image_url: str
    created_at: datetime
    updated_at: datetime
    tags: list[str] = []
    pin_expires_at: Optional[datetime] = None
    effective_expires_at: Optional[datetime] = None  # null for users not subject to retention

    class Config:
        from_attributes = True


class ImageTagsUpdate(BaseModel):
    tags: list[str]


class PinRequest(BaseModel):
    duration_days: Optional[int] = None  # None = use server default


class PresignedUrlRequest(BaseModel):
    ttl_days: Optional[int] = None  # None = use server default; bumps pin if shorter


class PresignedUrlResponse(BaseModel):
    url: str                     # absolute URL with the web-UI hostname
    token: str                   # the {payload}.{sig} portion (informational)
    expires_at: datetime         # URL expiry
    image_id: str
    pin_expires_at: datetime     # the resulting pin expiry (>= expires_at)
```

- [ ] **Step 2:** Verify: `cd backend && ./venv/bin/python -c "from app.schemas.schemas import PinRequest, PresignedUrlRequest, PresignedUrlResponse; print('ok')"`
Expected: `ok`.

- [ ] **Step 3:** Commit: `git add backend/app/schemas/schemas.py && git commit -m "feat(backend): pin + presigned-url schemas"`

---

## Task 7 — Centralise `ImageResponse` construction

The endpoint builds `ImageResponse(...)` by hand at six sites. Centralise to one helper before adding fields.

**Files:**
- Modify: `backend/app/services/image_service.py`
- Modify: `backend/app/api/v1/endpoints/images.py`

- [ ] **Step 1:** Append to `class ImageService:`:

```python
    @staticmethod
    def to_response(image, *, settings_obj=None):
        from app.schemas.schemas import ImageResponse
        from app.core.config import settings as default_settings
        from app.services.user_service import ANONYMOUS_USER_ID

        s = settings_obj or default_settings
        eff = None
        if image.user_id == ANONYMOUS_USER_ID:
            eff = ImageService.effective_expires_at(
                created_at=image.created_at,
                pin_expires_at=image.pin_expires_at,
                retention_days=s.ANONYMOUS_IMAGE_RETENTION_DAYS,
            )
        return ImageResponse(
            id=image.id,
            user_id=image.user_id,
            original_filename=image.original_filename,
            original_size=image.original_size,
            current_size=image.current_size,
            width=image.width,
            height=image.height,
            format=image.format,
            thumbnail_url=f"{s.API_PREFIX}/images/{image.id}/thumbnail",
            image_url=f"{s.API_PREFIX}/images/{image.id}/current",
            created_at=image.created_at,
            updated_at=image.updated_at,
            tags=ImageService.get_tags(image),
            pin_expires_at=image.pin_expires_at,
            effective_expires_at=eff,
        )
```

- [ ] **Step 2:** In `backend/app/api/v1/endpoints/images.py`, every `return ImageResponse(...)` (six sites: upload, list-loop, get, tag-update, plus inside resize) becomes `return ImageService.to_response(image)` (or `img` in the list loop). Leave `RotateResponse` / `FlipResponse` / `ResizeResponse` alone.

- [ ] **Step 3:** Run: `cd backend && ./venv/bin/pytest tests/ -v`
Expected: green.

- [ ] **Step 4:** Commit: `git add backend/app/services/image_service.py backend/app/api/v1/endpoints/images.py && git commit -m "refactor(backend): centralise ImageResponse via to_response"`

---

## Task 8 — Pin / unpin REST endpoints (TDD)

**Files:**
- Create: `backend/tests/test_pin_endpoints.py`
- Modify: `backend/app/api/v1/endpoints/images.py`

- [ ] **Step 1: Failing tests**

```python
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_put_pin_sets_expiry(client: AsyncClient, seeded_image):
    r = await client.put(f"/api/v1/images/{seeded_image['id']}/pin", json={"duration_days": 30})
    assert r.status_code == 200
    pin = datetime.fromisoformat(r.json()["pin_expires_at"].replace("Z", "+00:00"))
    delta = pin - datetime.now(timezone.utc)
    assert timedelta(days=29, hours=23) < delta < timedelta(days=30, hours=1)


@pytest.mark.asyncio
async def test_put_pin_default_duration(client: AsyncClient, seeded_image):
    r = await client.put(f"/api/v1/images/{seeded_image['id']}/pin", json={})
    pin = datetime.fromisoformat(r.json()["pin_expires_at"].replace("Z", "+00:00"))
    delta = pin - datetime.now(timezone.utc)
    assert timedelta(days=89, hours=23) < delta < timedelta(days=90, hours=1)


@pytest.mark.asyncio
async def test_put_pin_extends_not_shortens(client: AsyncClient, seeded_image):
    await client.put(f"/api/v1/images/{seeded_image['id']}/pin", json={"duration_days": 60})
    r = await client.put(f"/api/v1/images/{seeded_image['id']}/pin", json={"duration_days": 10})
    pin = datetime.fromisoformat(r.json()["pin_expires_at"].replace("Z", "+00:00"))
    delta = pin - datetime.now(timezone.utc)
    assert timedelta(days=59) < delta < timedelta(days=61)


@pytest.mark.asyncio
async def test_put_pin_rejects_zero(client: AsyncClient, seeded_image):
    r = await client.put(f"/api/v1/images/{seeded_image['id']}/pin", json={"duration_days": 0})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_put_pin_404_for_unknown(client: AsyncClient):
    r = await client.put("/api/v1/images/missing/pin", json={"duration_days": 30})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_pin_clears(client: AsyncClient, seeded_image):
    await client.put(f"/api/v1/images/{seeded_image['id']}/pin", json={"duration_days": 30})
    r = await client.delete(f"/api/v1/images/{seeded_image['id']}/pin")
    assert r.status_code == 200
    assert r.json()["pin_expires_at"] is None


@pytest.mark.asyncio
async def test_delete_pin_404_for_unknown(client: AsyncClient):
    r = await client.delete("/api/v1/images/missing/pin")
    assert r.status_code == 404
```

- [ ] **Step 2: Add `client` and `seeded_image` fixtures to `backend/tests/conftest.py` if missing**

```python
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.models import Image


@pytest_asyncio.fixture
async def client(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def seeded_image(db_session, seeded_user):
    img = Image(
        id="test-img-1", user_id=seeded_user, original_filename="x.png",
        original_size=10, current_path="/tmp/x.png", current_size=10,
        width=10, height=10, format="PNG",
    )
    db_session.add(img); await db_session.commit()
    return {"id": img.id, "user_id": img.user_id}
```

- [ ] **Step 3:** Run tests, confirm 7 failures.

- [ ] **Step 4: Add the endpoints** — in `backend/app/api/v1/endpoints/images.py` (add `PinRequest` to the schemas import line, then append):

```python
@router.put("/{image_id}/pin", response_model=ImageResponse)
async def pin_image_endpoint(
    image_id: str,
    payload: PinRequest,
    db: AsyncSession = Depends(get_db),
):
    """Pin or extend the pin on an image (MCP-only entrypoint)."""
    duration = payload.duration_days or settings.PIN_DEFAULT_DURATION_DAYS
    try:
        image = await ImageService.pin_image(db, image_id, duration_days=duration)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return ImageService.to_response(image)


@router.delete("/{image_id}/pin", response_model=ImageResponse)
async def unpin_image_endpoint(
    image_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Unpin an image. Used by both the MCP unpin tool and the web UI."""
    image = await ImageService.unpin_image(db, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return ImageService.to_response(image)
```

- [ ] **Step 5:** Run tests, confirm 7 passed.

- [ ] **Step 6:** Commit: `git add backend/app/api/v1/endpoints/images.py backend/tests/test_pin_endpoints.py backend/tests/conftest.py && git commit -m "feat(backend): PUT/DELETE /images/{id}/pin (extend-not-shorten)"`

---

## Task 9 — HMAC presigned-URL service (TDD, pepper-aware)

The service splits into three pure functions:
- `build_token(image_id, exp, pepper)` — constructs the token, baking the pepper into the HMAC.
- `decode_token_unverified(token)` — extracts `{image_id, exp, payload, sig}` without trusting the signature; the caller uses `image_id` to look up the image's current pepper.
- `verify_token(payload, sig, pepper, exp)` — recomputes the HMAC using the looked-up pepper and compares with `compare_digest`. Also enforces expiry.

This split is necessary because verification requires a DB round-trip (read the image's pepper) — and the caller, not the service, owns the DB session.

**Files:**
- Create: `backend/app/services/presigned_url.py`
- Create: `backend/tests/test_presigned_url.py`

- [ ] **Step 1: Failing tests**

```python
import time
import pytest
from app.services.presigned_url import build_token, decode_token_unverified, verify_token


def _setup_secret(monkeypatch):
    monkeypatch.setattr("app.services.presigned_url.settings.PRESIGNED_URL_SECRET", "test-secret")


def test_round_trip_decodes_image_id_and_exp(monkeypatch):
    _setup_secret(monkeypatch)
    exp = int(time.time()) + 3600
    token = build_token(image_id="abc-123", expires_at_epoch=exp, pepper="peppA")
    decoded = decode_token_unverified(token)
    assert decoded["image_id"] == "abc-123"
    assert decoded["exp"] == exp
    assert verify_token(payload=decoded["payload"], sig=decoded["sig"], pepper="peppA", exp=exp) is True


def test_verify_rejects_wrong_pepper(monkeypatch):
    _setup_secret(monkeypatch)
    exp = int(time.time()) + 3600
    token = build_token(image_id="abc-123", expires_at_epoch=exp, pepper="peppA")
    decoded = decode_token_unverified(token)
    # Different pepper (e.g. after a rotation) MUST fail verification.
    assert verify_token(payload=decoded["payload"], sig=decoded["sig"], pepper="peppB", exp=exp) is False


def test_verify_rejects_tampered_signature(monkeypatch):
    _setup_secret(monkeypatch)
    exp = int(time.time()) + 3600
    token = build_token(image_id="abc-123", expires_at_epoch=exp, pepper="peppA")
    decoded = decode_token_unverified(token)
    bad_sig = decoded["sig"][:-2] + "00"
    assert verify_token(payload=decoded["payload"], sig=bad_sig, pepper="peppA", exp=exp) is False


def test_verify_rejects_expired(monkeypatch):
    _setup_secret(monkeypatch)
    exp = int(time.time()) - 1
    token = build_token(image_id="abc-123", expires_at_epoch=exp, pepper="peppA")
    decoded = decode_token_unverified(token)
    assert verify_token(payload=decoded["payload"], sig=decoded["sig"], pepper="peppA", exp=exp) is False


def test_verify_rejects_wrong_global_secret(monkeypatch):
    monkeypatch.setattr("app.services.presigned_url.settings.PRESIGNED_URL_SECRET", "secret-A")
    exp = int(time.time()) + 3600
    token = build_token(image_id="abc-123", expires_at_epoch=exp, pepper="peppA")
    decoded = decode_token_unverified(token)
    monkeypatch.setattr("app.services.presigned_url.settings.PRESIGNED_URL_SECRET", "secret-B")
    assert verify_token(payload=decoded["payload"], sig=decoded["sig"], pepper="peppA", exp=exp) is False


def test_decode_rejects_malformed():
    assert decode_token_unverified("not-a-token") is None
    assert decode_token_unverified("a.b.c") is None
    assert decode_token_unverified("") is None
```

- [ ] **Step 2:** Run: `cd backend && ./venv/bin/pytest tests/test_presigned_url.py -v`
Expected: import error.

- [ ] **Step 3: Implement** — create `backend/app/services/presigned_url.py`:

```python
"""Stateless HMAC-signed presigned URLs for images.

URL form:  {INSTANCE_URL}/i/{payload}.{sig}
  payload  = base64url("{image_id}|{exp_epoch}")
  sig      = hex( hmac_sha256(PRESIGNED_URL_SECRET, payload + url_pepper) )

The url_pepper is per-image, server-side only, never in the URL. Rotating
an image's url_pepper invalidates every token for that image without
affecting any other image. No DB writes by this module — verification
needs the caller to look up the image's current pepper from the DB.
"""
import base64
import hmac
import hashlib
import time
from typing import Optional

from app.core.config import settings


def _sign(payload_b64: str, pepper: str) -> str:
    secret = settings.PRESIGNED_URL_SECRET.encode("utf-8")
    msg = (payload_b64 + "|" + pepper).encode("utf-8")
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def build_token(*, image_id: str, expires_at_epoch: int, pepper: str) -> str:
    """Return the {payload}.{sig} token portion of the URL."""
    raw = f"{image_id}|{expires_at_epoch}".encode("utf-8")
    payload = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return f"{payload}.{_sign(payload, pepper)}"


def decode_token_unverified(token: str) -> Optional[dict]:
    """Decode a token's payload without verifying the signature.

    Returns {image_id, exp, payload, sig} or None for malformed tokens.
    The caller MUST then pass payload+sig+looked-up-pepper to verify_token.
    """
    if not token or "." not in token:
        return None
    parts = token.split(".")
    if len(parts) != 2:
        return None
    payload, sig = parts
    try:
        padded = payload + "=" * (-len(payload) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        image_id, exp_str = raw.split("|", 1)
        exp = int(exp_str)
    except (ValueError, UnicodeDecodeError):
        return None
    return {"image_id": image_id, "exp": exp, "payload": payload, "sig": sig}


def verify_token(*, payload: str, sig: str, pepper: str, exp: int) -> bool:
    """Constant-time HMAC verify with the per-image pepper, plus expiry check."""
    if exp <= int(time.time()):
        return False
    expected = _sign(payload, pepper)
    return hmac.compare_digest(expected, sig)
```

- [ ] **Step 4:** Run tests, confirm 6 passed.

- [ ] **Step 5:** Commit: `git add backend/app/services/presigned_url.py backend/tests/test_presigned_url.py && git commit -m "feat(backend): HMAC-signed presigned URLs with per-image pepper"`

---

## Task 10 — Mint endpoint + `GET /i/{token}` serve endpoint (TDD)

**Files:**
- Modify: `backend/app/api/v1/endpoints/images.py` (mint endpoint)
- Create: `backend/app/api/endpoints/presigned.py` (serve endpoint at root, no API prefix)
- Modify: `backend/app/main.py` (register new router)
- Append to: `backend/tests/test_pin_endpoints.py`

Note: the serve route lives at the root, not under `/api/v1`, because the URL is meant to be terse and shareable. Hence a separate router file outside the versioned API.

- [ ] **Step 1: Failing tests** — append to `backend/tests/test_pin_endpoints.py`:

```python
import os


@pytest.mark.asyncio
async def test_mint_url_returns_absolute_with_request_host_and_bumps_pin(
    client: AsyncClient, seeded_image, monkeypatch,
):
    monkeypatch.setattr("app.services.presigned_url.settings.PRESIGNED_URL_SECRET", "test-secret")
    r = await client.post(
        f"/api/v1/images/{seeded_image['id']}/presigned-url",
        json={"ttl_days": 30},
        headers={"x-forwarded-host": "imagetools.example.com", "x-forwarded-proto": "https"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["url"].startswith("https://imagetools.example.com/i/")
    pin = datetime.fromisoformat(body["pin_expires_at"].replace("Z", "+00:00"))
    assert timedelta(days=29, hours=23) < pin - datetime.now(timezone.utc) < timedelta(days=30, hours=1)


@pytest.mark.asyncio
async def test_mint_url_404_for_unknown(client: AsyncClient):
    r = await client.post("/api/v1/images/missing/presigned-url", json={"ttl_days": 7})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_i_serves_bytes(client: AsyncClient, seeded_image, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.presigned_url.settings.PRESIGNED_URL_SECRET", "test-secret")
    real = tmp_path / "x.png"
    real.write_bytes(b"\x89PNG\r\n\x1a\nFAKE")
    import sqlalchemy
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as s:
        await s.execute(
            sqlalchemy.text("UPDATE images SET current_path = :p WHERE id = :i"),
            {"p": str(real), "i": seeded_image["id"]},
        )
        await s.commit()
    mint = await client.post(
        f"/api/v1/images/{seeded_image['id']}/presigned-url",
        json={"ttl_days": 30},
    )
    url = mint.json()["url"]
    # Strip the host part — AsyncClient is bound to base_url=http://test
    path = url.split("://", 1)[1].split("/", 1)[1]
    r = await client.get(f"/{path}")
    assert r.status_code == 200
    assert r.content.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_get_i_404_for_invalid_token(client: AsyncClient):
    r = await client.get("/i/not-a-real-token")
    assert r.status_code == 404
```

- [ ] **Step 2: Add the mint endpoint** — in `backend/app/api/v1/endpoints/images.py`. Add `PresignedUrlRequest, PresignedUrlResponse` to the schemas import; add `from fastapi import Request` to the FastAPI imports if missing; add `from app.core.url_utils import get_instance_url` and `from app.services.presigned_url import build_token` to the imports. Then append:

```python
@router.post("/{image_id}/presigned-url", response_model=PresignedUrlResponse)
async def create_presigned_url_endpoint(
    image_id: str,
    payload: PresignedUrlRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Mint a long-lived HMAC-signed URL for embedding in agent-generated documents.

    HMAC includes the image's url_pepper, so revoke_presigned_urls (rotates the
    pepper) invalidates this URL. Side effect: bumps pin_expires_at to >= URL
    expiry so the link stays alive.
    """
    image = await ImageService.get_image(db, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    ttl_days = payload.ttl_days or settings.PIN_DEFAULT_DURATION_DAYS
    try:
        await ImageService.pin_image(db, image.id, duration_days=ttl_days)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    refreshed = await ImageService.get_image(db, image.id)

    import time as _time
    exp = int(_time.time()) + ttl_days * 86400
    token = build_token(
        image_id=image.id, expires_at_epoch=exp, pepper=refreshed.url_pepper,
    )
    base = get_instance_url(request).rstrip("/")
    return PresignedUrlResponse(
        url=f"{base}/i/{token}",
        token=token,
        expires_at=datetime.fromtimestamp(exp, tz=timezone.utc),
        image_id=image.id,
        pin_expires_at=refreshed.pin_expires_at,
    )
```

(Add `from datetime import datetime, timezone` to the file imports if missing.)

- [ ] **Step 3: Create the serve router** — `backend/app/api/endpoints/presigned.py`. Order matters: decode payload (untrusted), look up image to fetch its current pepper, then verify with that pepper. A rotated pepper makes the verify fail → 404.

```python
"""GET /i/{token} — serve image bytes for an HMAC-signed presigned URL."""
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.presigned_url import decode_token_unverified, verify_token
from app.services.image_service import ImageService

router = APIRouter(prefix="/i", tags=["presigned"])


@router.get("/{token}")
async def serve_presigned(token: str, db: AsyncSession = Depends(get_db)):
    decoded = decode_token_unverified(token)
    if decoded is None:
        raise HTTPException(status_code=404, detail="Invalid or expired URL")
    image = await ImageService.get_image(db, decoded["image_id"])
    if image is None or not image.current_path or not os.path.exists(image.current_path):
        raise HTTPException(status_code=404, detail="Image not found")
    if not verify_token(
        payload=decoded["payload"], sig=decoded["sig"],
        pepper=image.url_pepper, exp=decoded["exp"],
    ):
        # Either expired, signature mismatch, or pepper rotated since mint.
        raise HTTPException(status_code=404, detail="Invalid or expired URL")
    return FileResponse(
        path=image.current_path,
        media_type=f"image/{image.format.lower()}",
        filename=image.original_filename,
    )
```

- [ ] **Step 4: Register the router** — in `backend/app/main.py`, add `presigned` to the endpoints import line and append `app.include_router(presigned.router)` (no prefix — short URLs intentional).

- [ ] **Step 5:** Run: `cd backend && ./venv/bin/pytest tests/test_pin_endpoints.py -v`
Expected: all green.

- [ ] **Step 6:** Commit: `git add backend/app/api/v1/endpoints/images.py backend/app/api/endpoints/presigned.py backend/app/main.py backend/tests/test_pin_endpoints.py && git commit -m "feat(backend): mint + serve HMAC-signed presigned image URLs (pepper-aware)"`

---

## Task 11 — Share-link viewer HTML page (TDD)

`/s/{token}` now returns an HTML page with the image in a frame, tag chips, capture date, and effective expiry. Raw bytes move to `/s/{token}/raw`. **The in-memory `share_service` is unchanged** — `get_shared_image(token)` still returns the existing `ShareEntry` (image_id, image_path, media_type, original_filename, expires_at). The viewer looks up the `Image` ORM row via `ImageService.get_image(db, entry.image_id)` to render fresh tags / captured_at / pin-aware expiry on every page load.

**Files:**
- Modify or create: `backend/app/api/endpoints/share_view.py` (or wherever the existing `/s/{token}` handler lives)
- Create: `backend/tests/test_share_view.py`

- [ ] **Step 1: Locate the current share-serve handler**

Run: `grep -rn '/s/{token}\|@router.get.*"/s/' backend/app/`
Note the file. The existing handler returns raw bytes via `FileResponse`. We replace it with two routes (HTML viewer + `/raw`).

- [ ] **Step 2: Failing tests** — `backend/tests/test_share_view.py`:

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_share_root_returns_html_with_metadata(client: AsyncClient, seeded_image):
    # Create a share link via the existing API
    r = await client.post(
        f"/api/v1/images/{seeded_image['id']}/share",
        headers={"X-User-ID": seeded_image["user_id"]},
    )
    assert r.status_code == 200
    token = r.json()["url"].rsplit("/", 1)[1]

    page = await client.get(f"/s/{token}")
    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    body = page.text
    assert f"/s/{token}/raw" in body                # the <img> source
    assert "Captured:" in body
    assert "Expires:" in body or "Auto-deletes:" in body


@pytest.mark.asyncio
async def test_share_raw_returns_bytes(client: AsyncClient, seeded_image, tmp_path):
    import sqlalchemy
    from app.core.database import AsyncSessionLocal
    real = tmp_path / "x.png"
    real.write_bytes(b"\x89PNG\r\n\x1a\nFAKE")
    async with AsyncSessionLocal() as s:
        await s.execute(
            sqlalchemy.text("UPDATE images SET current_path = :p WHERE id = :i"),
            {"p": str(real), "i": seeded_image["id"]},
        )
        await s.commit()
    r = await client.post(
        f"/api/v1/images/{seeded_image['id']}/share",
        headers={"X-User-ID": seeded_image["user_id"]},
    )
    token = r.json()["url"].rsplit("/", 1)[1]
    raw = await client.get(f"/s/{token}/raw")
    assert raw.status_code == 200
    assert raw.content.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_share_root_404_for_unknown(client: AsyncClient):
    r = await client.get("/s/not-a-real-token")
    assert r.status_code == 404
```

- [ ] **Step 3: Implement the viewer routes**

Create or replace `backend/app/api/endpoints/share_view.py`. `share_service.get_shared_image(token)` is the existing **synchronous, in-memory** lookup; we then load the `Image` from DB to render fresh metadata.

```python
"""HTML viewer + raw bytes for the in-memory 5-minute share links."""
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.services.share_service import get_shared_image
from app.services.image_service import ImageService
from app.services.user_service import ANONYMOUS_USER_ID

router = APIRouter(prefix="/s", tags=["share"])


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;")
         .replace(">", "&gt;").replace('"', "&quot;")
    )


def _render_viewer(*, token: str, image, link_expires_at, eff, is_pinned, tags) -> str:
    tags_html = "".join(
        f'<span class="tag">{_html_escape(t)}</span>' for t in tags
    ) or '<span class="tag empty">no tags</span>'
    captured = image.created_at.strftime("%Y-%m-%d %H:%M UTC")
    if eff is not None:
        expiry_value = eff.strftime("%Y-%m-%d %H:%M UTC")
    else:
        expiry_value = "never (this user is not subject to retention)"
    pin_note = '<span class="pin">📌 Pinned</span>' if is_pinned else ""
    link_expiry = link_expires_at.strftime("%H:%M:%S UTC")
    return f"""<!doctype html>
<html><head>
<meta charset="utf-8" />
<title>{_html_escape(image.original_filename)}</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 0; padding: 2rem;
         background: #1e1e1e; color: #ddd; }}
  .frame {{ max-width: 1100px; margin: 0 auto; background: #2a2a2a;
            padding: 1.5rem; border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4); }}
  h1 {{ margin: 0 0 1rem 0; font-size: 1.2rem; word-break: break-all; }}
  img {{ max-width: 100%; max-height: 75vh; display: block; margin: 0 auto;
         border-radius: 4px; background: #111; }}
  .meta {{ display: grid; grid-template-columns: max-content 1fr; gap: 0.5rem 1rem;
           margin-top: 1.5rem; font-size: 0.95rem; }}
  .meta dt {{ color: #999; }}
  .tag {{ display: inline-block; background: #4a4a8a; color: #eef;
          border-radius: 999px; padding: 2px 10px; font-size: 0.85rem;
          margin: 2px 4px 2px 0; }}
  .tag.empty {{ background: #3a3a3a; color: #777; }}
  .pin {{ background: #856; color: #fee; border-radius: 999px; padding: 2px 10px;
          font-size: 0.85rem; margin-left: 0.5rem; }}
  .footer {{ margin-top: 1.5rem; font-size: 0.8rem; color: #888; }}
</style>
</head><body>
<div class="frame">
  <h1>{_html_escape(image.original_filename)} {pin_note}</h1>
  <img src="/s/{_html_escape(token)}/raw" alt="{_html_escape(image.original_filename)}" />
  <dl class="meta">
    <dt>Tags:</dt><dd>{tags_html}</dd>
    <dt>Captured:</dt><dd>{captured}</dd>
    <dt>Auto-deletes:</dt><dd>{expiry_value}</dd>
  </dl>
  <div class="footer">This share link expires at {link_expiry}.</div>
</div>
</body></html>"""


@router.get("/{token}", response_class=HTMLResponse)
async def view_share(token: str, db: AsyncSession = Depends(get_db)):
    entry = get_shared_image(token)  # in-memory, synchronous
    if entry is None:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    image = await ImageService.get_image(db, entry.image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    eff = (
        ImageService.effective_expires_at(
            created_at=image.created_at,
            pin_expires_at=image.pin_expires_at,
            retention_days=settings.ANONYMOUS_IMAGE_RETENTION_DAYS,
        )
        if image.user_id == ANONYMOUS_USER_ID else None
    )
    is_pinned = image.pin_expires_at is not None and image.pin_expires_at > datetime.now(timezone.utc)
    return HTMLResponse(_render_viewer(
        token=token, image=image, link_expires_at=entry.expires_at,
        eff=eff, is_pinned=is_pinned, tags=ImageService.get_tags(image),
    ))


@router.get("/{token}/raw")
async def serve_share_raw(token: str, db: AsyncSession = Depends(get_db)):
    entry = get_shared_image(token)  # in-memory, synchronous
    if entry is None:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    image = await ImageService.get_image(db, entry.image_id)
    if image is None or not image.current_path or not os.path.exists(image.current_path):
        raise HTTPException(status_code=404, detail="Image file missing")
    return FileResponse(
        path=image.current_path,
        media_type=f"image/{image.format.lower()}",
        filename=image.original_filename,
    )
```

- [ ] **Step 4: Register the router** in `backend/app/main.py` (add `share_view` to the endpoints import, then `app.include_router(share_view.router)` outside the API prefix). **Remove any pre-existing `/s/{token}` registration** from wherever it lived previously.

- [ ] **Step 5:** Run: `cd backend && ./venv/bin/pytest tests/test_share_view.py -v`
Expected: 3 passed.

- [ ] **Step 6:** Commit: `git add backend/app/api/endpoints/share_view.py backend/app/main.py backend/tests/test_share_view.py && git commit -m "feat(backend): share-link viewer page with tags + capture date + pin-aware expiry"`

---

## Task 12 — Rate limiting on public image routes (TDD)

Add per-IP rate limiting via `slowapi` to the three public-facing image routes: `/i/{token}` (presigned), `/s/{token}` (share viewer HTML), `/s/{token}/raw` (share bytes).

**Files:**
- Create: `backend/app/core/rate_limit.py`
- Modify: `backend/app/main.py` (register handler + middleware)
- Modify: `backend/app/api/endpoints/presigned.py`, `backend/app/api/endpoints/share_view.py` (decorate routes)
- Create: `backend/tests/test_rate_limit.py`

- [ ] **Step 1: Failing test** — `backend/tests/test_rate_limit.py`. Setting the limit to a small value via monkeypatch makes the test fast.

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_share_route_rate_limited(monkeypatch, client: AsyncClient, seeded_image):
    # Tighten the limit just for this test.
    monkeypatch.setattr("app.core.config.settings.RATE_LIMIT_IMAGE_ACCESS", "3/minute")
    # Force the limiter to re-read the setting.
    from app.core.rate_limit import reset_for_tests
    reset_for_tests()

    r = await client.post(
        f"/api/v1/images/{seeded_image['id']}/share",
        headers={"X-User-ID": seeded_image["user_id"]},
    )
    token = r.json()["url"].rsplit("/", 1)[1]

    statuses = []
    for _ in range(5):
        statuses.append((await client.get(f"/s/{token}")).status_code)

    # First 3 should pass (200), the 4th and 5th should be 429.
    assert statuses[:3] == [200, 200, 200]
    assert 429 in statuses[3:]


@pytest.mark.asyncio
async def test_presigned_route_rate_limited(monkeypatch, client: AsyncClient, seeded_image, tmp_path):
    monkeypatch.setattr("app.core.config.settings.RATE_LIMIT_IMAGE_ACCESS", "3/minute")
    monkeypatch.setattr("app.services.presigned_url.settings.PRESIGNED_URL_SECRET", "test-secret")
    from app.core.rate_limit import reset_for_tests
    reset_for_tests()

    # Need a real file so /i/ would otherwise serve 200.
    import sqlalchemy
    from app.core.database import AsyncSessionLocal
    real = tmp_path / "x.png"; real.write_bytes(b"\x89PNG\r\n\x1a\nFAKE")
    async with AsyncSessionLocal() as s:
        await s.execute(
            sqlalchemy.text("UPDATE images SET current_path = :p WHERE id = :i"),
            {"p": str(real), "i": seeded_image["id"]},
        )
        await s.commit()
    mint = await client.post(
        f"/api/v1/images/{seeded_image['id']}/presigned-url", json={"ttl_days": 30}
    )
    url = mint.json()["url"]
    path = url.split("://", 1)[1].split("/", 1)[1]
    statuses = []
    for _ in range(5):
        statuses.append((await client.get(f"/{path}")).status_code)
    assert statuses[:3] == [200, 200, 200]
    assert 429 in statuses[3:]
```

- [ ] **Step 2: Implement the limiter module** — `backend/app/core/rate_limit.py`:

```python
"""Per-IP rate limiter shared across the public-facing image routes."""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

_limiter: Limiter | None = None


def get_limiter() -> Limiter:
    global _limiter
    if _limiter is None:
        _limiter = Limiter(key_func=get_remote_address)
    return _limiter


def image_access_limit() -> str:
    """Return the configured rate-limit string (read each call so test overrides apply)."""
    return settings.RATE_LIMIT_IMAGE_ACCESS


def reset_for_tests() -> None:
    """Reset the limiter's internal state (for tests that change the limit string)."""
    global _limiter
    _limiter = None
```

- [ ] **Step 3: Wire the limiter into the app** — in `backend/app/main.py`:

```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.rate_limit import get_limiter

app.state.limiter = get_limiter()
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
```

- [ ] **Step 4: Decorate the three routes**

In `backend/app/api/endpoints/presigned.py`, change `serve_presigned`:

```python
from fastapi import Request
from app.core.rate_limit import get_limiter, image_access_limit

@router.get("/{token}")
@get_limiter().limit(image_access_limit)
async def serve_presigned(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    ...  # existing body
```

(Note: `slowapi`'s decorator requires `request: Request` as the first positional arg of the handler; the existing handler doesn't take it — add it.)

In `backend/app/api/endpoints/share_view.py`, do the same for `view_share` and `serve_share_raw`. Each handler gains a `request: Request` first arg and a `@get_limiter().limit(image_access_limit)` decorator.

- [ ] **Step 5:** Run: `cd backend && ./venv/bin/pytest tests/test_rate_limit.py -v`
Expected: 2 passed. (Tests may take a few seconds.)

- [ ] **Step 6: Smoke-check the unrelated routes still work**

Run: `cd backend && ./venv/bin/pytest tests/ -v`
Expected: full suite still green.

- [ ] **Step 7:** Commit: `git add backend/app/core/rate_limit.py backend/app/main.py backend/app/api/endpoints/presigned.py backend/app/api/endpoints/share_view.py backend/tests/test_rate_limit.py && git commit -m "feat(backend): per-IP rate limiting on /i/{token}, /s/{token}, /s/{token}/raw"`

---

## Task 13 — Pepper rotation: revoke all presigned URLs for an image (TDD)

This task wires the rotation mechanism end-to-end on the backend: a service helper that rotates the pepper, a REST endpoint, and a test confirming a previously-valid URL stops working immediately after rotation.

**Files:**
- Modify: `backend/app/services/image_service.py` (append `rotate_url_pepper`)
- Modify: `backend/app/api/v1/endpoints/images.py` (`DELETE /images/{id}/presigned-urls`)
- Append to: `backend/tests/test_pin_endpoints.py`

- [ ] **Step 1: Failing tests** — append to `backend/tests/test_pin_endpoints.py`:

```python
@pytest.mark.asyncio
async def test_rotate_pepper_invalidates_existing_url(
    client: AsyncClient, seeded_image, tmp_path, monkeypatch,
):
    monkeypatch.setattr("app.services.presigned_url.settings.PRESIGNED_URL_SECRET", "test-secret")
    real = tmp_path / "x.png"; real.write_bytes(b"\x89PNG\r\n\x1a\nFAKE")
    import sqlalchemy
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as s:
        await s.execute(
            sqlalchemy.text("UPDATE images SET current_path = :p WHERE id = :i"),
            {"p": str(real), "i": seeded_image["id"]},
        )
        await s.commit()
    # Mint a URL — confirm it works.
    mint = await client.post(
        f"/api/v1/images/{seeded_image['id']}/presigned-url", json={"ttl_days": 30},
    )
    url = mint.json()["url"]
    path = url.split("://", 1)[1].split("/", 1)[1]
    assert (await client.get(f"/{path}")).status_code == 200
    # Revoke. The previously-minted URL must now 404.
    rev = await client.delete(f"/api/v1/images/{seeded_image['id']}/presigned-urls")
    assert rev.status_code == 200
    assert (await client.get(f"/{path}")).status_code == 404
    # And a freshly-minted URL must work again.
    mint2 = await client.post(
        f"/api/v1/images/{seeded_image['id']}/presigned-url", json={"ttl_days": 30},
    )
    path2 = mint2.json()["url"].split("://", 1)[1].split("/", 1)[1]
    assert (await client.get(f"/{path2}")).status_code == 200


@pytest.mark.asyncio
async def test_rotate_pepper_404_for_unknown(client: AsyncClient):
    r = await client.delete("/api/v1/images/missing/presigned-urls")
    assert r.status_code == 404
```

- [ ] **Step 2: Add the `rotate_url_pepper` service helper** — append to `class ImageService:` in `backend/app/services/image_service.py` (and add `import secrets` at the top of the file if missing):

```python
    @staticmethod
    async def rotate_url_pepper(db, image_id: str):
        """Rotate this image's url_pepper. Invalidates every presigned URL for the image."""
        image = await ImageService.get_image(db, image_id)
        if image is None:
            return None
        image.url_pepper = secrets.token_hex(16)
        await db.commit()
        await db.refresh(image)
        return image
```

- [ ] **Step 3: Add the REST endpoint** — append to `backend/app/api/v1/endpoints/images.py`:

```python
@router.delete("/{image_id}/presigned-urls", status_code=200)
async def revoke_presigned_urls_endpoint(
    image_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Revoke ALL outstanding presigned URLs for this image by rotating its pepper.

    Used when a draft document is finalized, when a screenshot is replaced, or
    whenever an embedded URL must stop resolving without changing the image
    bytes themselves.
    """
    image = await ImageService.rotate_url_pepper(db, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return {"image_id": image.id, "revoked": True}
```

- [ ] **Step 4:** Run: `cd backend && ./venv/bin/pytest tests/test_pin_endpoints.py -v`
Expected: all green (the two new tests included).

- [ ] **Step 5:** Commit: `git add backend/app/services/image_service.py backend/app/api/v1/endpoints/images.py backend/tests/test_pin_endpoints.py && git commit -m "feat(backend): revoke presigned URLs by rotating per-image pepper"`

---

## Task 14 — MCP `BackendClient` Protocol + impls

**Files:**
- Modify: `mcp-server/src/mcp_server/backend.py`
- Modify: `mcp-server/src/mcp_server/backend_http.py`
- Modify: `mcp-server/src/mcp_server/backend_local.py`

- [ ] **Step 1: Extend the dataclasses + Protocol** in `backend.py`. Add to `ImageMeta`:

```python
    pin_expires_at: str | None = None       # ISO-8601, or None
    effective_expires_at: str | None = None
```

Add the new dataclass:

```python
@dataclass(frozen=True)
class PresignedUrl:
    url: str
    token: str
    expires_at: str
    image_id: str
    pin_expires_at: str
```

Extend `BackendClient` Protocol:

```python
    async def pin_image(
        self, user_id: str, image_id: str, duration_days: int | None
    ) -> ImageMeta | None: ...

    async def unpin_image(self, user_id: str, image_id: str) -> ImageMeta | None: ...

    async def create_presigned_url(
        self, user_id: str, image_id: str, ttl_days: int | None
    ) -> PresignedUrl | None: ...

    async def revoke_presigned_urls(
        self, user_id: str, image_id: str
    ) -> bool: ...
```

- [ ] **Step 2: Implement on `HttpBackendClient`** (`backend_http.py`). Find or factor a small `_meta_from_image_response(d)` helper that consumes the existing fields, plus `pin_expires_at` and `effective_expires_at`. Then append:

```python
    async def pin_image(self, user_id, image_id, duration_days):
        body = {"duration_days": duration_days} if duration_days is not None else {}
        r = await self._client.put(
            f"/api/v1/images/{image_id}/pin",
            json=body, headers=self._auth_headers(user_id),
        )
        if r.status_code == 404: return None
        r.raise_for_status()
        return _meta_from_image_response(r.json())

    async def unpin_image(self, user_id, image_id):
        r = await self._client.delete(
            f"/api/v1/images/{image_id}/pin",
            headers=self._auth_headers(user_id),
        )
        if r.status_code == 404: return None
        r.raise_for_status()
        return _meta_from_image_response(r.json())

    async def create_presigned_url(self, user_id, image_id, ttl_days):
        body = {"ttl_days": ttl_days} if ttl_days is not None else {}
        r = await self._client.post(
            f"/api/v1/images/{image_id}/presigned-url",
            json=body, headers=self._auth_headers(user_id),
        )
        if r.status_code == 404: return None
        r.raise_for_status()
        d = r.json()
        return PresignedUrl(
            url=d["url"], token=d["token"], expires_at=d["expires_at"],
            image_id=d["image_id"], pin_expires_at=d["pin_expires_at"],
        )

    async def revoke_presigned_urls(self, user_id, image_id):
        r = await self._client.delete(
            f"/api/v1/images/{image_id}/presigned-urls",
            headers=self._auth_headers(user_id),
        )
        if r.status_code == 404: return False
        r.raise_for_status()
        return True
```

If `_meta_from_image_response` and `_auth_headers` don't already exist as helpers, factor them out from the existing `list_user_images` / `get_image` code and reuse here.

- [ ] **Step 3: Implement on `LocalBackendClient`** in `backend_local.py`, calling `ImageService.pin_image`, `ImageService.unpin_image`, `ImageService.rotate_url_pepper`, and the same code path the mint endpoint uses for the URL (build_token + pin_image, reading the image's url_pepper). Convert datetimes to ISO strings.

- [ ] **Step 4: Smoke** — `cd mcp-server && python -m pytest tests/ -v`
Expected: existing tests still green.

- [ ] **Step 5:** Commit: `git add mcp-server/src/mcp_server/backend.py mcp-server/src/mcp_server/backend_http.py mcp-server/src/mcp_server/backend_local.py && git commit -m "feat(mcp): BackendClient gains pin/unpin/presigned-url/revoke"`

---

## Task 15 — MCP tool functions (TDD)

**Files:**
- Create: `mcp-server/tests/test_tools_pin.py`
- Modify: `mcp-server/src/mcp_server/tools.py`

- [ ] **Step 1: Failing tests**

```python
import pytest
from unittest.mock import AsyncMock
from mcp_server.tools import (
    pin_image, unpin_image, get_presigned_url, download_image, revoke_presigned_urls,
)
from mcp_server.backend import ImageMeta, ImageBytes, PresignedUrl


def _meta(image_id="i1", pin=None):
    return ImageMeta(
        id=image_id, user_id="u1", original_filename="x.png", original_size=1,
        width=1, height=1, format="PNG",
        thumbnail_url="/t", image_url="/i",
        created_at="2026-04-30T00:00:00+00:00", updated_at="2026-04-30T00:00:00+00:00",
        tags=[], pin_expires_at=pin, effective_expires_at=None,
    )


@pytest.mark.asyncio
async def test_pin_default_duration():
    backend = AsyncMock()
    backend.pin_image.return_value = _meta(pin="2026-07-29T00:00:00+00:00")
    out = await pin_image(backend, user_id="u1", image_id="i1")
    backend.pin_image.assert_awaited_once_with("u1", "i1", None)
    assert out["meta"]["pin_expires_at"] == "2026-07-29T00:00:00+00:00"


@pytest.mark.asyncio
async def test_pin_passes_duration():
    backend = AsyncMock()
    backend.pin_image.return_value = _meta(pin="2026-05-30T00:00:00+00:00")
    await pin_image(backend, user_id="u1", image_id="i1", duration_days=30)
    backend.pin_image.assert_awaited_once_with("u1", "i1", 30)


@pytest.mark.asyncio
async def test_pin_raises_lookup_error_when_missing():
    backend = AsyncMock(); backend.pin_image.return_value = None
    with pytest.raises(LookupError):
        await pin_image(backend, user_id="u1", image_id="missing")


@pytest.mark.asyncio
async def test_unpin_calls_backend():
    backend = AsyncMock(); backend.unpin_image.return_value = _meta(pin=None)
    out = await unpin_image(backend, user_id="u1", image_id="i1")
    assert out["meta"]["pin_expires_at"] is None


@pytest.mark.asyncio
async def test_get_presigned_url_returns_full_payload():
    backend = AsyncMock()
    backend.create_presigned_url.return_value = PresignedUrl(
        url="https://imagetools.example/i/abc.def", token="abc.def",
        expires_at="2026-07-29T00:00:00+00:00",
        image_id="i1", pin_expires_at="2026-07-29T00:00:00+00:00",
    )
    out = await get_presigned_url(backend, user_id="u1", image_id="i1", ttl_days=90)
    assert out["url"].startswith("https://imagetools.example/i/")
    assert out["token"] == "abc.def"
    assert out["expires_at"] == "2026-07-29T00:00:00+00:00"
    assert out["pin_expires_at"] == "2026-07-29T00:00:00+00:00"


@pytest.mark.asyncio
async def test_download_image_alias_for_get_image():
    backend = AsyncMock()
    backend.get_image.return_value = ImageBytes(meta=_meta(), data=b"\x89PNG\r\n", mime_type="image/png")
    out = await download_image(backend, user_id="u1", image_id="i1")
    assert out["mime_type"] == "image/png"
    assert out["data"].startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_revoke_calls_backend_and_returns_revoked():
    backend = AsyncMock(); backend.revoke_presigned_urls.return_value = True
    out = await revoke_presigned_urls(backend, user_id="u1", image_id="i1")
    assert out == {"image_id": "i1", "revoked": True}


@pytest.mark.asyncio
async def test_revoke_raises_lookup_error_when_missing():
    backend = AsyncMock(); backend.revoke_presigned_urls.return_value = False
    with pytest.raises(LookupError):
        await revoke_presigned_urls(backend, user_id="u1", image_id="missing")
```

- [ ] **Step 2:** Run, confirm failures.

- [ ] **Step 3: Add tools** to `mcp-server/src/mcp_server/tools.py`:

```python
from .backend import PresignedUrl  # add to existing imports


async def pin_image(
    backend: BackendClient, user_id: str, image_id: str,
    duration_days: int | None = None,
) -> dict[str, Any]:
    """Pin an image to delay auto-cleanup. Re-pinning extends the existing pin (never shortens).

    Use this BEFORE embedding an image URL in a generated document. If you also call
    get_presigned_url, that already bumps the pin — explicit pin_image is only needed
    when you keep an image alive without minting a URL (e.g. you'll call download_image).
    """
    meta = await backend.pin_image(user_id, image_id, duration_days)
    if meta is None:
        raise LookupError(f"image not found: {image_id}")
    return {"meta": _meta_dict(meta)}


async def unpin_image(
    backend: BackendClient, user_id: str, image_id: str,
) -> dict[str, Any]:
    """Unpin an image (return it to the normal retention schedule)."""
    meta = await backend.unpin_image(user_id, image_id)
    if meta is None:
        raise LookupError(f"image not found: {image_id}")
    return {"meta": _meta_dict(meta)}


async def get_presigned_url(
    backend: BackendClient, user_id: str, image_id: str,
    ttl_days: int | None = None,
) -> dict[str, Any]:
    """Mint a long-lived HMAC-signed URL the agent can embed in a generated document.

    Side effect: bumps pin_expires_at to >= URL expiry, so the embedded link stays valid.
    The URL uses the web UI's hostname.
    Returns {url, token, expires_at, image_id, pin_expires_at}.
    """
    out = await backend.create_presigned_url(user_id, image_id, ttl_days)
    if out is None:
        raise LookupError(f"image not found: {image_id}")
    return {
        "url": out.url, "token": out.token,
        "expires_at": out.expires_at, "image_id": out.image_id,
        "pin_expires_at": out.pin_expires_at,
    }


async def download_image(
    backend: BackendClient, user_id: str, image_id: str,
) -> dict[str, Any]:
    """Download an image's bytes + metadata. Alias of `get_image` for prompt clarity."""
    return await get_image(backend, user_id, image_id)


async def revoke_presigned_urls(
    backend: BackendClient, user_id: str, image_id: str,
) -> dict[str, Any]:
    """Revoke ALL outstanding presigned URLs for this image.

    Implementation: rotates the image's url_pepper. Use this when a draft
    document referencing the screenshot is finalized, or when a screenshot is
    replaced and old links must stop resolving.
    """
    ok = await backend.revoke_presigned_urls(user_id, image_id)
    if not ok:
        raise LookupError(f"image not found: {image_id}")
    return {"image_id": image_id, "revoked": True}
```

- [ ] **Step 4:** Run: `cd mcp-server && python -m pytest tests/test_tools_pin.py -v`
Expected: 8 passed.

- [ ] **Step 5:** Commit: `git add mcp-server/src/mcp_server/tools.py mcp-server/tests/test_tools_pin.py && git commit -m "feat(mcp): pin/unpin/get_presigned_url/download_image/revoke_presigned_urls tools"`

---

## Task 16 — Register MCP tools with FastMCP

**Files:** Modify `mcp-server/src/mcp_server/server.py`

- [ ] **Step 1:** Find the existing `@mcp.tool()` registrations (`list_recent_images`, `get_image`, `get_recent_images`). Below them, add five wrappers, mirroring the existing pattern. Adapt `_backend()` / `_user()` to whatever helpers the file already uses to obtain backend + user (do not invent new ones — read the surrounding code).

```python
@mcp.tool()
async def pin_image(image_id: str, duration_days: int | None = None) -> dict:
    """Pin an image to delay its auto-deletion."""
    return await tools.pin_image(_backend(), _user(), image_id, duration_days)


@mcp.tool()
async def unpin_image(image_id: str) -> dict:
    """Unpin an image."""
    return await tools.unpin_image(_backend(), _user(), image_id)


@mcp.tool()
async def get_presigned_url(image_id: str, ttl_days: int | None = None) -> dict:
    """Mint a long-lived URL for embedding in a generated document. Bumps pin."""
    return await tools.get_presigned_url(_backend(), _user(), image_id, ttl_days)


@mcp.tool()
async def download_image(image_id: str) -> dict:
    """Download image bytes + metadata."""
    return await tools.download_image(_backend(), _user(), image_id)


@mcp.tool()
async def revoke_presigned_urls(image_id: str) -> dict:
    """Revoke all outstanding presigned URLs for this image (rotates pepper)."""
    return await tools.revoke_presigned_urls(_backend(), _user(), image_id)
```

- [ ] **Step 2:** Smoke: `cd mcp-server && python -m mcp_server.stdio --help 2>&1 | head -10`
Expected: usage prints; no import errors.

- [ ] **Step 3:** Commit: `git add mcp-server/src/mcp_server/server.py && git commit -m "feat(mcp): register pin/unpin/presigned/download/revoke tools"`

---

## Task 17 — Frontend: pin badge, unpin confirmation, Copy Document Link, Invalidate Document Links, tag refresh

The web UI grows two affordances: a 📌 badge on pinned images with an Unpin-with-confirmation menu item, and a new "Copy Document Link" action in the share dropdown that mints a presigned URL and copies it. There is **no** "Pin" button — only agents pin.

**Files:**
- Modify: `frontend/src/services/api.js`
- Modify: `frontend/src/stores/imageStore.js`
- Modify: `frontend/src/components/ImageCard.vue`

- [ ] **Step 1: API service**

In `frontend/src/services/api.js`, append to `imageService`:

```javascript
  unpinImage: async (imageId) => {
    const response = await api.delete(`/images/${imageId}/pin`);
    return response.data;
  },

  createDocumentLink: async (imageId, ttlDays) => {
    const body = ttlDays != null ? { ttl_days: ttlDays } : {};
    const response = await api.post(`/images/${imageId}/presigned-url`, body);
    return response.data;
  },

  revokeDocumentLinks: async (imageId) => {
    const response = await api.delete(`/images/${imageId}/presigned-urls`);
    return response.data;
  },
```

- [ ] **Step 2: Store actions + tag-refresh-after-delete**

In `frontend/src/stores/imageStore.js`, replace `deleteImage` (lines 153–164) with:

```javascript
    async deleteImage(imageId) {
      try {
        await imageService.deleteImage(imageId);
        this.images = this.images.filter(img => img.id !== imageId);
        this.selectedImages = this.selectedImages.filter(id => id !== imageId);
        // Reload tags — the deleted image may have been the last carrier
        // of one or more tags. /tags excludes orphans server-side.
        await this.loadUserTags();
      } catch (error) {
        this.error = error.message;
        console.error('Failed to delete image:', error);
        throw error;
      }
    },

    async unpinImage(imageId) {
      try {
        const updated = await imageService.unpinImage(imageId);
        const index = this.images.findIndex(img => img.id === imageId);
        if (index !== -1) this.images[index] = updated;
        return updated;
      } catch (error) {
        this.error = error.response?.data?.detail || error.message;
        console.error('Failed to unpin image:', error);
        throw error;
      }
    },
```

- [ ] **Step 3: ImageCard pin badge + tooltip**

In `frontend/src/components/ImageCard.vue`, inside `<div class="image-preview">` under the `<img ... />` line, add:

```html
      <div v-if="isPinned" class="pin-badge" :title="pinTooltip">
        <span class="pin-icon">📌</span>
      </div>
```

In `<script setup>`, near `compressionRatio`:

```javascript
const isPinned = computed(() => {
  if (!props.image.pin_expires_at) return false;
  return new Date(props.image.pin_expires_at) > new Date();
});

const pinTooltip = computed(() => {
  if (!isPinned.value) return '';
  return `Pinned by AI agent until ${new Date(props.image.pin_expires_at).toLocaleString()}`;
});
```

Replace the existing `expirationTooltip` computed (around lines 429–437) with:

```javascript
const expirationTooltip = computed(() => {
  const lines = [];
  if (props.image.created_at) {
    let s = props.image.created_at;
    if (!s.endsWith('Z') && !s.includes('+')) s += 'Z';
    lines.push(`Uploaded: ${new Date(s).toLocaleString()}`);
  }
  if (props.image.effective_expires_at) {
    lines.push(`Auto-deletes: ${new Date(props.image.effective_expires_at).toLocaleString()}`);
  }
  if (isPinned.value) {
    lines.push(`Pinned until: ${new Date(props.image.pin_expires_at).toLocaleString()}`);
  }
  return lines.join('\n') || 'Uploaded: unknown';
});
```

- [ ] **Step 4: Unpin menu item + inline confirm**

Inside the `more-actions-menu` block, at the top of `<div v-if="showMoreActionsMenu" ...>`:

```html
              <button
                v-if="isPinned"
                @click="handleMenuAction(() => showUnpinConfirm = true)"
                class="menu-action"
                :disabled="isProcessing"
              >
                <span class="menu-icon">📌</span>
                <span class="menu-label">Unpin image</span>
              </button>
```

In `<script setup>`:

```javascript
const showUnpinConfirm = ref(false);

const confirmUnpin = async () => {
  isProcessing.value = true;
  processingMessage.value = 'Unpinning...';
  try {
    await imageStore.unpinImage(props.image.id);
    showUnpinConfirm.value = false;
    showToast('Image unpinned', 'success', 2000);
  } catch (e) {
    showToast('Failed to unpin image', 'error', 3000);
  } finally {
    isProcessing.value = false;
    processingMessage.value = '';
  }
};
```

After the existing `delete-confirm` block:

```html
    <!-- Unpin confirmation -->
    <div v-if="showUnpinConfirm" class="card-actions" @click.stop>
      <div class="delete-confirm">
        <span class="delete-message">Unpin {{ image.original_filename }}? It will return to the normal retention schedule.</span>
        <div class="delete-actions">
          <button @click="confirmUnpin" class="btn-confirm btn-danger" :disabled="isProcessing">
            {{ isProcessing ? '⏳' : '✓' }} Unpin
          </button>
          <button @click="showUnpinConfirm = false" class="btn-confirm btn-cancel" :disabled="isProcessing">
            ✕ Cancel
          </button>
        </div>
      </div>
    </div>
```

Change the wrapper on `<div class="icon-buttons">` (line 47) to:

```html
      <div class="icon-buttons" v-if="!showDeleteConfirm && !showUnpinConfirm">
```

- [ ] **Step 5: "Copy Document Link" + "Invalidate Document Links" actions in the share dropdown**

In the share-actions menu (around lines 89–116), add two new items below "Copy Share Link":

```html
              <button
                @click="handleShareAction(handleCopyDocumentLink)"
                class="menu-action"
                :disabled="isProcessing"
              >
                <span class="menu-icon">🔖</span>
                <span class="menu-label">Copy Document Link</span>
              </button>

              <button
                @click="handleShareAction(() => showInvalidateLinksConfirm = true)"
                class="menu-action"
                :disabled="isProcessing"
              >
                <span class="menu-icon">⛔</span>
                <span class="menu-label">Invalidate Document Links</span>
              </button>
```

In `<script setup>`, add:

```javascript
const showInvalidateLinksConfirm = ref(false);

const handleCopyDocumentLink = async () => {
  try {
    const data = await imageService.createDocumentLink(props.image.id);  // default TTL = 90d
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(data.url);
      const days = Math.round((new Date(data.expires_at) - new Date()) / 86400000);
      showToast(`Document link copied! Valid for ~${days} days.`, 'success', 3000);
    } else {
      showToast(`Document URL: ${data.url}`, 'info', 8000);
    }
  } catch (error) {
    console.error('Failed to create document link:', error);
    showToast('Failed to create document link.', 'error', 3000);
  }
};

const confirmInvalidateLinks = async () => {
  isProcessing.value = true;
  processingMessage.value = 'Revoking links...';
  try {
    await imageService.revokeDocumentLinks(props.image.id);
    showInvalidateLinksConfirm.value = false;
    showToast('All document links for this image revoked.', 'success', 3000);
  } catch (e) {
    showToast('Failed to revoke document links.', 'error', 3000);
  } finally {
    isProcessing.value = false;
    processingMessage.value = '';
  }
};
```

After the existing `delete-confirm` and unpin-confirm blocks, add the confirmation block for invalidate:

```html
    <!-- Invalidate Document Links confirmation -->
    <div v-if="showInvalidateLinksConfirm" class="card-actions" @click.stop>
      <div class="delete-confirm">
        <span class="delete-message">Invalidate every existing Document Link for {{ image.original_filename }}? Anyone holding an old link (e.g. embedded in a draft doc) will see a 404.</span>
        <div class="delete-actions">
          <button @click="confirmInvalidateLinks" class="btn-confirm btn-danger" :disabled="isProcessing">
            {{ isProcessing ? '⏳' : '✓' }} Invalidate
          </button>
          <button @click="showInvalidateLinksConfirm = false" class="btn-confirm btn-cancel" :disabled="isProcessing">
            ✕ Cancel
          </button>
        </div>
      </div>
    </div>
```

Update the `icon-buttons` wrapper to also hide while the new confirm is open:

```html
      <div class="icon-buttons" v-if="!showDeleteConfirm && !showUnpinConfirm && !showInvalidateLinksConfirm">
```

(Make sure `imageService` is imported at the top of `<script setup>` — likely already imported via the existing API import line; if not, add `import { imageService } from '../services/api';`.)

- [ ] **Step 6: Pin badge styles**

Append to `<style scoped>`:

```css
.pin-badge {
  position: absolute;
  top: 6px;
  left: 6px;
  background: rgba(255, 235, 59, 0.95);
  color: #5d4037;
  border-radius: 999px;
  padding: 2px 6px;
  font-size: 0.85rem;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.25);
  z-index: 5;
}
.pin-icon { display: inline-block; transform: rotate(-15deg); }
```

- [ ] **Step 7: End-to-end manual check**

Run: `cd /home/philg/src/python/ImageTools && ./dev-all.sh`. In another terminal, simulate the agent flow against a known anonymous image (use a real `IMG_ID`):

```bash
# Pin via the REST endpoint that the MCP server proxies to
curl -X PUT "http://localhost:8081/api/v1/images/IMG_ID/pin" -H 'content-type: application/json' -d '{"duration_days": 30}'
# Mint a presigned URL
curl -X POST "http://localhost:8081/api/v1/images/IMG_ID/presigned-url" -H 'content-type: application/json' -d '{"ttl_days": 30}'
# Open the returned URL in a browser — image should display
```

In Brave at `http://localhost:5173`:
1. After pin, the image card shows a 📌 badge top-left. Tooltip on size/dim row includes `Auto-deletes:` and `Pinned until:` lines.
2. Click ⋯ → "Unpin image" → ✓ Unpin. Badge disappears.
3. Click the share dropdown (⬇) → "Copy Document Link". Toast confirms; paste into a new tab — image renders directly. Keep this tab open.
4. Click the share dropdown (⬇) → "Invalidate Document Links" → ✓ Invalidate. Reload the tab from step 3 — it must now 404. (Confirms the per-image pepper rotation took effect.)
5. Click the share dropdown (⬇) → "Copy Document Link" again → paste in a new tab. The new link must work (proves the rotation is per-image-revocation, not a one-way break).
6. Click "Copy Share Link" (existing) → paste in a new tab — share viewer page renders with the image in a frame, tag chips, capture date, and expiry. (Test before unpinning — viewer should also show "📌 Pinned" if applicable.)
7. Delete an image whose tag is unique (no other image has it). Confirm the tag's chip disappears from the top-bar tag filter without a manual refresh.

Stop dev with Ctrl-C.

- [ ] **Step 8:** Commit: `git add frontend/src/services/api.js frontend/src/stores/imageStore.js frontend/src/components/ImageCard.vue && git commit -m "feat(frontend): pin badge, unpin confirm, Copy/Invalidate Document Links, tag refresh after delete"`

---

## Task 18 — Bump version

**Files:** Modify `version.json`

- [ ] **Step 1:** Run: `cd /home/philg/src/python/ImageTools && ./bump-version.js minor`

- [ ] **Step 2:** Commit: `git add version.json && git commit -m "chore: bump version for MCP image-pinning + presigned URLs + share viewer"`

---

## Self-Review Checklist (run before declaring complete)

- **Spec coverage:**
  - MCP `pin_image` with extend-not-shorten semantic → Task 4 + Task 14 + Task 16.
  - MCP `unpin_image` → Task 4 + Task 14 + Task 16.
  - MCP `get_presigned_url` returning HMAC-signed URL with the web UI hostname → Task 9 (HMAC helpers, pepper-aware) + Task 10 (mint endpoint, uses `get_instance_url(request)`) + Task 14 + Task 16.
  - MCP `download_image` → Task 15 + Task 16.
  - MCP `revoke_presigned_urls` (per-image revocation via pepper rotation) → Task 13 (REST + service) + Task 14 + Task 15 + Task 16.
  - Pin extends auto-cleanup → Task 5.
  - URL uses HMAC for obscured filename/link → Task 9.
  - URL revocation per-image without rotating the global secret → Task 1 (`url_pepper` column) + Task 2 (migration + backfill) + Task 9 (pepper folded into HMAC) + Task 10 (mint reads pepper, serve verifies with pepper) + Task 13 (rotate endpoint).
  - Hostname of the web UI used as the URL base → Task 10 Step 2 (uses `get_instance_url(request)`).
  - Share-link viewer renders image in a frame with tags + capture date + pin-aware expiry → Task 11. Existing in-memory `share_service` is unchanged (per Decision Point #10).
  - Rate limiting on `/i/{token}`, `/s/{token}`, `/s/{token}/raw` → Task 12.
  - Web UI shows pin badge → Task 17 Step 3.
  - Web UI offers Unpin with confirmation → Task 17 Step 4.
  - "Copy Document Link" + "Invalidate Document Links" actions in image card → Task 17 Step 5.
  - Tags only display for images with tags → Task 17 Step 2 (refresh after delete).
- **No placeholders.** Every code block is complete; no "TODO", "TBD", "fill in".
- **Type / name consistency:** `pin_expires_at`, `url_pepper`, `effective_expires_at`, `pin_image`, `unpin_image`, `get_presigned_url`, `download_image`, `revoke_presigned_urls`, `rotate_url_pepper`, `PinRequest`, `PresignedUrlRequest`, `PresignedUrlResponse`, `build_token`, `decode_token_unverified`, `verify_token`, `PRESIGNED_URL_SECRET`, `RATE_LIMIT_IMAGE_ACCESS`, `get_shared_image` (sync, in-memory), `createDocumentLink`, `revokeDocumentLinks`, `unpinImage`, `isPinned`, `showUnpinConfirm`, `confirmUnpin`, `showInvalidateLinksConfirm`, `confirmInvalidateLinks`, `pinTooltip` — spelled identically across tasks.
- **MCP-only pinning:** the frontend never calls `PUT /pin`. Only the MCP server (and any test/curl call) does. Confirmed by absence of a `pinImage` action in Task 17 Step 2.
- **Pepper never appears in URL or API responses.** Confirmed: only used inside the HMAC computation; not part of `ImageResponse`; not echoed by `/api/v1/images/{id}/presigned-url`.
