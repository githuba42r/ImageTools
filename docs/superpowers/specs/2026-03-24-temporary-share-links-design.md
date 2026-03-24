# Temporary Share Links for Images

**Date:** 2026-03-24
**Status:** Approved
**Purpose:** Allow users to generate short-lived, unauthenticated URLs for images so they can be shared with AI agents or other tools for analysis.

## Problem

Images behind Authelia/nginx authentication cannot be accessed by external tools (AI agents, etc.) without credentials. Users need a way to share a direct URL to an image that bypasses authentication and expires quickly.

## Design

### Token Format

- 16-character base62 string (a-z, A-Z, 0-9)
- ~95 bits of entropy — infeasible to guess within the 5-minute window
- URL pattern: `/s/{token}` (e.g., `/s/aB3xK9mP2wQ7nFhT`)

### Storage: In-Memory Dict

Tokens are stored in a Python dictionary keyed by token string. Each entry holds:

- `image_id` — reference to the image
- `image_path` — filesystem path to the current (processed) version
- `media_type` — MIME type (e.g., `image/jpeg`)
- `expires_at` — UTC datetime of expiration

Rationale: Links are intentionally ephemeral (default 5 minutes). Losing them on server restart is acceptable and desirable. No database migration needed. O(1) lookup.

### Cleanup

APScheduler (already in use) runs a periodic job every 60 seconds to purge expired entries from the dict.

### Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `SHARE_LINK_EXPIRY_SECONDS` | `300` | TTL for share links in seconds |

Added to `core/config.py` settings.

## Backend

### New Service: `services/share_service.py`

- `create_share_link(image_id: str) -> dict` — generates token, stores entry, returns `{"url": "/s/{token}", "expires_in": seconds}`
- `get_shared_image(token: str) -> ShareEntry | None` — returns entry if valid and not expired, else `None`
- `cleanup_expired()` — called by scheduler, removes expired entries

### New Endpoint: `api/v1/endpoints/sharing.py`

- `POST /api/v1/images/{image_id}/share` — requires `X-User-ID` header (standard auth). Validates image exists and belongs to user. Returns share URL and expiry.

### New Top-Level Route in `main.py`

- `GET /s/{token}` — serves the image file via `FileResponse`. Returns 404 if token is invalid or expired. Registered before the SPA catch-all route.

## Frontend

### ImageCard.vue Changes

New button added to the action bar between "Copy" (clipboard) and "AI Chat":

- **Icon:** 🔗 (link icon)
- **Tooltip:** "Copy Link"
- **Behavior:**
  1. Calls `POST /api/v1/images/{image_id}/share`
  2. Builds full URL: `${window.location.origin}${response.url}`
  3. Copies to clipboard via `navigator.clipboard.writeText()`
  4. Shows toast: "Link copied! Expires in 5 minutes."

### API Service Addition

New method in `services/api.js`:

- `shareService.createShareLink(imageId)` — POST to `/api/v1/images/{imageId}/share`

## Authentication Bypass

The `/s/` path must bypass authentication at every layer that enforces it:

### Nginx (`deployment/nginx/nginx.conf`)

Add a `location /s/` block that proxies to the backend **without** `auth_basic` or `auth_request` directives.

### Authelia (if configured)

Add `/s/` to the access control policy bypass rules so Authelia does not intercept these requests.

### Internal Auth Middleware (`middleware/internal_auth.py`)

Add `/s/` to the bypass prefixes list so the defense-in-depth layer does not reject unauthenticated requests to share URLs.

### Documentation Updates

Update `docs/NGINX_AUTHELIA_DEPLOYMENT.md` to document that `/s/` paths are intentionally unauthenticated for temporary image sharing, and explain the security model (short TTL + high-entropy tokens).

## Security Considerations

- **Guessability:** 16-char base62 = ~95 bits of entropy. Brute-forcing within a 5-minute window is infeasible.
- **Expiration:** Links automatically expire. In-memory storage means they also vanish on restart.
- **No enumeration:** No endpoint lists active share links. Tokens are not sequential.
- **Scope:** Only the processed (current) version of the image is served. No access to originals, thumbnails, metadata, or other user data.
- **Rate limiting:** Not implemented. Each link creation requires authentication, limiting abuse to authenticated users.

## Files Changed

| File | Change |
|------|--------|
| `backend/app/core/config.py` | Add `SHARE_LINK_EXPIRY_SECONDS` setting |
| `backend/app/services/share_service.py` | New — in-memory token store and management |
| `backend/app/api/v1/endpoints/sharing.py` | New — POST endpoint for creating share links |
| `backend/app/main.py` | Add `GET /s/{token}` route, register sharing router, register scheduler job |
| `backend/app/middleware/internal_auth.py` | Add `/s/` to bypass list |
| `backend/app/core/scheduler.py` | Add cleanup job for expired share links |
| `frontend/src/components/ImageCard.vue` | Add Copy Link button and handler |
| `frontend/src/services/api.js` | Add `shareService.createShareLink()` |
| `deployment/nginx/nginx.conf` | Add unauthenticated `/s/` location block |
| `docs/NGINX_AUTHELIA_DEPLOYMENT.md` | Document `/s/` auth bypass |
