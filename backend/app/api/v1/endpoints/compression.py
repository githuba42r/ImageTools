from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.schemas.schemas import CompressionRequest, CompressionResponse
from app.services.compression_service import CompressionService
from app.services.image_service import ImageService

router = APIRouter(prefix="/compression", tags=["compression"])


@router.post("/{image_id}", response_model=CompressionResponse)
async def compress_image(
    image_id: str,
    request: CompressionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Compress an image with specified preset or custom parameters."""
    # Verify image exists
    image = await ImageService.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Build custom params if provided
    custom_params = None
    if request.preset == "custom":
        if not all([request.quality, request.max_width, request.max_height, request.format]):
            raise HTTPException(
                status_code=400,
                detail="Custom preset requires quality, max_width, max_height, and format"
            )
        custom_params = {
            "quality": request.quality,
            "max_width": request.max_width,
            "max_height": request.max_height,
            "target_size_kb": request.target_size_kb,
            "format": request.format,
        }
    
    # Compress image
    try:
        output_path, compressed_size, original_size = await CompressionService.compress_image(
            db, image_id, request.preset, custom_params
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Calculate compression ratio
    compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
    
    return CompressionResponse(
        image_id=image_id,
        original_size=original_size,
        compressed_size=compressed_size,
        compression_ratio=round(compression_ratio, 2),
        image_url=f"{settings.API_PREFIX}/images/{image_id}/current"
    )


@router.get("/presets")
async def get_presets():
    """Get available compression presets."""
    return {
        "presets": [
            {
                "name": "email",
                "label": "Email",
                "description": "Optimized for email attachments (~500KB)",
                "max_width": settings.EMAIL_MAX_WIDTH,
                "max_height": settings.EMAIL_MAX_HEIGHT,
                "quality": settings.EMAIL_QUALITY,
                "target_size_kb": settings.EMAIL_TARGET_SIZE_KB,
                "format": settings.EMAIL_FORMAT,
            },
            {
                "name": "web",
                "label": "Web",
                "description": "Balanced quality for web (~500KB)",
                "max_width": settings.WEB_MAX_WIDTH,
                "max_height": settings.WEB_MAX_HEIGHT,
                "quality": settings.WEB_QUALITY,
                "target_size_kb": settings.WEB_TARGET_SIZE_KB,
                "format": settings.WEB_FORMAT,
            },
            {
                "name": "web_hq",
                "label": "Web HQ",
                "description": "High quality for web (~1MB)",
                "max_width": settings.WEB_HQ_MAX_WIDTH,
                "max_height": settings.WEB_HQ_MAX_HEIGHT,
                "quality": settings.WEB_HQ_QUALITY,
                "target_size_kb": settings.WEB_HQ_TARGET_SIZE_KB,
                "format": settings.WEB_HQ_FORMAT,
            },
            {
                "name": "custom",
                "label": "Custom",
                "description": "Define your own parameters",
            }
        ]
    }
