from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.schemas.schemas import CompressionRequest, CompressionResponse
from app.services.compression_service import CompressionService
from app.services.image_service import ImageService
from app.services import profile_service
from app.services.session_service import SessionService

router = APIRouter(prefix="/compression", tags=["compression"])


@router.post("/{image_id}", response_model=CompressionResponse)
async def compress_image(
    image_id: str,
    request: CompressionRequest,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db)
):
    """Compress an image with specified preset, custom profile, or custom parameters."""
    # Verify session exists
    session = await SessionService.get_session(db, x_session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
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
            db, image_id, x_session_id, request.preset, custom_params
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
async def get_presets(
    x_session_id: str = Header(..., alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get available compression presets and user custom profiles."""
    # Verify session exists
    session = await SessionService.get_session(db, x_session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Ensure system default profiles exist
    await profile_service.create_system_default_profiles(db)
    
    # Get system default profiles and user custom profiles
    # This returns the same list as the Manage Profiles modal
    presets = []
    all_profiles = await profile_service.get_profiles(db, x_session_id)
    for profile in all_profiles:
        presets.append({
            "id": profile.id,
            "name": profile.name,
            "label": profile.name,
            "description": f"{profile.format} • {profile.max_width}x{profile.max_height} • Q{profile.quality} • ~{profile.target_size_kb}KB",
            "max_width": profile.max_width,
            "max_height": profile.max_height,
            "quality": profile.quality,
            "target_size_kb": profile.target_size_kb,
            "format": profile.format,
            "is_default": profile.is_default,
            "system_default": profile.system_default,
            "overrides_system_default": getattr(profile, 'overrides_system_default', False),
            "type": "system" if profile.system_default else "custom"
        })
    
    return {"presets": presets}
