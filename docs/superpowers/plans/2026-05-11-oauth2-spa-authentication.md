# OAuth2 SPA Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional vinCreative OAuth2 authentication to the ImageTools SPA + FastAPI backend, activated by env-var presence, with the entire OAuth2 dance proxied through the backend and the JWT discarded after callback.

**Architecture:** A new `OAuth2SessionMiddleware` and OAuth2 router are added to the backend when `OAUTH2_AUTH_HOST` + `OAUTH2_CLIENT_ID` + `OAUTH2_CLIENT_SECRET` are all set. The middleware reads a signed `imagetools_session` cookie and populates `request.state.remote_user` / `remote_name` — the same fields `InternalAuthMiddleware` populates today from Authelia headers. A small Vue 3 `LoginView` is shown when the SPA gets a 401-with-login_url from the backend.

**Tech Stack:** FastAPI · Pydantic · Starlette middleware · `PyJWT[crypto]` (RS256) · `itsdangerous` (signed cookies) · `httpx` · Vue 3 · Pinia · Axios

**Spec:** `docs/superpowers/specs/2026-05-11-oauth2-spa-authentication-design.md`

---

## File Structure

**New backend files:**
- `backend/app/middleware/oauth2_session.py` — `OAuth2SessionMiddleware`
- `backend/app/api/v1/endpoints/oauth2.py` — `/connect` `/callback` `/logout` `/me`
- `backend/app/services/oauth2_service.py` — JWT verify, public-key cache, code-for-token
- `backend/app/services/session_service.py` — signed-cookie sign/verify (session + state)
- `backend/tests/test_session_service.py`
- `backend/tests/test_oauth2_service.py`
- `backend/tests/test_oauth2_endpoints.py`
- `backend/tests/test_oauth2_session_middleware.py`
- `backend/tests/test_internal_auth_in_oauth2_mode.py`

**Modified backend files:**
- `backend/app/core/config.py` — add OAuth2 settings + `oauth2_enabled` property
- `backend/app/middleware/__init__.py` — export `OAuth2SessionMiddleware`
- `backend/app/middleware/internal_auth.py` — skip Authelia-header path in OAuth2 mode
- `backend/app/main.py` — conditionally register middleware + router
- `backend/tests/conftest.py` — add RSA keypair + IdP mock-transport fixtures
- `backend/requirements.txt` — add `PyJWT[crypto]`, `itsdangerous`

**New frontend files:**
- `frontend/src/views/LoginView.vue`

**Modified frontend files:**
- `frontend/src/services/api.js` — `withCredentials = true` + 401 interceptor
- `frontend/src/stores/userStore.js` — `displayName`, `needsLogin`, `logout()`
- `frontend/src/App.vue` — conditional `<LoginView v-if="needsLogin" />` + logout button

**Modified config/docs:**
- `.env.example` — commented OAuth2 block
- `.env.production.example` — commented OAuth2 block

---

## Phase 1 — Foundation

### Task 1: Add Python dependencies

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add the two new dependencies to `backend/requirements.txt`**

Append these two lines (alphabetical placement is fine; the file is unordered):

```
PyJWT[crypto]>=2.8,<3.0  # RS256 JWT verification — crypto extra pulls in cryptography (already pinned)
itsdangerous>=2.1,<3.0   # signed cookies for OAuth2 session + state
```

- [ ] **Step 2: Install into the venv**

Run: `cd /home/philg/src/python/ImageTools/backend && source venv/bin/activate && pip install -r requirements.txt`
Expected: `Successfully installed PyJWT-2.x.x itsdangerous-2.x.x` (or "already satisfied" if local caches have them).

- [ ] **Step 3: Smoke import**

Run: `cd /home/philg/src/python/ImageTools/backend && source venv/bin/activate && python -c "import jwt, itsdangerous; print(jwt.__version__, itsdangerous.__version__)"`
Expected: two version strings printed, no `ImportError`.

- [ ] **Step 4: Commit**

```bash
cd /home/philg/src/python/ImageTools
git add backend/requirements.txt
git commit -m "chore(backend): add PyJWT[crypto] and itsdangerous for OAuth2"
```

---

### Task 2: Add OAuth2 settings to `config.py`

**Files:**
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: Add the settings block above the existing `@property` definitions**

Insert this block immediately after the existing `# Authelia Integration` comment block (around line 101, before `@property def allowed_extensions_list`):

```python
    # OAuth2 (optional) — feature is implicitly active when AUTH_HOST + CLIENT_ID + CLIENT_SECRET are all set.
    # Backend proxies the entire flow; client_secret and JWT never reach the browser.
    OAUTH2_AUTH_HOST: str = ""
    OAUTH2_CLIENT_ID: str = ""
    OAUTH2_CLIENT_SECRET: str = ""
    OAUTH2_SCOPE: str = "auth"
    OAUTH2_PUBLIC_KEY_CACHE_SECONDS: int = 3600
    OAUTH2_STATE_TTL_SECONDS: int = 300

    @property
    def oauth2_enabled(self) -> bool:
        return bool(self.OAUTH2_AUTH_HOST and self.OAUTH2_CLIENT_ID and self.OAUTH2_CLIENT_SECRET)
```

- [ ] **Step 2: Verify the property works**

Run: `cd /home/philg/src/python/ImageTools/backend && source venv/bin/activate && python -c "
from app.core.config import Settings
s1 = Settings(OAUTH2_AUTH_HOST='', OAUTH2_CLIENT_ID='', OAUTH2_CLIENT_SECRET='')
s2 = Settings(OAUTH2_AUTH_HOST='https://idp.example', OAUTH2_CLIENT_ID='cid', OAUTH2_CLIENT_SECRET='sec')
assert s1.oauth2_enabled is False, 'should be disabled when no env'
assert s2.oauth2_enabled is True, 'should be enabled when all three set'
assert s2.OAUTH2_SCOPE == 'auth', 'default scope'
print('config OK')
"`
Expected: `config OK`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/config.py
git commit -m "feat(backend): add OAuth2 settings and oauth2_enabled property"
```

---

### Task 3: Test fixtures for RSA-signed JWTs and IdP mock transport

**Files:**
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Inspect the existing conftest**

Run: `grep -n -E 'fixture|import' /home/philg/src/python/ImageTools/backend/tests/conftest.py | head -20`
Note what's already there so the new fixtures sit alongside cleanly. Do NOT remove or rename any existing fixture.

- [ ] **Step 2: Append the new fixtures to `backend/tests/conftest.py`**

```python
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
```

- [ ] **Step 3: Verify the fixtures import cleanly and produce a usable token**

Create a temp test at `backend/tests/test_conftest_smoke.py`:

```python
import jwt as _jwt

def test_keypair_and_make_jwt(oauth2_keypair, make_jwt):
    token = make_jwt(email="x@y.z", fullname="X Y")
    claims = _jwt.decode(token, oauth2_keypair["public_pem"], algorithms=["RS256"], options={"verify_exp": False})
    assert claims["email"] == "x@y.z"
    assert claims["name"]["fullname"] == "X Y"
    assert "expires" in claims
```

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_conftest_smoke.py -v`
Expected: 1 passed.

- [ ] **Step 4: Delete the smoke test (it was a check, not part of the spec)**

```bash
rm backend/tests/test_conftest_smoke.py
```

- [ ] **Step 5: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "test(backend): RSA keypair + IdP mock transport fixtures for OAuth2"
```

---

## Phase 2 — Pure services (TDD)

### Task 4: `session_service.py` — sign/verify session and state cookies

**Files:**
- Create: `backend/app/services/session_service.py`
- Test: `backend/tests/test_session_service.py`

- [ ] **Step 1: Write the failing tests at `backend/tests/test_session_service.py`**

```python
import time

import pytest

