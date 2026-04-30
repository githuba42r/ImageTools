"""GET /i/{token} — serve image bytes for an HMAC-signed presigned URL.

Order of operations matters:
  1. Decode the payload (untrusted) to extract image_id.
  2. Look up the image to fetch its current url_pepper.
  3. Verify the HMAC using that pepper.
A rotated pepper makes the verify fail → 404, which is how revocation works.
"""
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.presigned_url import decode_token_unverified, verify_token
from app.services.image_service import ImageService

router = APIRouter(prefix="/i", tags=["presigned"])


@router.get("/{token}")
async def serve_presigned(token: str, db: AsyncSession = Depends(get_db)):
    decoded = decode_token_unverified(token)
    if decoded is None:
        raise HTTPException(status_code=404, detail="Invalid or expired URL")
    image = await ImageService.get_image(db, decoded["image_id"])
    if image is None or not image.current_path or not os.path.exists(image.current_path):
        raise HTTPException(status_code=404, detail="Image not found")
    if not verify_token(
        payload=decoded["payload"], sig=decoded["sig"],
        pepper=image.url_pepper, exp=decoded["exp"],
    ):
        # Either expired, signature mismatch, or pepper rotated since mint.
        raise HTTPException(status_code=404, detail="Invalid or expired URL")
    return FileResponse(
        path=image.current_path,
        media_type=f"image/{image.format.lower()}",
        filename=image.original_filename,
    )
