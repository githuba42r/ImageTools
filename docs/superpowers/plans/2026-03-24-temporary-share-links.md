# Temporary Share Links Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add temporary, unauthenticated image share URLs so users can copy a short-lived link for AI agents or external tools to access an image.

**Architecture:** In-memory token store with APScheduler cleanup. New `/s/{token}` top-level route bypasses all auth. Frontend adds a "Copy Link" button to each image card that creates a share link and copies it to the clipboard.

**Tech Stack:** FastAPI, Python `secrets` module, APScheduler, Vue 3, Axios

**Spec:** `docs/superpowers/specs/2026-03-24-temporary-share-links-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/core/config.py` | Modify | Add `SHARE_LINK_EXPIRY_SECONDS` setting |
| `backend/app/services/share_service.py` | Create | In-memory token store, create/get/cleanup |
| `backend/app/api/v1/endpoints/sharing.py` | Create | POST endpoint for creating share links |
| `backend/app/main.py` | Modify | Import sharing router, add `GET /s/{token}` route, register cleanup job |
| `backend/app/middleware/internal_auth.py` | Modify | Add `/s/` to bypass prefixes |
| `backend/app/core/scheduler.py` | Modify | Add share link cleanup job |
| `frontend/src/services/api.js` | Modify | Add `shareService` |
| `frontend/src/components/ImageCard.vue` | Modify | Add Copy Link button and handler |
| `deployment/nginx/nginx.conf` | Modify | Add unauthenticated `/s/` location block |
| `docs/NGINX_AUTHELIA_DEPLOYMENT.md` | Modify | Document `/s/` auth bypass |

---

### Task 1: Create Feature Branch

**Files:** None (git only)

- [ ] **Step 1: Create and switch to feature branch**

```bash
git checkout -b feature/temporary-share-links
```

- [ ] **Step 2: Verify branch**

```bash
git branch --show-current
```

Expected: `feature/temporary-share-links`

---

### Task 2: Add Configuration Setting

**Files:**
- Modify: `backend/app/core/config.py:24` (after `ANONYMOUS_IMAGE_RETENTION_DAYS`)

- [ ] **Step 1: Add SHARE_LINK_EXPIRY_SECONDS to Settings class**

In `backend/app/core/config.py`, add after line 24 (`ANONYMOUS_IMAGE_RETENTION_DAYS: int = 30`):

```python
    SHARE_LINK_EXPIRY_SECONDS: int = 300  # TTL for temporary share links (default 5 minutes)
```

- [ ] **Step 2: Verify the setting loads**

```bash
cd /home/philg/src/python/ImageTools/backend && python -c "from app.core.config import settings; print(settings.SHARE_LINK_EXPIRY_SECONDS)"
```

Expected: `300`

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/config.py
git commit -m "feat: add SHARE_LINK_EXPIRY_SECONDS config setting"
```

---

### Task 3: Create Share Service

**Files:**
- Create: `backend/app/services/share_service.py`

- [ ] **Step 1: Create the share service**

Create `backend/app/services/share_service.py`:

```python
"""In-memory temporary share link service.

Manages short-lived tokens that map to image files. Tokens are stored in
a Python dict and expire after SHARE_LINK_EXPIRY_SECONDS. A periodic
cleanup task purges expired entries. All state is intentionally lost on
restart — these are ephemeral links.
"""

import secrets
import string
import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Base62 alphabet for URL-safe tokens
_ALPHABET = string.ascii_letters + string.digits
_TOKEN_LENGTH = 16


@dataclass
class ShareEntry:
    image_id: str
    image_path: str
    media_type: str
    original_filename: str
    expires_at: datetime


# Module-level store — single process, intentionally ephemeral
_store: dict[str, ShareEntry] = {}


def create_share_link(image_id: str, image_path: str, media_type: str, original_filename: str) -> dict:
    """Create a temporary share token for an image.

    Returns dict with 'url' (relative path) and 'expires_in' (seconds).
    """
    token = "".join(secrets.choice(_ALPHABET) for _ in range(_TOKEN_LENGTH))
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.SHARE_LINK_EXPIRY_SECONDS)

    _store[token] = ShareEntry(
        image_id=image_id,
        image_path=image_path,
        media_type=media_type,
        original_filename=original_filename,
        expires_at=expires_at,
    )

    logger.info(f"Share link created for image {image_id}, token={token[:4]}..., expires={expires_at.isoformat()}")
    return {
        "url": f"/s/{token}",
        "expires_in": settings.SHARE_LINK_EXPIRY_SECONDS,
    }