from app.services import session_service


def test_session_sign_verify_roundtrip():
    token = session_service.sign_session({"u": "a@b.c", "d": "A B", "exp": int(time.time()) + 60})
    payload = session_service.verify_session(token, max_age=120)
    assert payload["u"] == "a@b.c"
    assert payload["d"] == "A B"


def test_session_expired_returns_none():
    token = session_service.sign_session({"u": "a@b.c", "d": "A", "exp": 0})
    # Force expiry by passing max_age=0
    assert session_service.verify_session(token, max_age=0) is None


def test_session_tampered_returns_none():
    token = session_service.sign_session({"u": "a@b.c", "d": "A", "exp": int(time.time()) + 60})
    tampered = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
    assert session_service.verify_session(tampered, max_age=120) is None


def test_state_sign_verify_roundtrip():
    token = session_service.sign_state({"s": "abc123", "r": "/foo"})
    payload = session_service.verify_state(token, max_age=300)
    assert payload == {"s": "abc123", "r": "/foo"}


def test_state_and_session_have_distinct_signatures():
    """A session-signed token must not validate as a state token (different salt)."""
    sess = session_service.sign_session({"u": "a@b.c", "d": "A", "exp": int(time.time()) + 60})
    assert session_service.verify_state(sess, max_age=300) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_session_service.py -v`
Expected: ImportError / ModuleNotFoundError on `app.services.session_service` (file doesn't exist yet).

- [ ] **Step 3: Implement `backend/app/services/session_service.py`**

```python
"""Signed-cookie helpers for OAuth2 session and state cookies.

Both cookies are signed by SESSION_SECRET_KEY with itsdangerous.URLSafeTimedSerializer.
Distinct salts ensure a session-cookie value cannot be replayed as a state cookie.
The service is pure functions; no I/O, no DB.
"""
from typing import Optional

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import settings

_SESSION_SALT = "imagetools.session.v1"
_STATE_SALT = "imagetools.oauth2_state.v1"


def _serializer(salt: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SESSION_SECRET_KEY, salt=salt)


def sign_session(payload: dict) -> str:
    return _serializer(_SESSION_SALT).dumps(payload)


def verify_session(token: str, max_age: int) -> Optional[dict]:
    try:
        return _serializer(_SESSION_SALT).loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None


def sign_state(payload: dict) -> str:
    return _serializer(_STATE_SALT).dumps(payload)


def verify_state(token: str, max_age: int) -> Optional[dict]:
    try:
        return _serializer(_STATE_SALT).loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_session_service.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/session_service.py backend/tests/test_session_service.py
git commit -m "feat(backend): signed session+state cookie service for OAuth2"
```

---

### Task 5: `oauth2_service.exchange_code` — code-for-JWT against the IdP

**Files:**
- Create: `backend/app/services/oauth2_service.py`
- Test: `backend/tests/test_oauth2_service.py`

- [ ] **Step 1: Write the failing tests at `backend/tests/test_oauth2_service.py`**

```python
import httpx
import pytest

from app.core.config import settings
from app.services import oauth2_service


@pytest.fixture(autouse=True)
def reset_key_cache():
    oauth2_service._PUBLIC_KEY_CACHE["key"] = None
    oauth2_service._PUBLIC_KEY_CACHE["fetched_at"] = 0
    yield


@pytest.fixture(autouse=True)
def oauth2_settings(monkeypatch):
    monkeypatch.setattr(settings, "OAUTH2_AUTH_HOST", "https://idp.test")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_ID", "imagetools")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_SECRET", "shh")
    monkeypatch.setattr(settings, "OAUTH2_SCOPE", "auth")
    monkeypatch.setattr(settings, "OAUTH2_PUBLIC_KEY_CACHE_SECONDS", 3600)


@pytest.mark.asyncio
async def test_exchange_code_returns_jwt(idp_mock_transport, make_jwt, monkeypatch):
    state = idp_mock_transport["state"]
    state["next_jwt"] = make_jwt()
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    token = await oauth2_service.exchange_code("abc-code", "https://app/api/v1/oauth2/callback")
    assert token == state["next_jwt"]
    assert state["token_calls"] == 1


@pytest.mark.asyncio
async def test_exchange_code_idp_5xx_raises(idp_mock_transport, monkeypatch):
    state = idp_mock_transport["state"]
    state["force_token_status"] = 500
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    with pytest.raises(httpx.HTTPStatusError):
        await oauth2_service.exchange_code("abc-code", "https://app/cb")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_oauth2_service.py -v`
Expected: ModuleNotFoundError on `app.services.oauth2_service`.

- [ ] **Step 3: Create `backend/app/services/oauth2_service.py` with the code-exchange function and a transport hook for tests**

```python
"""OAuth2 IdP integration: code-for-token exchange, public-key fetch+cache, JWT verify.

Pure server-side. Reads OAUTH2_* settings. Uses httpx.AsyncClient with an optional
`_http_transport` override so tests can inject MockTransport without monkeypatching httpx.
"""
import time
from email.utils import parsedate_to_datetime
from typing import Optional

import httpx
import jwt

from app.core.config import settings

# Test hook: tests overwrite this with httpx.MockTransport(...).
_http_transport: Optional[httpx.AsyncBaseTransport] = None

_PUBLIC_KEY_CACHE: dict = {"key": None, "fetched_at": 0.0}


def _client(timeout: float) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=timeout, transport=_http_transport)


async def exchange_code(code: str, redirect_uri: str) -> str:
    """POST /oauth2/jwttoken with the auth code and return the raw JWT string."""
    url = f"{settings.OAUTH2_AUTH_HOST.rstrip('/')}/oauth2/jwttoken"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": settings.OAUTH2_CLIENT_ID,
        "client_secret": settings.OAUTH2_CLIENT_SECRET,
    }
    async with _client(timeout=15.0) as client:
        resp = await client.post(url, data=data)
        resp.raise_for_status()
    body = resp.json()
    token = body.get("access_token") or body.get("token") or body.get("jwt")
    if not token:
        raise ValueError("IdP token response missing access_token")
    return token
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_oauth2_service.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/oauth2_service.py backend/tests/test_oauth2_service.py
git commit -m "feat(backend): oauth2_service.exchange_code with mock-transport hook"
```

---

### Task 6: `oauth2_service.fetch_public_key` with TTL caching

**Files:**
- Modify: `backend/app/services/oauth2_service.py`
- Modify: `backend/tests/test_oauth2_service.py` (append tests)

- [ ] **Step 1: Append the failing tests to `backend/tests/test_oauth2_service.py`**

```python
@pytest.mark.asyncio
async def test_fetch_public_key_caches(idp_mock_transport, monkeypatch):
    state = idp_mock_transport["state"]
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    k1 = await oauth2_service.fetch_public_key()
    k2 = await oauth2_service.fetch_public_key()
    assert k1 == k2 == state["key_pem"]
    assert state["key_calls"] == 1   # second call was a cache hit


@pytest.mark.asyncio
async def test_fetch_public_key_force_refresh_bypasses_cache(idp_mock_transport, monkeypatch):
    state = idp_mock_transport["state"]
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    await oauth2_service.fetch_public_key()
    await oauth2_service.fetch_public_key(force_refresh=True)
    assert state["key_calls"] == 2


