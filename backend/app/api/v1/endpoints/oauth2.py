"""OAuth2 endpoints: /connect /callback /logout /me.

Only registered in main.py when settings.oauth2_enabled is true.
"""
import logging
import secrets
import time
import urllib.parse

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.services import oauth2_service, session_service

logger = logging.getLogger(__name__)

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
    # Open-redirect guard: only accept same-origin absolute paths.
    # Reject anything that starts with "//" (scheme-relative URL, e.g. //evil.com)
    # or doesn't start with "/" (could be a full URL or a relative path).
    if not return_path.startswith("/") or return_path.startswith("//"):
        return_path = "/"
    state = secrets.token_urlsafe(32)
    state_cookie = session_service.sign_state({"s": state, "r": return_path})

    qs = urllib.parse.urlencode({
        "client_id": settings.OAUTH2_CLIENT_ID,
        "scope": settings.OAUTH2_SCOPE,
        "state": state,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
    })
    authorize_url = f"{settings.OAUTH2_AUTH_HOST.rstrip('/')}/oauth2/connect?{qs}"

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
    # Defense-in-depth: same-origin guard on the cookie-borne return path too.
    if not return_path.startswith("/") or return_path.startswith("//"):
        return_path = "/"

    try:
        jwt_str = await oauth2_service.exchange_code(code, _redirect_uri())
        identity = await oauth2_service.verify_jwt(jwt_str)
    except ValueError as e:
        logger.warning("OAuth2 callback failed (token_invalid): %s", e)
        return _login_error_redirect(f"token_invalid:{e}")
    except Exception:
        logger.exception("OAuth2 callback failed (idp_unreachable branch)")
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
