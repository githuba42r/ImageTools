"""HTML viewer + raw bytes for the in-memory 5-minute share links.

GET /s/{token}      → HTML page (image in a frame, tag chips, capture date,
                       pin-aware effective expiry).
GET /s/{token}/raw  → image bytes (referenced by the page's <img> tag).
"""
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.rate_limit import get_limiter, image_access_limit
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
    safe_token = _html_escape(token)
    safe_filename = _html_escape(image.original_filename)
    return f"""<!doctype html>
<html><head>
<meta charset="utf-8" />
<title>{safe_filename}</title>
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
  <h1>{safe_filename} {pin_note}</h1>
  <img src="/s/{safe_token}/raw" alt="{safe_filename}" />
  <dl class="meta">
    <dt>Tags:</dt><dd>{tags_html}</dd>
    <dt>Captured:</dt><dd>{captured}</dd>
    <dt>Auto-deletes:</dt><dd>{expiry_value}</dd>
  </dl>
  <div class="footer">This share link expires at {link_expiry}.</div>
</div>
</body></html>"""


@router.get("/{token}", response_class=HTMLResponse)
@get_limiter().limit(image_access_limit)
async def view_share(request: Request, token: str, db: AsyncSession = Depends(get_db)):
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
    pin_at = image.pin_expires_at
    if pin_at is not None and pin_at.tzinfo is not None:
        pin_at = pin_at.replace(tzinfo=None)
    is_pinned = pin_at is not None and pin_at > datetime.utcnow()
    return HTMLResponse(_render_viewer(
        token=token, image=image, link_expires_at=entry.expires_at,
        eff=eff, is_pinned=is_pinned, tags=ImageService.get_tags(image),
    ))


@router.get("/{token}/raw")
@get_limiter().limit(image_access_limit)
async def serve_share_raw(request: Request, token: str, db: AsyncSession = Depends(get_db)):
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