@pytest.mark.asyncio
async def test_fetch_public_key_respects_ttl(idp_mock_transport, monkeypatch):
    state = idp_mock_transport["state"]
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    monkeypatch.setattr(settings, "OAUTH2_PUBLIC_KEY_CACHE_SECONDS", 0)  # always expire
    await oauth2_service.fetch_public_key()
    await oauth2_service.fetch_public_key()
    assert state["key_calls"] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_oauth2_service.py -v`
Expected: AttributeError / missing `fetch_public_key`.

- [ ] **Step 3: Add `fetch_public_key` to `backend/app/services/oauth2_service.py`**

Append below `exchange_code`:

```python
async def fetch_public_key(force_refresh: bool = False) -> str:
    """Return the IdP's public key (PEM). In-process cache with TTL = OAUTH2_PUBLIC_KEY_CACHE_SECONDS.

    On force_refresh, the cache is bypassed and refilled (used after a signature failure
    to recover from key rotation).
    """
    now = time.time()
    cached = _PUBLIC_KEY_CACHE["key"]
    fetched_at = _PUBLIC_KEY_CACHE["fetched_at"]
    ttl = settings.OAUTH2_PUBLIC_KEY_CACHE_SECONDS
    if not force_refresh and cached and (now - fetched_at) < ttl:
        return cached
    url = f"{settings.OAUTH2_AUTH_HOST.rstrip('/')}/auth/get-key"
    async with _client(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    pem = resp.text
    _PUBLIC_KEY_CACHE["key"] = pem
    _PUBLIC_KEY_CACHE["fetched_at"] = now
    return pem
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_oauth2_service.py -v`
Expected: 5 passed (2 from Task 5 + 3 new).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/oauth2_service.py backend/tests/test_oauth2_service.py
git commit -m "feat(backend): oauth2_service.fetch_public_key with TTL cache"
```

---

### Task 7: `oauth2_service.verify_jwt` — RS256 verify, expires check, retry on signature fail

**Files:**
- Modify: `backend/app/services/oauth2_service.py`
- Modify: `backend/tests/test_oauth2_service.py` (append tests)

- [ ] **Step 1: Append the failing tests**

```python
@pytest.mark.asyncio
async def test_verify_jwt_valid_returns_identity(idp_mock_transport, make_jwt, monkeypatch):
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    token = make_jwt(email="user@x.test", fullname="User X")
    claims = await oauth2_service.verify_jwt(token)
    assert claims["email"] == "user@x.test"
    assert claims["fullname"] == "User X"
    assert claims["expires_epoch"] > time.time()


@pytest.mark.asyncio
async def test_verify_jwt_missing_email_raises(idp_mock_transport, oauth2_keypair, monkeypatch):
    import jwt as pyjwt
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    # Build a JWT with no email
    from email.utils import format_datetime
    from datetime import datetime, timezone, timedelta
    claims = {
        "user_id": "1",
        "name": {"fullname": "Nameless"},
        "expires": format_datetime(datetime.now(timezone.utc) + timedelta(hours=1)),
    }
    token = pyjwt.encode(claims, oauth2_keypair["private_pem"], algorithm="RS256")
    with pytest.raises(ValueError, match="email"):
        await oauth2_service.verify_jwt(token)


@pytest.mark.asyncio
async def test_verify_jwt_expired_raises(idp_mock_transport, make_jwt, monkeypatch):
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    token = make_jwt(expires_in_seconds=-10)
    with pytest.raises(ValueError, match="expired"):
        await oauth2_service.verify_jwt(token)


@pytest.mark.asyncio
async def test_verify_jwt_retries_on_signature_failure(idp_mock_transport, oauth2_keypair, monkeypatch):
    """First decode fails (stale key), force-refresh, second decode succeeds."""
    import jwt as pyjwt
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from email.utils import format_datetime
    from datetime import datetime, timezone, timedelta

    # Generate a SECOND keypair: cached public key is the old one, but the JWT is signed by the new one.
    new_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    new_private_pem = new_private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    new_public_pem = new_private.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    # Token is signed by the NEW key
    claims = {
        "user_id": "1",
        "email": "rot@x.test",
        "name": {"fullname": "Rot User"},
        "expires": format_datetime(datetime.now(timezone.utc) + timedelta(hours=1)),
    }
    token = pyjwt.encode(claims, new_private_pem, algorithm="RS256")

    # IdP key endpoint starts serving the OLD key, then flips to the NEW key on the second call
    state = idp_mock_transport["state"]
    # Prime cache with OLD key
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    await oauth2_service.fetch_public_key()  # caches old key
    # Now flip IdP to serve the new key
    state["key_pem"] = new_public_pem

    out = await oauth2_service.verify_jwt(token)
    assert out["email"] == "rot@x.test"
    # Two key fetches total: one to prime, one forced after signature failure
    assert state["key_calls"] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_oauth2_service.py -v`
Expected: AttributeError / missing `verify_jwt`.

- [ ] **Step 3: Add `verify_jwt` to `backend/app/services/oauth2_service.py`**

Append:

```python
async def verify_jwt(token: str) -> dict:
    """Verify a vinCreative JWT and return a small identity dict.

    Returns {"email": str, "fullname": Optional[str], "expires_epoch": int}.
    Raises ValueError if the token is malformed, expired, or missing email.
    Raises jwt.InvalidSignatureError or jwt.PyJWTError on persistent verification failure.
    """
    key = await fetch_public_key()
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"verify_aud": False, "verify_exp": False},
        )
    except jwt.InvalidSignatureError:
        key = await fetch_public_key(force_refresh=True)
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"verify_aud": False, "verify_exp": False},
        )

    expires_str = claims.get("expires")
    if not expires_str:
        raise ValueError("JWT missing 'expires' claim")
    try:
        expires_dt = parsedate_to_datetime(expires_str)
    except (TypeError, ValueError) as e:
        raise ValueError(f"JWT 'expires' unparseable: {expires_str}") from e
    expires_epoch = int(expires_dt.timestamp())
    if expires_epoch < time.time():
        raise ValueError("JWT expired")

    email = claims.get("email")
    if not email:
        raise ValueError("JWT missing 'email' claim")

    name = claims.get("name")
    fullname = name.get("fullname") if isinstance(name, dict) else None

    return {"email": email, "fullname": fullname, "expires_epoch": expires_epoch}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_oauth2_service.py -v`
Expected: 9 passed (5 from Tasks 5–6 + 4 new).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/oauth2_service.py backend/tests/test_oauth2_service.py
git commit -m "feat(backend): oauth2_service.verify_jwt with key-refresh retry"
```

---

## Phase 3 — HTTP endpoints (TDD)

### Task 8: OAuth2 router skeleton + `GET /oauth2/connect`

**Files:**
- Create: `backend/app/api/v1/endpoints/oauth2.py`
- Test: `backend/tests/test_oauth2_endpoints.py`

- [ ] **Step 1: Write the failing tests at `backend/tests/test_oauth2_endpoints.py`**

```python
import urllib.parse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.api.v1.endpoints import oauth2 as oauth2_endpoints
from app.services import oauth2_service, session_service


@pytest.fixture(autouse=True)
def oauth2_settings(monkeypatch):
    monkeypatch.setattr(settings, "OAUTH2_AUTH_HOST", "https://idp.test")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_ID", "imagetools")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_SECRET", "shh")
    monkeypatch.setattr(settings, "OAUTH2_SCOPE", "auth")
    monkeypatch.setattr(settings, "INSTANCE_URL", "https://app.test")
    monkeypatch.setattr(settings, "SESSION_SECRET_KEY", "x" * 64)


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(oauth2_endpoints.router, prefix="/api/v1")
    return TestClient(app, follow_redirects=False)


def test_connect_sets_state_cookie_and_redirects(client):
    r = client.get("/api/v1/oauth2/connect")
    assert r.status_code == 302
    loc = r.headers["location"]
    assert loc.startswith("https://idp.test/oauth2/authorize?")
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query)
    assert qs["client_id"] == ["imagetools"]
    assert qs["scope"] == ["auth"]
    assert qs["redirect_uri"] == ["https://app.test/api/v1/oauth2/callback"]
    assert "state" in qs and qs["state"][0]
    # State cookie set
    assert "imagetools_oauth_state" in r.cookies
    # And the cookie's state matches the query state
    parsed = session_service.verify_state(r.cookies["imagetools_oauth_state"], max_age=300)
    assert parsed is not None
    assert parsed["s"] == qs["state"][0]
    assert parsed["r"] == "/"   # default return path


