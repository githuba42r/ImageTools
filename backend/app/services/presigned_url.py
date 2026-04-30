"""Stateless HMAC-signed presigned URLs for images.

URL form:  {INSTANCE_URL}/i/{payload}.{sig}
  payload  = base64url("{image_id}|{exp_epoch}")
  sig      = hex( hmac_sha256(PRESIGNED_URL_SECRET, payload + "|" + url_pepper) )

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
