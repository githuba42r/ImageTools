# Session → User Identity Refactor

**Commit:** `e700051`
**Branch:** `master`
**Status:** Complete — all files updated, build verified, committed.

---

## Overview

The browser-scoped, expiring **Session** concept has been replaced throughout the entire stack with a persistent **User** identity.

Previously, each browser tab or window received its own short-lived session UUID stored in `localStorage`. Sessions expired, images were capped per session, and two browsers logged in as the same user would see different images.

After this refactor, a **User** record is stable and persistent:

- **Authenticated users** (Authelia / nginx basic-auth): UUID generated on first login, retrieved by username on every subsequent request. All browsers sharing the same authenticated username see the same images, mobile pairings, and addon authorizations.
- **Anonymous users** (no auth proxy): A single well-known fixed UUID (`00000000-0000-0000-0000-000000000000`) is shared globally by all unauthenticated browsers. This record is created at startup and never deleted.

---

## Design Decisions

| Concern | Old behaviour | New behaviour |
|---|---|---|
| Identity scope | Per browser tab (UUID in localStorage) | Per authenticated username / global anonymous |
| Expiry | Sessions expired after N days | Users never expire |
| Image limit | `MAX_IMAGES_PER_SESSION` | No limit |
| Anonymous cleanup | Expired session images deleted | Anonymous images deleted by age (`ANONYMOUS_IMAGE_RETENTION_DAYS`, default 30 days) |
| DB table | `sessions` | `users` |
| FK column name | `session_id` | `user_id` |
| HTTP header | `X-Session-ID` | `X-User-ID` |
| REST endpoint | `POST /api/v1/sessions` | `POST /api/v1/users` |
| Frontend localStorage key | `imagetools_session_id` | `imagetools_user_id` |
| Frontend store | `sessionStore` / `useSessionStore` | `userStore` / `useUserStore` |
| Frontend env override | `VITE_SESSION_OVERRIDE` | `VITE_USER_OVERRIDE` |

### Config changes

| Key | Change |
|---|---|
| `SESSION_EXPIRY_DAYS` | **Removed** |
| `MAX_IMAGES_PER_SESSION` | **Removed** |
| `ANONYMOUS_IMAGE_RETENTION_DAYS` | **Added** (default: `30`) |
| `SESSION_SECRET_KEY` | **Kept** — used for Fernet encryption of OpenRouter API keys, unrelated to user sessions |

---

## Files Changed

### Backend — deleted

| File | Reason |
|---|---|
| `backend/app/api/v1/endpoints/sessions.py` | Replaced by `users.py` |
| `backend/app/services/session_service.py` | Replaced by `user_service.py` |

### Backend — created

| File | Purpose |
|---|---|
| `backend/app/api/v1/endpoints/users.py` | `POST /users` (get-or-create), `GET /users/{id}`, `GET /users/{id}/validate` |
| `backend/app/services/user_service.py` | `UserService`: `get_or_create_user()`, `get_user()`, `validate_user()`, `cleanup_anonymous_old_images()` |

### Backend — modified

| File | Key change |
|---|---|
| `backend/app/models/models.py` | `Session` model → `User` model; all `session_id` FK columns → `user_id` |
| `backend/app/schemas/schemas.py` | `SessionCreate` / `SessionResponse` → `UserCreate` / `UserResponse`; all schemas updated |
| `backend/app/core/config.py` | Removed `SESSION_EXPIRY_DAYS` / `MAX_IMAGES_PER_SESSION`; added `ANONYMOUS_IMAGE_RETENTION_DAYS` |
| `backend/app/core/migrate.py` | Full rewrite: renames `sessions` → `users` table and all child-table `session_id` → `user_id` FK columns on first startup |
| `backend/app/core/scheduler.py` | `cleanup_expired_sessions_task` → `cleanup_old_anonymous_images_task` |
| `backend/app/core/websocket_manager.py` | Internal dict renamed `websocket_sessions` → `websocket_users`; `connect()`/`disconnect()` use `user_id`; `broadcast_to_session()` method name retained (all callers pass `user_id=`) |
| `backend/app/main.py` | Imports `UserService` / `users` router; removes `SessionService` / `sessions` router; WebSocket endpoint param `session_id` → `user_id`; lifespan bootstraps anonymous user |
| `backend/app/api/v1/endpoints/images.py` | Upload and list endpoints use `user_id`; list route is `GET /images/user/{user_id}` |
| `backend/app/api/v1/endpoints/mobile.py` | All `session_id` params and `broadcast_to_session()` calls use `user_id` |
| `backend/app/api/v1/endpoints/addon.py` | All `session_id` params and `broadcast_to_session()` calls use `user_id` |
| `backend/app/api/v1/endpoints/chat.py` | `session_id` → `user_id` |
| `backend/app/api/v1/endpoints/compression.py` | `session_id` → `user_id` |
| `backend/app/api/v1/endpoints/profiles.py` | `session_id` → `user_id` |
| `backend/app/api/v1/endpoints/settings.py` | `session_id` → `user_id` |
| `backend/app/api/v1/endpoints/openrouter_oauth.py` | `session_id` → `user_id` |
| `backend/app/services/image_service.py` | `session_id` → `user_id` |
| `backend/app/services/mobile_service.py` | `session_id` → `user_id` |
| `backend/app/services/addon_service.py` | `session_id` → `user_id` |
| `backend/app/services/ai_chat_service.py` | `session_id` → `user_id` |
| `backend/app/services/cost_tracker.py` | `session_id` → `user_id` |
| `backend/app/services/settings_service.py` | `session_id` → `user_id` |
| `backend/app/services/profile_service.py` | `session_id` → `user_id` |
| `backend/app/services/compression_service.py` | `session_id` → `user_id` |
| `backend/app/services/openrouter_oauth_service.py` | `session_id` → `user_id` |