def test_connect_honours_return_query(client):
    r = client.get("/api/v1/oauth2/connect?return=/images")
    parsed = session_service.verify_state(r.cookies["imagetools_oauth_state"], max_age=300)
    assert parsed["r"] == "/images"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_oauth2_endpoints.py -v`
Expected: ModuleNotFoundError on `app.api.v1.endpoints.oauth2`.

- [ ] **Step 3: Create `backend/app/api/v1/endpoints/oauth2.py`**

```python
"""OAuth2 endpoints: /connect /callback /logout /me.

Only registered in main.py when settings.oauth2_enabled is true.
"""
import secrets
import time
import urllib.parse

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.services import oauth2_service, session_service

router = APIRouter(prefix="/oauth2", tags=["oauth2"])

SESSION_COOKIE_NAME = "imagetools_session"
STATE_COOKIE_NAME = "imagetools_oauth_state"


def _is_secure() -> bool:
    return settings.INSTANCE_URL.startswith("https://")


def _redirect_uri() -> str:
    return f"{settings.INSTANCE_URL.rstrip('/')}/api/v1/oauth2/callback"


@router.get("/connect")
async def connect(request: Request, return_: str = "/"):
    # FastAPI doesn't allow `return` as a parameter name, so we re-read raw query
    return_path = request.query_params.get("return", "/")
    state = secrets.token_urlsafe(32)
    state_cookie = session_service.sign_state({"s": state, "r": return_path})

    qs = urllib.parse.urlencode({
        "client_id": settings.OAUTH2_CLIENT_ID,
        "scope": settings.OAUTH2_SCOPE,
        "state": state,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
    })
    authorize_url = f"{settings.OAUTH2_AUTH_HOST.rstrip('/')}/oauth2/authorize?{qs}"

    resp = RedirectResponse(authorize_url, status_code=302)
    resp.set_cookie(
        STATE_COOKIE_NAME,
        state_cookie,
        max_age=settings.OAUTH2_STATE_TTL_SECONDS,
        httponly=True,
        secure=_is_secure(),
        samesite="lax",
        path="/api/v1/oauth2/",
    )
    return resp
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_oauth2_endpoints.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/endpoints/oauth2.py backend/tests/test_oauth2_endpoints.py
git commit -m "feat(backend): GET /oauth2/connect endpoint with signed state cookie"
```

---

### Task 9: `GET /oauth2/callback` — happy path

**Files:**
- Modify: `backend/app/api/v1/endpoints/oauth2.py`
- Modify: `backend/tests/test_oauth2_endpoints.py`

- [ ] **Step 1: Append the failing test**

```python
def test_callback_happy_path_sets_session_cookie(client, idp_mock_transport, make_jwt, monkeypatch):
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    state = idp_mock_transport["state"]
    state["next_jwt"] = make_jwt(email="happy@x.test", fullname="Happy User")

    # Simulate the prior /connect by minting a state cookie ourselves
    state_token = session_service.sign_state({"s": "S1", "r": "/dashboard"})

    r = client.get(
        "/api/v1/oauth2/callback?code=AC&state=S1",
        cookies={STATE_COOKIE_NAME: state_token},
    )
    assert r.status_code == 302
    assert r.headers["location"] == "/dashboard"
    # State cookie cleared (set with Max-Age=0)
    sc = r.headers.get_list("set-cookie")
    assert any("imagetools_oauth_state=" in h and ("Max-Age=0" in h or "max-age=0" in h.lower()) for h in sc)
    # Session cookie set
    assert "imagetools_session" in r.cookies
    payload = session_service.verify_session(r.cookies["imagetools_session"], max_age=24 * 3600)
    assert payload["u"] == "happy@x.test"
    assert payload["d"] == "Happy User"
    assert payload["exp"] > time.time()
```

Add this import at the top of the test file if missing:

```python
import time
from app.api.v1.endpoints.oauth2 import STATE_COOKIE_NAME
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_oauth2_endpoints.py::test_callback_happy_path_sets_session_cookie -v`
Expected: 404 or attribute error (no callback handler yet).

- [ ] **Step 3: Implement the callback in `backend/app/api/v1/endpoints/oauth2.py`**

Append below the `connect` route:

```python
@router.get("/callback")
async def callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    provider_error = request.query_params.get("error")
    state_cookie = request.cookies.get(STATE_COOKIE_NAME)

    if provider_error:
        return _login_error_redirect(provider_error)

    if not code or not state or not state_cookie:
        return _bad_state_response()

    parsed_state = session_service.verify_state(state_cookie, max_age=settings.OAUTH2_STATE_TTL_SECONDS)
    if not parsed_state or parsed_state.get("s") != state:
        return _bad_state_response()

    return_path = parsed_state.get("r", "/") or "/"

    try:
        jwt_str = await oauth2_service.exchange_code(code, _redirect_uri())
        identity = await oauth2_service.verify_jwt(jwt_str)
    except ValueError as e:
        return _login_error_redirect(f"token_invalid:{e}")
    except Exception:
        return _login_error_redirect("idp_unreachable")

    session_payload = {
        "u": identity["email"],
        "d": identity["fullname"] or identity["email"],
        "exp": identity["expires_epoch"],
    }
    session_cookie = session_service.sign_session(session_payload)
    max_age = max(60, identity["expires_epoch"] - int(time.time()))

    resp = RedirectResponse(return_path, status_code=302)
    resp.set_cookie(
        SESSION_COOKIE_NAME,
        session_cookie,
        max_age=max_age,
        httponly=True,
        secure=_is_secure(),
        samesite="lax",
        path="/",
    )
    # Clear state cookie
    resp.delete_cookie(STATE_COOKIE_NAME, path="/api/v1/oauth2/")
    return resp


def _bad_state_response() -> Response:
    resp = RedirectResponse("/?login_error=state_mismatch", status_code=302)
    resp.delete_cookie(STATE_COOKIE_NAME, path="/api/v1/oauth2/")
    return resp


def _login_error_redirect(reason: str) -> Response:
    safe = urllib.parse.quote(reason, safe="")
    resp = RedirectResponse(f"/?login_error={safe}", status_code=302)
    resp.delete_cookie(STATE_COOKIE_NAME, path="/api/v1/oauth2/")
    return resp
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_oauth2_endpoints.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/endpoints/oauth2.py backend/tests/test_oauth2_endpoints.py
git commit -m "feat(backend): GET /oauth2/callback happy path mints session cookie"
```

---

### Task 10: `/oauth2/callback` — error branches

**Files:**
- Modify: `backend/tests/test_oauth2_endpoints.py`

- [ ] **Step 1: Append the failing tests**

```python
def test_callback_state_mismatch(client):
    state_token = session_service.sign_state({"s": "EXPECTED", "r": "/"})
    r = client.get(
        "/api/v1/oauth2/callback?code=AC&state=WRONG",
        cookies={STATE_COOKIE_NAME: state_token},
    )
    assert r.status_code == 302
    assert "login_error=state_mismatch" in r.headers["location"]


def test_callback_missing_state_cookie(client):
    r = client.get("/api/v1/oauth2/callback?code=AC&state=ANY")
    assert r.status_code == 302
    assert "login_error=state_mismatch" in r.headers["location"]


def test_callback_provider_error_passed_through(client):
    state_token = session_service.sign_state({"s": "S1", "r": "/"})
    r = client.get(
        "/api/v1/oauth2/callback?error=access_denied",
        cookies={STATE_COOKIE_NAME: state_token},
    )
    assert r.status_code == 302
    assert "login_error=access_denied" in r.headers["location"]


