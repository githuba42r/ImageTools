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
    # vinCreative IdP wraps the PEM in {"status": bool, "data": "<PEM>", "timestamp": int}.
    # Other IdPs may return the raw PEM as the body — fall back to resp.text.
    ctype = resp.headers.get("content-type", "")
    if "application/json" in ctype:
        body = resp.json()
        pem = body.get("data") or ""
        if not pem.startswith("-----BEGIN"):
            raise ValueError(
                f"IdP /auth/get-key JSON did not contain a PEM in 'data' (keys={list(body.keys())})"
            )
    else:
        pem = resp.text
    _PUBLIC_KEY_CACHE["key"] = pem
    _PUBLIC_KEY_CACHE["fetched_at"] = now
    return pem


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