def get_shared_image(token: str) -> Optional[ShareEntry]:
    """Look up a share token. Returns the entry if valid, None if expired or missing."""
    entry = _store.get(token)
    if entry is None:
        return None

    if datetime.now(timezone.utc) >= entry.expires_at:
        # Expired — remove eagerly
        del _store[token]
        return None

    return entry


def cleanup_expired() -> int:
    """Remove all expired entries. Returns count of removed entries."""
    now = datetime.now(timezone.utc)
    expired_tokens = [t for t, e in _store.items() if now >= e.expires_at]
    for token in expired_tokens:
        del _store[token]

    if expired_tokens:
        logger.info(f"Cleaned up {len(expired_tokens)} expired share link(s)")
    return len(expired_tokens)
```

- [ ] **Step 2: Verify module imports**

```bash
cd /home/philg/src/python/ImageTools/backend && python -c "from app.services.share_service import create_share_link, get_shared_image, cleanup_expired; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/share_service.py
git commit -m "feat: add in-memory share link service"
```

---

### Task 4: Create Sharing API Endpoint

**Files:**
- Create: `backend/app/api/v1/endpoints/sharing.py`
- Modify: `backend/app/main.py:24` (import line) and `backend/app/main.py:114` (router registration)

- [ ] **Step 1: Create the sharing endpoint**

Create `backend/app/api/v1/endpoints/sharing.py`:

```python
"""API endpoints for creating temporary image share links."""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.services.image_service import ImageService
from app.services.share_service import create_share_link

router = APIRouter(prefix="/images", tags=["sharing"])


@router.post("/{image_id}/share")
async def create_share(
    image_id: str,
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db),
):
    """Create a temporary, unauthenticated share link for an image.

    The link expires after SHARE_LINK_EXPIRY_SECONDS (default 300s / 5 min).
    """
    image = await ImageService.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Verify the requesting user owns the image
    if image.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="Not your image")

    media_type = f"image/{image.format.lower()}"
    result = create_share_link(
        image_id=image.id,
        image_path=image.current_path,
        media_type=media_type,
        original_filename=image.original_filename,
    )

    return result
```

- [ ] **Step 2: Register the sharing router in main.py**

In `backend/app/main.py`, add `sharing` to the import on line 24:

```python
from app.api.v1.endpoints import users, images, compression, history, background, chat, openrouter_oauth, settings as settings_router, mobile, addon, profiles, sharing
```

Then add after line 114 (`app.include_router(addon.router, ...)`):

```python
app.include_router(sharing.router, prefix=settings.API_PREFIX)
```

- [ ] **Step 3: Add the GET /s/{token} route in main.py**

First, add `HTTPException` to the FastAPI import on line 1 of `backend/app/main.py`:

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
```

Then add this route after the `/version` endpoint (after line 139) and before the WebSocket endpoint:

```python
@app.get("/s/{token}")
async def serve_shared_image(token: str):
    """Serve a temporarily shared image. No authentication required."""
    from app.services.share_service import get_shared_image

    entry = get_shared_image(token)
    if entry is None:
        raise HTTPException(status_code=404, detail="Not found")

    return FileResponse(
        entry.image_path,
        media_type=entry.media_type,
        filename=entry.original_filename,
    )
```

- [ ] **Step 4: Verify the app starts**

```bash
cd /home/philg/src/python/ImageTools/backend && python -c "from app.main import app; print('Routes:', [r.path for r in app.routes if hasattr(r, 'path') and '/s/' in r.path])"
```

Expected: `Routes: ['/s/{token}']`

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/endpoints/sharing.py backend/app/main.py
git commit -m "feat: add share link creation endpoint and /s/{token} route"
```

---

### Task 5: Add Auth Bypass for /s/ Path

**Files:**
- Modify: `backend/app/middleware/internal_auth.py:54-57` (BYPASS_PREFIXES list)

- [ ] **Step 1: Add /s/ to internal auth bypass prefixes**

In `backend/app/middleware/internal_auth.py`, add to the `BYPASS_PREFIXES` list (after line 56):

```python
        "/s/",              # Temporary share links (intentionally unauthenticated)