def test_callback_jwt_missing_email_surfaces_token_invalid(client, idp_mock_transport, oauth2_keypair, monkeypatch):
    import jwt as pyjwt
    from email.utils import format_datetime
    from datetime import datetime, timezone, timedelta
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    bad_claims = {
        "user_id": "1",
        "name": {"fullname": "X"},
        "expires": format_datetime(datetime.now(timezone.utc) + timedelta(hours=1)),
    }
    idp_mock_transport["state"]["next_jwt"] = pyjwt.encode(
        bad_claims, oauth2_keypair["private_pem"], algorithm="RS256"
    )
    state_token = session_service.sign_state({"s": "S1", "r": "/"})
    r = client.get(
        "/api/v1/oauth2/callback?code=AC&state=S1",
        cookies={STATE_COOKIE_NAME: state_token},
    )
    assert r.status_code == 302
    assert "login_error=token_invalid" in r.headers["location"]


def test_callback_idp_unreachable(client, idp_mock_transport, monkeypatch):
    monkeypatch.setattr(oauth2_service, "_http_transport", idp_mock_transport["transport"])
    idp_mock_transport["state"]["force_token_status"] = 503
    state_token = session_service.sign_state({"s": "S1", "r": "/"})
    r = client.get(
        "/api/v1/oauth2/callback?code=AC&state=S1",
        cookies={STATE_COOKIE_NAME: state_token},
    )
    assert r.status_code == 302
    assert "login_error=idp_unreachable" in r.headers["location"]
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python -m pytest tests/test_oauth2_endpoints.py -v`
Expected: 8 passed (the callback implementation from Task 9 already handles these branches).

(If any fail, the gap is in the Task-9 implementation — go back and adjust until all pass.)

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_oauth2_endpoints.py
git commit -m "test(backend): /oauth2/callback error branches (state, provider, JWT, IdP)"
```

---

### Task 11: `POST /oauth2/logout` and `GET /oauth2/me`

**Files:**
- Modify: `backend/app/api/v1/endpoints/oauth2.py`
- Modify: `backend/tests/test_oauth2_endpoints.py`

- [ ] **Step 1: Append the failing tests**

```python
def test_logout_clears_session_cookie(client):
    session_cookie = session_service.sign_session({"u": "a@b.c", "d": "A", "exp": int(time.time()) + 60})
    r = client.post("/api/v1/oauth2/logout", cookies={"imagetools_session": session_cookie})
    assert r.status_code == 204
    sc = r.headers.get_list("set-cookie")
    assert any("imagetools_session=" in h and ("max-age=0" in h.lower() or "expires=Thu, 01 Jan 1970" in h) for h in sc)


def test_logout_without_session_is_idempotent(client):
    r = client.post("/api/v1/oauth2/logout")
    assert r.status_code == 204


def test_me_with_valid_cookie_returns_identity(client):
    session_cookie = session_service.sign_session({"u": "me@x.test", "d": "Me X", "exp": int(time.time()) + 60})
    r = client.get("/api/v1/oauth2/me", cookies={"imagetools_session": session_cookie})
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "me@x.test"
    assert body["display_name"] == "Me X"
    assert body["expires_at"] > time.time()


def test_me_without_cookie_returns_401(client):
    r = client.get("/api/v1/oauth2/me")
    assert r.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_oauth2_endpoints.py -v`
Expected: 404 / route not found.

- [ ] **Step 3: Implement the routes**

Append to `backend/app/api/v1/endpoints/oauth2.py`:

```python
@router.post("/logout", status_code=204)
async def logout(request: Request):
    resp = Response(status_code=204)
    resp.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return resp


@router.get("/me")
async def me(request: Request):
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie:
        raise HTTPException(status_code=401, detail="No session")
    payload = session_service.verify_session(cookie, max_age=30 * 24 * 3600)
    if not payload or payload.get("exp", 0) < time.time():
        raise HTTPException(status_code=401, detail="Session expired")
    return {
        "username": payload["u"],
        "display_name": payload.get("d") or payload["u"],
        "expires_at": payload["exp"],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_oauth2_endpoints.py -v`
Expected: 12 passed (8 from earlier + 4 new).

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/endpoints/oauth2.py backend/tests/test_oauth2_endpoints.py
git commit -m "feat(backend): POST /oauth2/logout and GET /oauth2/me"
```

---

## Phase 4 — Middleware

### Task 12: `OAuth2SessionMiddleware`

**Files:**
- Create: `backend/app/middleware/oauth2_session.py`
- Modify: `backend/app/middleware/__init__.py`
- Test: `backend/tests/test_oauth2_session_middleware.py`

- [ ] **Step 1: Check the existing `backend/app/middleware/__init__.py`**

Run: `cat /home/philg/src/python/ImageTools/backend/app/middleware/__init__.py`
Note the current export style.

- [ ] **Step 2: Write the failing tests at `backend/tests/test_oauth2_session_middleware.py`**

```python
import time

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.config import settings
from app.middleware.oauth2_session import OAuth2SessionMiddleware
from app.services import session_service


@pytest.fixture(autouse=True)
def oauth2_settings(monkeypatch):
    monkeypatch.setattr(settings, "SESSION_SECRET_KEY", "x" * 64)


@pytest.fixture
def app_with_middleware():
    app = FastAPI()
    app.add_middleware(OAuth2SessionMiddleware)

    @app.get("/probe")
    async def probe(request: Request):
        return {
            "remote_user": getattr(request.state, "remote_user", None),
            "remote_name": getattr(request.state, "remote_name", None),
        }

    @app.get("/api/v1/oauth2/connect")
    async def connect_stub():
        return {"stub": True}

    @app.get("/i/anything")
    async def i_stub():
        return {"public": True}

    @app.get("/health")
    async def health_stub():
        return {"ok": True}

    return app


def test_valid_cookie_populates_request_state(app_with_middleware):
    client = TestClient(app_with_middleware)
    cookie = session_service.sign_session({"u": "u@x.test", "d": "U X", "exp": int(time.time()) + 60})
    r = client.get("/probe", cookies={"imagetools_session": cookie})
    assert r.status_code == 200
    assert r.json() == {"remote_user": "u@x.test", "remote_name": "U X"}


def test_no_cookie_returns_401_with_login_url(app_with_middleware):
    client = TestClient(app_with_middleware)
    r = client.get("/probe")
    assert r.status_code == 401
    assert "OAuth2" in r.headers["www-authenticate"]
    assert "/api/v1/oauth2/connect" in r.headers["www-authenticate"]


def test_expired_cookie_returns_401(app_with_middleware):
    client = TestClient(app_with_middleware)
    cookie = session_service.sign_session({"u": "u@x.test", "d": "U", "exp": int(time.time()) - 10})
    r = client.get("/probe", cookies={"imagetools_session": cookie})
    assert r.status_code == 401


def test_tampered_cookie_returns_401(app_with_middleware):
    client = TestClient(app_with_middleware)
    cookie = session_service.sign_session({"u": "u@x.test", "d": "U", "exp": int(time.time()) + 60})
    r = client.get("/probe", cookies={"imagetools_session": cookie[:-2] + "ZZ"})
    assert r.status_code == 401


def test_oauth2_endpoints_bypass(app_with_middleware):
    client = TestClient(app_with_middleware)
    r = client.get("/api/v1/oauth2/connect")
    assert r.status_code == 200


def test_public_image_bypass(app_with_middleware):
    client = TestClient(app_with_middleware)
    r = client.get("/i/anything")
    assert r.status_code == 200


