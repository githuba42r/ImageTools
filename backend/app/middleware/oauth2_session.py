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

# OAuth2 session enforcement is scoped to API endpoints. Static SPA assets
# (/, /assets/*, SPA router paths), /mcp, /s/, /i/, /health, /version are not
# under /api/ and pass through automatically — the SPA loads and renders its
# own LoginView when an API call returns 401 + WWW-Authenticate: OAuth2.
API_PREFIX = "/api/"
BYPASS_PREFIXES = (
    "/api/v1/mobile/",
    "/api/v1/addon/",
    "/api/v1/mcp-tokens/",
    "/api/v1/oauth2/",
)


class OAuth2SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith(API_PREFIX):
            return await call_next(request)
        if any(path.startswith(p) for p in BYPASS_PREFIXES):
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
