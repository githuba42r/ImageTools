"""API endpoints for creating temporary image share links."""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.services.image_service import ImageService
from app.services.share_service import create_share_link

router = APIRouter(prefix="/images", tags=["sharing"])


@router.post("/{image_id}/share")
async def create_share(
    image_id: str,
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db),
):
    """Create a temporary, unauthenticated share link for an image.

    The link expires after SHARE_LINK_EXPIRY_SECONDS (default 300s / 5 min).
    """
    image = await ImageService.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Verify the requesting user owns the image
    if image.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="Not your image")

    media_type = f"image/{image.format.lower()}"
    result = create_share_link(
        image_id=image.id,
        image_path=image.current_path,
        media_type=media_type,
        original_filename=image.original_filename,
    )

    return result