def test_health_bypass(app_with_middleware):
    client = TestClient(app_with_middleware)
    r = client.get("/health")
    assert r.status_code == 200
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_oauth2_session_middleware.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 4: Create `backend/app/middleware/oauth2_session.py`**

```python
"""OAuth2 session middleware.

When OAuth2 mode is active, this middleware validates the imagetools_session cookie
and populates request.state.remote_user / remote_name (same fields InternalAuthMiddleware
populates from Authelia headers when OAuth2 is OFF).

On a protected path with no valid session, returns 401 with WWW-Authenticate that
points the SPA at the login endpoint.
"""
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.services import session_service

logger = logging.getLogger(__name__)

SESSION_COOKIE_NAME = "imagetools_session"
LOGIN_URL = "/api/v1/oauth2/connect"
# Outer guard for verify_session (must be >= any plausible JWT lifetime).
# Inner `exp` field is the real expiry; this just prevents replay of arbitrarily-old signed values.
_OUTER_MAX_AGE_SECONDS = 30 * 24 * 3600

BYPASS_PATHS = {"/health", "/version"}
BYPASS_PREFIXES = (
    "/api/v1/mobile/",
    "/api/v1/addon/",
    "/api/v1/mcp-tokens/",
    "/api/v1/oauth2/",
    "/mcp",
    "/s/",
    "/i/",
)


class OAuth2SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in BYPASS_PATHS or any(path.startswith(p) for p in BYPASS_PREFIXES):
            return await call_next(request)

        token = request.cookies.get(SESSION_COOKIE_NAME)
        payload = None
        if token:
            payload = session_service.verify_session(token, max_age=_OUTER_MAX_AGE_SECONDS)
            if payload and payload.get("exp", 0) < time.time():
                payload = None

        if payload is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
                headers={"WWW-Authenticate": f'OAuth2 login_url="{LOGIN_URL}"'},
            )

        request.state.remote_user = payload.get("u")
        request.state.remote_name = payload.get("d") or payload.get("u")
        return await call_next(request)
```

- [ ] **Step 5: Re-export from `backend/app/middleware/__init__.py`**

If the file currently exports `InternalAuthMiddleware`, add the new export:

```python
from .internal_auth import InternalAuthMiddleware
from .oauth2_session import OAuth2SessionMiddleware

__all__ = ["InternalAuthMiddleware", "OAuth2SessionMiddleware"]
```

(Preserve any other existing exports that were in the file.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_oauth2_session_middleware.py -v`
Expected: 7 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/middleware/oauth2_session.py backend/app/middleware/__init__.py backend/tests/test_oauth2_session_middleware.py
git commit -m "feat(backend): OAuth2SessionMiddleware reads signed cookie -> request.state"
```

---

## Phase 5 — Backend integration

### Task 13: `InternalAuthMiddleware` skips Authelia-header path in OAuth2 mode

**Files:**
- Modify: `backend/app/middleware/internal_auth.py`
- Test: `backend/tests/test_internal_auth_in_oauth2_mode.py`

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.config import settings
from app.middleware.internal_auth import InternalAuthMiddleware


@pytest.fixture
def app_factory():
    def _build():
        app = FastAPI()
        app.add_middleware(InternalAuthMiddleware)

        @app.get("/probe")
        async def probe(request: Request):
            return {
                "remote_user": getattr(request.state, "remote_user", None),
                "remote_name": getattr(request.state, "remote_name", None),
            }

        return app
    return _build


def test_oauth2_off_reads_authelia_headers(monkeypatch, app_factory):
    monkeypatch.setattr(settings, "OAUTH2_AUTH_HOST", "")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_ID", "")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "REQUIRE_INTERNAL_AUTH", False)
    client = TestClient(app_factory())
    r = client.get("/probe", headers={"Remote-User": "alice", "Remote-Name": "Alice"})
    assert r.status_code == 200
    assert r.json() == {"remote_user": "alice", "remote_name": "Alice"}


def test_oauth2_on_does_not_overwrite_existing_request_state(monkeypatch, app_factory):
    """When OAuth2 mode is on, InternalAuthMiddleware must NOT read or overwrite remote_user/name."""
    monkeypatch.setattr(settings, "OAUTH2_AUTH_HOST", "https://idp.test")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_ID", "cid")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_SECRET", "sec")
    monkeypatch.setattr(settings, "REQUIRE_INTERNAL_AUTH", False)

    # Simulate a prior middleware (e.g. OAuth2SessionMiddleware) having set state.
    app = FastAPI()

    @app.middleware("http")
    async def pre_set(request: Request, call_next):
        request.state.remote_user = "from-oauth2@x.test"
        request.state.remote_name = "From OAuth2"
        return await call_next(request)

    app.add_middleware(InternalAuthMiddleware)

    @app.get("/probe")
    async def probe(request: Request):
        return {
            "remote_user": getattr(request.state, "remote_user", None),
            "remote_name": getattr(request.state, "remote_name", None),
        }

    client = TestClient(app)
    # Inject Authelia headers — they MUST NOT overwrite the pre-set state
    r = client.get("/probe", headers={"Remote-User": "spoof@x.test", "Remote-Name": "Spoofer"})
    assert r.status_code == 200
    assert r.json() == {"remote_user": "from-oauth2@x.test", "remote_name": "From OAuth2"}


def test_internal_auth_secret_still_enforced_in_oauth2_mode(monkeypatch, app_factory):
    """Defense-in-depth path is independent of identity-source mode."""
    monkeypatch.setattr(settings, "OAUTH2_AUTH_HOST", "https://idp.test")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_ID", "cid")
    monkeypatch.setattr(settings, "OAUTH2_CLIENT_SECRET", "sec")
    monkeypatch.setattr(settings, "REQUIRE_INTERNAL_AUTH", True)
    monkeypatch.setattr(settings, "INTERNAL_AUTH_SECRET", "shared-secret")

    client = TestClient(app_factory())
    r = client.get("/probe")
    assert r.status_code == 403
    r = client.get("/probe", headers={"X-Internal-Auth": "shared-secret"})
    assert r.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_internal_auth_in_oauth2_mode.py -v`
Expected: `test_oauth2_on_does_not_overwrite_existing_request_state` will fail because the current middleware unconditionally overwrites.

- [ ] **Step 3: Modify `backend/app/middleware/internal_auth.py`**

In the `dispatch` method, replace the existing Authelia-header extraction block (lines 92–98 today):

```python
        # Extract Authelia user information from headers (always, regardless of internal auth)
        remote_user = request.headers.get("Remote-User")
        remote_name = request.headers.get("Remote-Name")
        
        # Store user information in request state for endpoints to access
        request.state.remote_user = remote_user
        request.state.remote_name = remote_name