```

The list should now be:

```python
    BYPASS_PREFIXES = [
        "/api/v1/mobile/",  # Mobile API uses long-term secrets
        "/api/v1/addon/",   # Addon API uses OAuth tokens
        "/s/",              # Temporary share links (intentionally unauthenticated)
    ]
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/middleware/internal_auth.py
git commit -m "feat: add /s/ to internal auth bypass for share links"
```

---

### Task 6: Register Cleanup Job in Scheduler

**Files:**
- Modify: `backend/app/core/scheduler.py`

- [ ] **Step 1: Add share link cleanup job**

In `backend/app/core/scheduler.py`, add this import at the top (after line 10):

```python
from app.services.share_service import cleanup_expired as cleanup_expired_share_links
```

Then add this task function after the `cleanup_old_anonymous_images_task` function (after line 32):

```python
async def cleanup_expired_share_links_task():
    """Scheduled task to clean up expired share links."""
    try:
        cleanup_expired_share_links()
    except Exception as e:
        logger.error(f"Error during share link cleanup: {e}", exc_info=True)
```

Then in the `start_scheduler()` function, add the job after the existing cleanup job is added (after line 73, before `scheduler.start()`):

```python
        # Add share link cleanup job (every 60 seconds)
        scheduler.add_job(
            cleanup_expired_share_links_task,
            trigger='interval',
            seconds=60,
            id='cleanup_expired_share_links',
            name='Cleanup Expired Share Links',
            replace_existing=True
        )
```

- [ ] **Step 2: Verify scheduler imports**

```bash
cd /home/philg/src/python/ImageTools/backend && python -c "from app.core.scheduler import start_scheduler; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/scheduler.py
git commit -m "feat: add periodic cleanup job for expired share links"
```

---

### Task 7: Add Frontend Share Service

**Files:**
- Modify: `frontend/src/services/api.js` (add after `historyService` at line 223)

- [ ] **Step 1: Add shareService to api.js**

In `frontend/src/services/api.js`, add after the `historyService` block (after line 223):

```javascript

