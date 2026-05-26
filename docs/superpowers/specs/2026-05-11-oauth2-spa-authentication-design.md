# OAuth2 SPA Authentication for ImageTools — Design

**Date:** 2026-05-11
**Branch:** `feature/oauth2-authentication` (proposed)
**Status:** Proposed

## Goal

Add optional vinCreative OAuth2 authentication to the ImageTools SPA + FastAPI
backend so that ImageTools deployments can sit behind the vinCreative identity
provider instead of (or as an alternative to) the current Authelia /
anonymous-fallback model. The integration must:

- Activate purely from environment configuration, with no schema migration or
  hard-coded provider details.
- Proxy the entire OAuth2 dance through the backend so the client secret and
  the IdP's JWT never reach the browser.
- Reuse the existing per-user image isolation: each authenticated user gets
  their own image space, keyed off a stable username derived from the JWT.
- Leave device-side flows (mobile pairing, browser addon, MCP token, presigned
  `/i/` URLs, ephemeral `/s/` shares) completely untouched.

## Scope

### In scope (this iteration)

- Authorization-code flow proxied through the backend (no PKCE for parity with
  `@aspedia/oauth2authentication`, which the vinCreative IdP is designed to
  pair with).
- RS256 JWT verification against the IdP's `/auth/get-key` public key with an
  in-process cache.
- A short-lived signed session cookie that carries the resolved username and
  display name; the JWT is verified once at callback and then discarded.
- A minimal Vue 3 login screen surfaced when the SPA gets a 401 with a login
  URL header.
- Coexistence with the existing `InternalAuthMiddleware` defense-in-depth path
  (`X-Internal-Auth`).

### Out of scope (explicit future work)

- **PKCE.** The reference library and production consumers (EC Payments,
  Tappr) don't use it. Adding PKCE would be a non-breaking follow-up if the
  IdP gains support.
- **Refresh tokens.** The JWT is single-shot; when the session cookie expires
  the user re-runs the flow. Adding silent refresh requires the IdP to issue
  refresh tokens to a confidential client and a new server-side store.
- **Multiple providers / provider linking.** Single configured IdP per
  deployment.
- **Permission-based gating.** All authenticated users are admitted; per-user
  data isolation already covers the "user X can't see user Y's images" case
  via the existing user model.
- **Multi-tenant `siteid` validation.** ImageTools is a single-tenant app per
  deployment; `siteid` is parsed but not enforced.
- **Server-side session revocation.** No `oauth_sessions` table; revocation
  would require one. Cookies are tamper-evident via signing, lifetime is
  bounded by the JWT's own `expires` claim.

## Activation

OAuth2 mode is implicitly active when **all three** of the following env vars
are set:

- `OAUTH2_AUTH_HOST`
- `OAUTH2_CLIENT_ID`
- `OAUTH2_CLIENT_SECRET`

Missing any required var → OAuth2 mode is off. ImageTools behaves exactly as
it does today (Authelia headers populate `request.state.remote_user`, with an
anonymous fallback). There is no `OAUTH2_ENABLED` boolean.

`OAUTH2_SCOPE` is optional and defaults to `auth` (matching EC Payments).

## Architecture

### Endpoints (backend, all under `/api/v1/oauth2/`)