```

with the OAuth2-aware version:

```python
        # Identity resolution: when OAuth2 mode is on, OAuth2SessionMiddleware has already
        # populated request.state.remote_user/remote_name from the session cookie. In that
        # case we MUST NOT overwrite — Authelia isn't in front of the backend, and reading
        # incoming Remote-User/Remote-Name headers would let a client spoof identity.
        if not settings.oauth2_enabled:
            remote_user = request.headers.get("Remote-User")
            remote_name = request.headers.get("Remote-Name")
            request.state.remote_user = remote_user
            request.state.remote_name = remote_name
            if remote_user:
                logger.debug(f"Authelia user detected: {remote_user} ({remote_name or 'no display name'})")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_internal_auth_in_oauth2_mode.py -v`
Expected: 3 passed.

- [ ] **Step 5: Also run the existing suite to make sure nothing regressed**

Run: `python -m pytest -q`
Expected: all green (current baseline 68 + new tests from prior tasks).

- [ ] **Step 6: Commit**

```bash
git add backend/app/middleware/internal_auth.py backend/tests/test_internal_auth_in_oauth2_mode.py
git commit -m "fix(backend): InternalAuthMiddleware skips Authelia header read in OAuth2 mode"
```

---

### Task 14: Wire middleware + router registration in `main.py`

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Inspect the current registration block**

Run: `grep -n -E 'add_middleware|include_router' /home/philg/src/python/ImageTools/backend/app/main.py | head -30`
Note the exact line numbers of the `app.add_middleware(InternalAuthMiddleware)` line and the imports for endpoints (the line that imports `users, images, ...`).

- [ ] **Step 2: Add the import for the OAuth2 router and middleware**

In `backend/app/main.py`, modify the `from app.api.v1.endpoints import ...` line to also import `oauth2`:

```python
from app.api.v1.endpoints import users, images, compression, history, background, chat, openrouter_oauth, settings as settings_router, mobile, addon, profiles, sharing, mcp_tokens, tags, oauth2
```

And modify `from app.middleware import InternalAuthMiddleware` to:

```python
from app.middleware import InternalAuthMiddleware, OAuth2SessionMiddleware
```

- [ ] **Step 3: Conditionally add the middleware before `InternalAuthMiddleware`**

Locate the line `app.add_middleware(InternalAuthMiddleware)` (around line 135). Insert directly above it:

```python
if settings.oauth2_enabled:
    app.add_middleware(OAuth2SessionMiddleware)
app.add_middleware(InternalAuthMiddleware)
```

(Starlette runs middlewares outermost-first; since `add_middleware` prepends, `OAuth2SessionMiddleware` ends up running BEFORE `InternalAuthMiddleware` even though it's added first — confirm with the order test in Step 5.)

- [ ] **Step 4: Conditionally include the OAuth2 router**

In the router registration block (around line 149), add:

```python
if settings.oauth2_enabled:
    app.include_router(oauth2.router, prefix=settings.API_PREFIX, tags=["oauth2"])
```

Place it next to the other `include_router` calls.

- [ ] **Step 5: Manual ordering check**

Run: `cd /home/philg/src/python/ImageTools/backend && source venv/bin/activate && OAUTH2_AUTH_HOST=https://idp.test OAUTH2_CLIENT_ID=cid OAUTH2_CLIENT_SECRET=sec python -c "
from app.main import app
names = [m.cls.__name__ for m in app.user_middleware]
print(names)
assert 'OAuth2SessionMiddleware' in names
assert names.index('OAuth2SessionMiddleware') < names.index('InternalAuthMiddleware'), names
print('order OK')
"`
Expected: `order OK` (OAuth2SessionMiddleware appears earlier in the user_middleware list, which means it runs OUTERMOST — first on the way in).

- [ ] **Step 6: Manual route check**

Same env, run: `python -c "
from app.main import app
paths = sorted({r.path for r in app.routes})
for p in ['/api/v1/oauth2/connect', '/api/v1/oauth2/callback', '/api/v1/oauth2/logout', '/api/v1/oauth2/me']:
    assert p in paths, (p, paths)
print('routes OK')
"`
Expected: `routes OK`.

- [ ] **Step 7: Run the full backend test suite**

Run: `python -m pytest -q`
Expected: all green.

- [ ] **Step 8: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(backend): wire OAuth2 middleware and router conditionally in main"
```

---

## Phase 6 — Frontend

### Task 15: `LoginView.vue`

**Files:**
- Create: `frontend/src/views/LoginView.vue`

- [ ] **Step 1: Check whether `frontend/src/views/` exists**

Run: `ls /home/philg/src/python/ImageTools/frontend/src/views/ 2>/dev/null || echo "no views dir"`

If "no views dir", create it implicitly when writing `LoginView.vue` (the Write tool will create parent dirs).

- [ ] **Step 2: Create `frontend/src/views/LoginView.vue`**

```vue
<template>
  <div class="login-screen">
    <div class="login-card">
      <h1>ImageTools</h1>
      <p>Sign in with your vinCreative account to access your images.</p>
      <div v-if="errorMessage" class="login-error" role="alert">
        {{ errorMessage }}
      </div>
      <button class="login-button" @click="signIn">Sign in</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const errorMessage = computed(() => {
  const params = new URLSearchParams(window.location.search)
  const err = params.get('login_error')
  if (!err) return null
  // Friendly messages for known cases; otherwise show raw
  switch (true) {
    case err.startsWith('token_invalid'): return 'Sign-in failed: the identity token was rejected.'
    case err === 'state_mismatch':        return 'Sign-in expired or was tampered with. Please try again.'
    case err === 'idp_unreachable':       return 'The identity provider is currently unreachable. Please try again shortly.'
    case err === 'access_denied':         return 'Access was denied at the identity provider.'
    default:                              return `Sign-in error: ${decodeURIComponent(err)}`
  }
})

function signIn() {
  const ret = encodeURIComponent(window.location.pathname + window.location.search)
  window.location.href = `/api/v1/oauth2/connect?return=${ret}`
}
</script>