// Share Link API
export const shareService = {
  async createShareLink(imageId) {
    const response = await api.post(`/images/${imageId}/share`);
    return response.data;
  },
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/services/api.js
git commit -m "feat: add shareService to frontend API client"
```

---

### Task 8: Add Copy Link Button to ImageCard

**Files:**
- Modify: `frontend/src/components/ImageCard.vue`
  - Template: after line 90 (after Copy to Clipboard button)
  - Script: after line 636 (after `handleCopyToClipboard`)
  - Import: add `shareService` to imports

- [ ] **Step 1: Add shareService import**

In `frontend/src/components/ImageCard.vue`, find the existing import from the api service. Search for the line importing from `'../services/api'` or `'@/services/api'` and add `shareService` to it.

If there's no direct import of api services (the component may use the store), add at the top of the `<script setup>` block:

```javascript
import { shareService } from '../services/api';
```

- [ ] **Step 2: Add the Copy Link button to the template**

In the template, add after the Copy to Clipboard button (after line 90, before the AI Chat button):

```html
          <!-- Copy Share Link Button -->
          <button
            @click="handleCopyShareLink"
            class="btn-icon"
            :disabled="isProcessing"
            :title="'Copy link'"
          >
            <span class="icon">🔗</span>
            <span class="tooltip">Copy Link</span>
          </button>
```

- [ ] **Step 3: Add the handleCopyShareLink function**

In the `<script setup>` section, add after `handleCopyToClipboard` (after line 636):

```javascript
const handleCopyShareLink = async () => {
  try {
    const data = await shareService.createShareLink(props.image.id);
    const fullUrl = `${window.location.origin}${data.url}`;

    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(fullUrl);
      const minutes = Math.round(data.expires_in / 60);
      showToast(`Link copied! Expires in ${minutes} minute${minutes !== 1 ? 's' : ''}.`, 'success', 3000);
    } else {
      // Fallback: show URL in toast for manual copy
      showToast(`Share URL: ${fullUrl}`, 'info', 8000);
    }
  } catch (error) {
    console.error('Failed to create share link:', error);
    showToast('Failed to create share link.', 'error', 3000);
  }
};
```

- [ ] **Step 4: Build the frontend to verify**

```bash
cd /home/philg/src/python/ImageTools/frontend && npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ImageCard.vue
git commit -m "feat: add Copy Link button to image cards"
```

---

### Task 9: Update Nginx Config for Auth Bypass

**Files:**
- Modify: `deployment/nginx/nginx.conf` (add after the `/health` location block, line 45)

- [ ] **Step 1: Add /s/ location block**

In `deployment/nginx/nginx.conf`, add after the `/health` location block (after line 45):

```nginx

    # Temporary share links (bypass auth for external access)
    location /s/ {
        auth_basic off;
        proxy_pass http://imagetools:8081;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
```

- [ ] **Step 2: Commit**

```bash
git add deployment/nginx/nginx.conf
git commit -m "feat: add nginx auth bypass for /s/ share link paths"
```

---

### Task 10: Update Deployment Documentation

**Files:**
- Modify: `docs/NGINX_AUTHELIA_DEPLOYMENT.md`

- [ ] **Step 1: Add share links section to deployment docs**

In `docs/NGINX_AUTHELIA_DEPLOYMENT.md`, find the "Security Considerations" section and add before it (or at the end of the document if no such section):

```markdown
## Temporary Share Links

ImageTools supports temporary, unauthenticated image share links at `/s/{token}`. These allow users to share an image URL with AI agents or external tools without requiring authentication.

### Security Model

- **Short-lived:** Links expire after a configurable period (default 5 minutes, controlled by `SHARE_LINK_EXPIRY_SECONDS`)
- **High entropy:** 16-character base62 tokens (~95 bits of entropy) — infeasible to guess
- **In-memory only:** Links are lost on server restart
- **No enumeration:** No endpoint lists active links

### Nginx Configuration

The `/s/` path is configured to bypass `auth_basic` in `nginx.conf`:

```nginx
location /s/ {
    auth_basic off;
    proxy_pass http://imagetools:8081;
    ...
}
```

### Authelia Configuration

If using Authelia, add `/s/` to the access control bypass rules in your Authelia configuration:

```yaml
access_control:
  rules:
    - domain: yourdomain.com
      policy: bypass
      resources:
        - "^/s/.*$"
        - "^/health$"
```

This ensures Authelia does not intercept requests to temporary share URLs.
```

- [ ] **Step 2: Commit**

```bash
git add docs/NGINX_AUTHELIA_DEPLOYMENT.md
git commit -m "docs: document /s/ auth bypass for temporary share links"
```

---

### Task 11: Integration Verification

**Files:** None (verification only)

- [ ] **Step 1: Build frontend**

```bash
cd /home/philg/src/python/ImageTools/frontend && npm run build
```

Expected: Build succeeds.

- [ ] **Step 2: Verify backend starts**

```bash
cd /home/philg/src/python/ImageTools/backend && timeout 5 python -m uvicorn app.main:app --host 127.0.0.1 --port 18081 2>&1 || true
```

Expected: Starts without import errors. Will timeout after 5s which is fine.

- [ ] **Step 3: Verify all new routes are registered**

```bash
cd /home/philg/src/python/ImageTools/backend && python -c "
from app.main import app
share_routes = [r.path for r in app.routes if hasattr(r, 'path') and ('share' in r.path or '/s/' in r.path)]
print('Share routes:', share_routes)
assert '/s/{token}' in share_routes, 'Missing /s/{token} route'
print('All share routes registered.')
"
```

Expected: Shows `/s/{token}` and the share creation route.

- [ ] **Step 4: Verify share service works end-to-end in Python**

```bash
cd /home/philg/src/python/ImageTools/backend && python -c "
from app.services.share_service import create_share_link, get_shared_image, cleanup_expired

# Create a link
result = create_share_link('test-id', '/tmp/test.jpg', 'image/jpeg', 'test.jpg')
token = result['url'].split('/')[-1]
print(f'Created: {result}')

# Retrieve it
entry = get_shared_image(token)
assert entry is not None, 'Should find the entry'
assert entry.image_id == 'test-id'
print(f'Retrieved: image_id={entry.image_id}')

# Bad token returns None
assert get_shared_image('nonexistent') is None
print('Bad token returns None: OK')

# Cleanup with nothing expired
removed = cleanup_expired()
print(f'Cleanup removed: {removed} (should be 0)')

print('All checks passed.')
"
```

Expected: `All checks passed.`