| Endpoint | Purpose |
|---|---|
| `GET /oauth2/connect` | SPA navigates here to start the flow. Backend generates a random `state`, persists it (along with the SPA's intended return path) in a short-lived signed cookie, and 302s the browser to `{OAUTH2_AUTH_HOST}/oauth2/authorize?client_id=…&scope=…&state=…&redirect_uri=…/oauth2/callback`. |
| `GET /oauth2/callback?code=…&state=…` | IdP redirects here. Backend validates `state` against the cookie, POSTs `{OAUTH2_AUTH_HOST}/oauth2/jwttoken` with `code`, `client_id`, and `client_secret`, RS256-verifies the returned JWT, extracts `email` + `name.fullname` + `expires`, mints a signed session cookie with those fields, clears the state cookie, and 302s the browser to the return path (default `/`). The JWT is never persisted. |
| `POST /oauth2/logout` | Clears the session cookie. Idempotent. |
| `GET /oauth2/me` | Returns `{username, display_name, expires_at}` from the session cookie. The SPA uses this to render "Logged in as …". |

### Identity flow at request time

The crucial property is that `OAuth2SessionMiddleware` and the existing
`InternalAuthMiddleware` are **parallel populators of the same `request.state`
fields**, not stacked layers. Downstream code (`user_service`, route handlers)
reads `request.state.remote_user` / `remote_name` and is unaware of which
middleware put them there.

```
OAuth2 mode ON:   cookie ─► OAuth2SessionMiddleware ─► request.state.remote_user/remote_name ─► user_service
OAuth2 mode OFF:  header ─► InternalAuthMiddleware  ─► request.state.remote_user/remote_name ─► user_service
                                                                                  ▲
                                                                       same downstream shape
```

`InternalAuthMiddleware` continues to validate the `X-Internal-Auth`
defense-in-depth header in both modes. When OAuth2 mode is on, its
Authelia-header-extraction step is skipped — `request.state.remote_user` will
already be set by `OAuth2SessionMiddleware`, and Authelia isn't in front of
the backend anyway.

### Full login data flow

1. SPA loads `/`. `userStore.initializeUser()` calls `POST /api/v1/users` → backend sees no session cookie → returns `401` with `WWW-Authenticate: OAuth2 login_url="/api/v1/oauth2/connect"`.
2. SPA's axios interceptor detects the 401 + header → sets `userStore.needsLogin = true` → `App.vue` swaps to `LoginView`.
3. User clicks "Sign in". SPA navigates: `window.location.href = "/api/v1/oauth2/connect"`.
4. Backend `/oauth2/connect` generates `state`, sets `imagetools_oauth_state` cookie (signed, 5-minute TTL, path-scoped to `/api/v1/oauth2/`), 302s to `{OAUTH2_AUTH_HOST}/oauth2/authorize?...&state=...&redirect_uri=https://{backend}/api/v1/oauth2/callback`.
5. User authenticates at vinCreative. IdP 302s browser back to `/api/v1/oauth2/callback?code=...&state=...`.
6. Backend `/oauth2/callback`:
   1. Validates `state` against the cookie. Mismatch → 400, clear cookie.
   2. POSTs `{OAUTH2_AUTH_HOST}/oauth2/jwttoken` with `code`, `client_id`, `client_secret`.
   3. Fetches IdP public key (cached, 1-hour TTL) and `jwt.decode(..., algorithms=["RS256"])`. On `InvalidSignature`, force-refreshes the key and retries once.
   4. Parses `expires` (RFC-2822) and asserts not-yet-expired.
   5. Extracts `email` (required) and `name.fullname` (optional, falls back to `email`).
   6. Mints `imagetools_session` cookie with `{u: email, d: display_name, exp: jwt_expires_epoch}`, signed, `HttpOnly`, `SameSite=Lax`, `Secure` when behind HTTPS, `Max-Age` set to `(expires - now)`.
   7. Clears state cookie.
   8. 302 to the return path (default `/`).
7. SPA reloads `/`. Session cookie is sent. `OAuth2SessionMiddleware` validates it, sets `request.state.remote_user = email`, `request.state.remote_name = display_name`. `POST /api/v1/users` succeeds, returning the user record. SPA renders normally.

## Backend components

### New files

| File | Responsibility |
|---|---|
| `backend/app/middleware/oauth2_session.py` | `OAuth2SessionMiddleware`. Validates session cookie, populates `request.state.remote_user` / `remote_name`. Honors the same bypass list as `InternalAuthMiddleware` (`/i/`, `/s/`, `/api/v1/mobile/*`, `/api/v1/addon/*`, `/api/v1/mcp-tokens/*`, `/mcp`, `/health`, `/version`). On a protected path with no valid cookie, returns 401 with `WWW-Authenticate: OAuth2 login_url="/api/v1/oauth2/connect"`. |
| `backend/app/api/v1/endpoints/oauth2.py` | The `/connect`, `/callback`, `/logout`, `/me` route handlers. Thin orchestration only. |
| `backend/app/services/oauth2_service.py` | `exchange_code(code) -> jwt_str`, `fetch_public_key(force_refresh=False) -> str` (in-process dict cache, TTL = `OAUTH2_PUBLIC_KEY_CACHE_SECONDS`), `verify_jwt(jwt_str) -> JwtClaims` (RS256, exp check, single retry on `InvalidSignature` with key refresh). All HTTP-out uses `httpx.AsyncClient`. |
| `backend/app/services/session_service.py` | Wraps `itsdangerous.URLSafeTimedSerializer` with the project's `SESSION_SECRET_KEY`. Sign/verify the session cookie payload and the state cookie payload. Pure functions; no I/O. |

### Modified files

| File | Change |
|---|---|
| `backend/app/core/config.py` | Add: `OAUTH2_AUTH_HOST`, `OAUTH2_CLIENT_ID`, `OAUTH2_CLIENT_SECRET`, `OAUTH2_SCOPE` (default `"auth"`), `OAUTH2_PUBLIC_KEY_CACHE_SECONDS` (default 3600), `OAUTH2_STATE_TTL_SECONDS` (default 300). Add computed `@property oauth2_enabled` that returns `bool(OAUTH2_AUTH_HOST and OAUTH2_CLIENT_ID and OAUTH2_CLIENT_SECRET)`. Reuse the existing `SESSION_SECRET_KEY` (currently unused) as the signing key for state + session cookies. |
| `backend/app/main.py` | If `settings.oauth2_enabled`, register `OAuth2SessionMiddleware` **before** `InternalAuthMiddleware` and mount the OAuth2 router under `/api/v1/oauth2`. Otherwise neither is added. |
| `backend/app/middleware/internal_auth.py` | When `settings.oauth2_enabled` is true, skip the Authelia-header read (lines 92–98 today). The `X-Internal-Auth` defense-in-depth path is unchanged. |
| `backend/app/api/v1/endpoints/users.py` (the `POST /users` bootstrap endpoint) | When `settings.oauth2_enabled` is true and `request.state.remote_user` is absent, return `401` with `WWW-Authenticate: OAuth2 login_url="/api/v1/oauth2/connect"` instead of falling back to anonymous. |
| `backend/requirements.txt` | Add `PyJWT[crypto]>=2.8` (RS256 needs the `cryptography` extra) and `itsdangerous>=2.1`. Both are tiny, well-maintained, no significant transitive footprint beyond `cryptography` (already pulled in by FastAPI's TLS stack in most builds). |

### Cookie specifications

**Session cookie** — `imagetools_session`
- Value: `URLSafeTimedSerializer(SESSION_SECRET_KEY).dumps({"u": email, "d": display_name, "exp": jwt_expires_epoch})`
- Attributes: `HttpOnly`, `Secure` (when `INSTANCE_URL` starts with `https://`), `SameSite=Lax`, `Path=/`, `Max-Age = (jwt_expires - now)`.

**State cookie** — `imagetools_oauth_state`
- Value: `URLSafeTimedSerializer(SESSION_SECRET_KEY).dumps({"s": random_state, "r": return_path})`
- Attributes: `HttpOnly`, `Secure` (conditional), `SameSite=Lax`, `Path=/api/v1/oauth2/`, `Max-Age = OAUTH2_STATE_TTL_SECONDS`.
- Always cleared by the callback after consumption (success or failure).

### JWT verification details

Canonical with EC Payments / Tappr per
`AI-Agent-Config/knowledgebase/.../jwt-payload-format.md`:

1. Fetch public key from `{OAUTH2_AUTH_HOST}/auth/get-key`. PEM, RS256.
2. Cache in-process with TTL `OAUTH2_PUBLIC_KEY_CACHE_SECONDS` (default 3600s).
3. `jwt.decode(token, public_key, algorithms=["RS256"], options={"verify_aud": False})`.
4. On `InvalidSignature`: refetch key with `force_refresh=True`, retry once.
5. Parse `expires` (RFC-2822 string, e.g. `"Fri, 08 May 2026 11:48:44 +1000"`) via `email.utils.parsedate_to_datetime`. Reject if already past.
6. Extract `email` (required — 502 if missing) and `name.fullname` (optional).
7. `siteid` is parsed but not enforced. TODO comment notes the multi-tenant follow-up.
8. `printnode_apikey` and `permissions[]` are ignored. The JWT is treated as a credential — never logged in full, never persisted.

### Middleware ordering in `main.py`

Starlette runs middlewares outermost-first, so the order added is the order
the request hits them:

```python
if settings.oauth2_enabled:
    app.add_middleware(OAuth2SessionMiddleware)
app.add_middleware(InternalAuthMiddleware)    # existing, unchanged registration
app.add_middleware(CORSMiddleware, ...)        # existing
app.add_middleware(SlowAPIMiddleware)          # existing
```

`OAuth2SessionMiddleware` populates `request.state.remote_user` first,
`InternalAuthMiddleware` then runs (no-ops on user resolution in OAuth2 mode,
but still validates `X-Internal-Auth`).

## Frontend components

### New file

`frontend/src/views/LoginView.vue` — minimal single-screen component:

- App title + short description.
- A single "Sign in" button that does `window.location.href = "/api/v1/oauth2/connect"`.
- Reads an optional `?login_error=…` query param from the URL and surfaces it as an error banner.

### Modified files

| File | Change |
|---|---|
| `frontend/src/services/api.js` | Set `axios.defaults.withCredentials = true` so the session cookie is sent. Add a response interceptor: on `401` with `WWW-Authenticate: OAuth2 login_url=…`, set `userStore.needsLogin = true`. |
| `frontend/src/stores/userStore.js` | Add `displayName` (mirrors backend `display_name`). Add `needsLogin` boolean. Add `async logout()` action: POST `/api/v1/oauth2/logout`, clear local state, set `needsLogin = true`. Existing `initializeUser()` flow is unchanged — the interceptor handles the 401-with-login-url branch. |
| `frontend/src/App.vue` | At the top of the existing template, render `<LoginView v-if="userStore.needsLogin" />` and fall through to the existing UI otherwise. Surface "Logged in as {displayName}" + a logout button in the existing header area. |

No Vue Router is introduced. The full OAuth2 dance is a sequence of
`window.location` navigations and HTTP 302s — the SPA only needs to decide
"show LoginView or the app" via a single boolean.

No frontend env vars needed. The SPA discovers `login_url` from the 401
response header.

## Configuration

| Env var | Default | Required to enable OAuth2? | Purpose |
|---|---|---|---|
| `OAUTH2_AUTH_HOST` | — | Yes | e.g. `https://crm.vincreative.com` |
| `OAUTH2_CLIENT_ID` | — | Yes | App's client ID with the IdP |
| `OAUTH2_CLIENT_SECRET` | — | Yes | Stays server-side only |
| `OAUTH2_SCOPE` | `auth` | No | Space-separated for multi-scope |
| `OAUTH2_PUBLIC_KEY_CACHE_SECONDS` | `3600` | No | JWKS cache TTL |
| `OAUTH2_STATE_TTL_SECONDS` | `300` | No | State cookie lifetime |
| `SESSION_SECRET_KEY` | *already declared* | Yes (must be a real value when OAuth2 is on) | Min 32 random bytes; signs state + session cookies |
| `INSTANCE_URL` | *already declared* | Yes | Builds the absolute `redirect_uri` and decides cookie `Secure` flag |

`.env.example` and `.env.production.example` get a commented `# OAuth2 (optional)` block.

## Edge cases & error handling

- **JWT signature fails on first verify** → force-refresh public key, retry once. Still fails → `502`, log clearly without dumping the token.
- **JWT expired at callback time** → 302 to `/?login_error=token_expired`.
- **State cookie missing / mismatch** → `400`, always clear the state cookie. Possible CSRF or stale tab.
- **IdP returns `?error=…` on callback** → 302 to `/?login_error=…`.
- **IdP host unreachable / 5xx during code exchange or key fetch** → `502`, log full error including hostname.
- **`auth.email` absent from JWT** → `502` (malformed IdP token). Log.
- **Session cookie tampered / expired mid-session** → middleware treats as missing → 401 with `WWW-Authenticate` → SPA re-prompts login via the interceptor.
- **`POST /oauth2/logout` called without a session** → `204` (idempotent).
- **Per-user data isolation** — same email → same `users.username` → same image space. New email → new user record → new isolated space. The existing `user_service.get_or_create_user()` does this; no plumbing changes.
- **Device flows** (`/api/v1/mobile/*`, `/api/v1/addon/*`, `/api/v1/mcp-tokens/*`, `/mcp`, `/i/`, `/s/`) bypass `OAuth2SessionMiddleware` via the shared bypass list. They are unaffected by OAuth2 mode.
- **`X-Internal-Auth` defense-in-depth** continues to apply in both modes when `REQUIRE_INTERNAL_AUTH=true`. OAuth2 mode does not change that posture.

## Testing strategy

### Backend (pytest) — new test files

- `tests/test_oauth2_service.py` — valid / expired / tampered / no-email JWTs; key cache refresh on signature fail; `email.utils.parsedate_to_datetime` parsing of vinCreative's RFC-2822 `expires`.
- `tests/test_session_service.py` — sign+verify roundtrip; expired payload; tampered payload.
- `tests/test_oauth2_endpoints.py` — `/connect` sets state cookie + 302s to provider with correct query string; `/callback` happy path with mocked IdP; state cookie missing; state mismatch; missing `code`; provider `?error=`; JWT verification failure; session cookie has correct attributes (`HttpOnly`, `SameSite=Lax`, `Max-Age` derived from JWT `expires`); `/logout` is idempotent; `/me` returns the cookie fields.
- `tests/test_oauth2_session_middleware.py` — valid cookie populates `request.state`; bypass paths (`/i/`, `/s/`, mobile, addon, mcp, health, version) are not blocked; protected path without cookie returns 401 with `WWW-Authenticate` header.
- `tests/test_internal_auth_in_oauth2_mode.py` — Authelia-header path is skipped when OAuth2 mode is on; `X-Internal-Auth` defense-in-depth still enforced when configured.

### Test fixtures

- A test RSA keypair generated once per session in `conftest.py`.
- `httpx.MockTransport` standing in for the IdP's `/auth/get-key` and `/oauth2/jwttoken` endpoints, returning JWTs signed by the test private key.

### Frontend

No unit-test framework exists today (per code survey). Skip. Rely on:
- The existing `vite build` check (catches type / compile errors).
- Manual smoke testing pre-release.

### Manual smoke checklist (pre-release)

- Cold load with no cookie → SPA shows `LoginView` → click → land on IdP → log in → return → SPA renders with display name shown.
- Reload → cookie still valid → no re-login.
- `POST /oauth2/logout` (via UI logout button) → next nav re-prompts.
- Verify MCP / mobile / addon / `/i/` / `/s/` flows still work in OAuth2 mode.
- Remove `OAUTH2_*` env vars and restart → behavior reverts exactly to today's Authelia / anonymous fallback.
- Tampered cookie (manually edit in browser dev tools) → next request → 401 → re-prompt.

## Rollout notes

- No database migration. No new tables. No new columns.
- The feature is gated entirely on env-var presence, so the same Docker image
  works for OAuth2-enabled and non-OAuth2 deployments.
- The deployment that turns OAuth2 on must set `SESSION_SECRET_KEY` to a real
  ≥32-byte random value; the backend should refuse to start in OAuth2 mode
  with a weak / unset secret (fail-fast assertion at app init).
- Existing user records survive the switch — when a previously-anonymous
  ImageTools instance gains OAuth2, the first sign-in by `email@x` creates a
  fresh user row (the anonymous UUID record remains, orphaned, with its
  images). Existing instances with a single anonymous user can run a one-off
  rename of the anonymous user's `username` to the operator's email if image
  continuity matters; this is operational, not in the backend's
  responsibility.