<style scoped>
.login-screen {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1a1a1a;
  color: #eee;
}
.login-card {
  background: #2a2a2a;
  padding: 2rem 3rem;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  max-width: 380px;
  text-align: center;
}
.login-card h1 { margin: 0 0 0.5rem; }
.login-card p  { margin: 0 0 1.5rem; opacity: 0.75; }
.login-button {
  padding: 0.75rem 1.5rem;
  background: #4a9eff;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
}
.login-button:hover { background: #3a8eef; }
.login-error {
  background: #4a1a1a;
  color: #f88;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}
</style>
```

- [ ] **Step 3: Verify the build still works**

Run: `cd /home/philg/src/python/ImageTools/frontend && npm run build 2>&1 | tail -10`
Expected: `✓ built in N.NNs` (no errors mentioning LoginView).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/LoginView.vue
git commit -m "feat(frontend): LoginView component for OAuth2 sign-in"
```

---

### Task 16: `api.js` — `withCredentials` + 401 interceptor

**Files:**
- Modify: `frontend/src/services/api.js`

- [ ] **Step 1: Inspect current `api.js`**

Run: `cat /home/philg/src/python/ImageTools/frontend/src/services/api.js`
Identify (a) the axios instance, and (b) the existing request interceptor that injects `X-User-ID`.

- [ ] **Step 2: Modify `frontend/src/services/api.js`**

At the top of the file, after the existing axios instance is created, add:

```js
// Send cookies (including the OAuth2 session cookie) on cross-origin requests.
// The backend uses HttpOnly cookies; the SPA never reads or writes them directly.
api.defaults.withCredentials = true
```

(Use the actual name of the axios instance — if it's `apiClient` or similar, adapt accordingly.)

Then add a response interceptor at the bottom of the module, before the default export:

```js
// 401 + WWW-Authenticate: OAuth2 → SPA enters login state.
// Lazy-import the user store to avoid a circular module load at startup.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status
    const wwwAuth = error?.response?.headers?.['www-authenticate'] || ''
    if (status === 401 && /^OAuth2\b/i.test(wwwAuth)) {
      const { useUserStore } = await import('../stores/userStore.js')
      const store = useUserStore()
      store.needsLogin = true
    }
    return Promise.reject(error)
  }
)
```

- [ ] **Step 3: Verify the build still works**

Run: `cd frontend && npm run build 2>&1 | tail -10`
Expected: green build.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/services/api.js
git commit -m "feat(frontend): withCredentials + 401-OAuth2 interceptor in api.js"
```

---

### Task 17: `userStore.js` — `displayName`, `needsLogin`, `logout`

**Files:**
- Modify: `frontend/src/stores/userStore.js`

- [ ] **Step 1: Inspect current store**

Run: `cat /home/philg/src/python/ImageTools/frontend/src/stores/userStore.js`
Note whether it uses the Options-style `defineStore({ state, actions })` or Composition-style `defineStore('user', () => { ... })`. The snippet below assumes Options-style — adapt the syntax to the file's style.

- [ ] **Step 2: Modify `frontend/src/stores/userStore.js`**

Add the new state fields (in `state`):

```js
displayName: null,
needsLogin: false,
```

Make sure `state` returns these alongside the existing `userId` and `userData`.

Add the `logout` action (alongside the existing `initializeUser`):

```js
async logout() {
  try {
    await api.post('/oauth2/logout')
  } catch (_) {
    // Idempotent; ignore failures
  }
  this.userId = null
  this.userData = null
  this.displayName = null
  localStorage.removeItem('imagetools_user_id')
  this.needsLogin = true
},
```

If `initializeUser` writes `userData.display_name` from the response body, also write it to `this.displayName`. Specifically, find the line that sets `this.userData = response.data` (or equivalent) and add immediately after:

```js
this.displayName = response.data?.display_name || response.data?.username || null
```

- [ ] **Step 3: Verify the build still works**

Run: `cd frontend && npm run build 2>&1 | tail -10`
Expected: green build.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/stores/userStore.js
git commit -m "feat(frontend): userStore.displayName/needsLogin + logout action"
```

---

### Task 18: `App.vue` — conditional `<LoginView>` + logout button

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Inspect current `App.vue`**

Run: `head -80 /home/philg/src/python/ImageTools/frontend/src/App.vue`
Identify the root template element and any existing header / toolbar area.

- [ ] **Step 2: Modify `frontend/src/App.vue` template**

At the very top of the `<template>` block, wrap the existing root with a conditional:

```vue
<template>
  <LoginView v-if="userStore.needsLogin" />
  <template v-else>
    <!-- existing root content moves here, unchanged -->
    <!-- ...existing template... -->
  </template>
</template>
```

Inside the existing header / toolbar area (or — if there isn't one — at the top of the existing main content), add:

```vue
<div v-if="userStore.displayName" class="user-badge">
  Logged in as <strong>{{ userStore.displayName }}</strong>
  <button class="logout-link" @click="userStore.logout">Sign out</button>
</div>
```

In the `<script setup>` block, add:

```js
import LoginView from './views/LoginView.vue'
```

(If the file is not using `<script setup>`, register `LoginView` in the `components` map and reference the store via `mapStores` or the existing pattern.)

Add scoped styles at the bottom for `.user-badge` and `.logout-link`:

```vue
<style scoped>
.user-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  opacity: 0.85;
}
.logout-link {
  background: none;
  border: 1px solid #888;
  color: inherit;
  padding: 0.1rem 0.5rem;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.8rem;
}
.logout-link:hover { background: rgba(255,255,255,0.06); }
</style>
```

- [ ] **Step 3: Verify the build still works**

Run: `cd frontend && npm run build 2>&1 | tail -10`
Expected: green build.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat(frontend): conditional LoginView render + Sign-out button in App.vue"
```

---

## Phase 7 — Docs & verification

### Task 19: Document the new env vars

**Files:**
- Modify: `.env.example`
- Modify: `.env.production.example`

- [ ] **Step 1: Append the OAuth2 block to `.env.example`**

```
# --- OAuth2 (optional) ----------------------------------------------------
# When all three OAUTH2_* values below are set, the SPA requires vinCreative
# OAuth2 sign-in. Leave any one blank to disable OAuth2 and fall back to
# Authelia / anonymous behaviour.
# OAUTH2_AUTH_HOST=https://crm.vincreative.com
# OAUTH2_CLIENT_ID=imagetools
# OAUTH2_CLIENT_SECRET=
# OAUTH2_SCOPE=auth
# OAUTH2_PUBLIC_KEY_CACHE_SECONDS=3600
# OAUTH2_STATE_TTL_SECONDS=300
# SESSION_SECRET_KEY=$(openssl rand -hex 32)   # Required when OAuth2 is on.
```

- [ ] **Step 2: Append the same block to `.env.production.example`**

(Identical content; production examples are guidance, not auto-loaded.)

- [ ] **Step 3: Commit**

```bash
git add .env.example .env.production.example
git commit -m "docs(env): OAuth2 configuration block in env examples"
```

---

### Task 20: Final verification — full test suite + frontend build + manual smoke setup

**Files:** none modified

- [ ] **Step 1: Backend test suite — OAuth2 OFF baseline**

Run: `cd backend && source venv/bin/activate && python -m pytest -q`
Expected: all green. No OAuth2-mode tests should run with active OAuth2 settings except those that monkeypatch them.

- [ ] **Step 2: Backend test suite — OAuth2 ON env**

Run: `OAUTH2_AUTH_HOST=https://idp.test OAUTH2_CLIENT_ID=cid OAUTH2_CLIENT_SECRET=sec python -m pytest -q`
Expected: all green. Verifies no settings-coupled test depends on OAuth2 being off.

- [ ] **Step 3: Frontend build**

Run: `cd frontend && npm run build`
Expected: green build, no new errors.

- [ ] **Step 4: Manual smoke checklist (write to a temporary file, not committed)**

Write to `/tmp/imagetools-oauth2-smoke.md`:

```
## OAuth2 manual smoke — pre-release

Setup:
  export OAUTH2_AUTH_HOST=<the vinCreative auth host>
  export OAUTH2_CLIENT_ID=<the registered client>
  export OAUTH2_CLIENT_SECRET=<...>
  export SESSION_SECRET_KEY=$(openssl rand -hex 32)
  export INSTANCE_URL=<the URL the browser sees, e.g. https://imagetools.example>

  Restart the backend so the new env is picked up.

Checks:
  [ ] Cold load: open / in a private window → LoginView appears
  [ ] Click Sign in → land on vinCreative login page
  [ ] Authenticate → return to / → app loads, "Logged in as <fullname>" visible
  [ ] Reload page → still logged in (cookie valid)
  [ ] Sign out → next nav re-prompts login
  [ ] Hit /i/<token> and /s/<token> with no session cookie → still served (bypassed)
  [ ] MCP token flow (curl /api/v1/mcp-tokens/whoami) → still works with bearer
  [ ] Remove OAUTH2_* env vars + restart → SPA falls back to existing behaviour
```

- [ ] **Step 5: Final commit (optional — no files changed)**

If there are uncommitted files (there shouldn't be), skip. Otherwise nothing to do here.

- [ ] **Step 6: Branch summary**

Run: `git log --oneline master..HEAD`
Expected: a clean series of TDD commits, each scoped to one task.

---

## Self-Review Notes

This plan has been checked against the spec:

- **Spec coverage** — each spec section maps to one or more tasks:
  - Activation (env-var trigger) → Task 2, Task 14
  - Endpoints (`/connect`, `/callback`, `/logout`, `/me`) → Tasks 8, 9, 10, 11
  - Identity flow (parallel-populator middlewares) → Tasks 12, 13
  - Backend components (sessions, oauth2 service) → Tasks 4, 5, 6, 7
  - Frontend components (LoginView, api.js, userStore, App.vue) → Tasks 15, 16, 17, 18
  - Config surface → Task 2, Task 19
  - Edge cases (state mismatch, IdP error, JWT failures, expired/tampered cookies) → Tasks 10, 11, 12
  - Testing strategy (five test files + fixtures) → Tasks 3, 4, 5, 6, 7, 8–11, 12, 13
- **No placeholders** — every code step shows real code; commands have expected outputs.
- **Type / name consistency** — `SESSION_COOKIE_NAME = "imagetools_session"` and `STATE_COOKIE_NAME = "imagetools_oauth_state"` reused across Task 8, 9, 10, 11, 12. `oauth2_service._http_transport`, `_PUBLIC_KEY_CACHE` used consistently across Tasks 5–7 and Tasks 9–10's tests.