### Frontend — deleted

| File | Reason |
|---|---|
| `frontend/src/stores/sessionStore.js` | Replaced by `userStore.js` |

### Frontend — created

| File | Purpose |
|---|---|
| `frontend/src/stores/userStore.js` | Pinia store: `userId`, `userData`, `initializeUser()`, `getOrCreateUser()`, `clearUser()`; localStorage key `imagetools_user_id`; env var `VITE_USER_OVERRIDE` |

### Frontend — modified

| File | Key change |
|---|---|
| `frontend/src/App.vue` | All session refs → user refs; `initializeSession()` → `initializeUser()`; `loadSessionImages()` → `loadUserImages()`; `setSessionId()` → `setUserId()`; `appConfig` keys updated; QR code payload `session_id` → `user_id`; `ImageCard` prop `sessionId` → `userId`; `UploadArea` `maxImages` prop removed |
| `frontend/src/stores/imageStore.js` | `useSessionStore` → `useUserStore`; `loadSessionImages` → `loadUserImages` |
| `frontend/src/services/api.js` | localStorage key `imagetools_user_id`; header `X-User-ID`; `sessionService` → `userService`; `POST /users`; `getUserImages()` at `/images/user/${userId}` |
| `frontend/src/services/websocketService.js` | WebSocket URL param `session_id=` → `user_id=` |
| `frontend/src/services/chatService.js` | `setSessionId` → `setUserId`; `getSessionConversations` → `getUserConversations` |
| `frontend/src/services/openRouterService.js` | `setSessionId` → `setUserId`; `X-Session-ID` → `X-User-ID` |
| `frontend/src/services/mobileService.js` | Request bodies `session_id` → `user_id`; URLs updated |
| `frontend/src/services/addonService.js` | Request bodies `session_id` → `user_id`; URLs updated |
| `frontend/src/components/ImageCard.vue` | `sessionId` prop → `userId`; `expiryDays` prop removed; expiration tooltip replaced with upload-date tooltip |
| `frontend/src/components/ChatInterface.vue` | `sessionId` prop → `userId` |
| `frontend/src/components/UploadArea.vue` | Removed "Max N images per session" UI text (limit no longer exists) |

---

## Database Migration

`backend/app/core/migrate.py` runs automatically on startup and handles the transition from any older schema:

1. Renames the `sessions` table to `users`
2. Drops the `expires_at` column (no longer relevant)
3. Adds `username` and `display_name` columns to `users`
4. For each child table (`images`, `mobile_app_pairings`, `addon_authorizations`, `conversations`, `user_settings`, `openrouter_keys`): renames `session_id` → `user_id` and updates the FK reference to point at `users`
5. Creates the anonymous user record (`00000000-0000-0000-0000-000000000000`) if it does not exist

Migration is idempotent — safe to run on a fresh DB or an already-migrated one.

---

## Important Notes for Future Developers

1. **`SESSION_SECRET_KEY` must not be removed.** Despite the name, it is used as the Fernet symmetric encryption key for storing OpenRouter API keys at rest. It has nothing to do with user sessions.

2. **`broadcast_to_session()` in `websocket_manager.py` was not renamed.** It is an internal implementation detail. All callers pass `user_id=` as the keyword argument — the method name is cosmetic.

3. **`migrate.py` intentionally contains `"session_id"` as SQL string literals.** These are the *old* column names being migrated *from* — they are correct and must not be changed.

4. **`sessionStorage` references in `App.vue`** (PKCE OAuth flow) use the browser-native `window.sessionStorage` API, not the application's old session concept. They were correctly left unchanged.

5. **`ChatInterface.vue` uses `chat_session_` as a localStorage key prefix** for per-image chat UI state persistence. This is internal to the chat component and unrelated to the old user session concept.

6. **LSP type warnings** in Python files (e.g., `Column[str] not assignable to str`) are pre-existing SQLAlchemy type annotation noise. They are not real bugs and can be ignored.

---

## Testing Checklist

After deployment, verify:

- [ ] Anonymous user: browser loads, gets UUID `00000000-0000-0000-0000-000000000000`, images persist across page reloads
- [ ] Authenticated user (Authelia): two different browsers logged in as the same user see the same images
- [ ] Image upload works and images appear under `/images/user/${userId}`
- [ ] WebSocket connects with `?user_id=` param; mobile upload triggers real-time image refresh
- [ ] Mobile pairing QR code contains `user_id` field; Android app pairs successfully
- [ ] Browser addon registration and screenshot upload work
- [ ] OpenRouter OAuth flow completes (PKCE; uses `SESSION_SECRET_KEY` for key encryption)
- [ ] Anonymous image cleanup scheduler runs (check logs at 2 AM or trigger manually)
- [ ] `GET /api/v1/users/{id}/validate` returns `{"valid": true}` for a known user
