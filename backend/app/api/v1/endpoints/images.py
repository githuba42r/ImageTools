from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.core.config import settings
from app.schemas.schemas import ImageResponse, RotateRequest, RotateResponse
from app.services.image_service import ImageService
from app.services.session_service import SessionService

router = APIRouter(prefix="/images", tags=["images"])


@router.post("", response_model=ImageResponse)
async def upload_image(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload a new image."""
    # Validate session
    if not await SessionService.validate_session(db, session_id):
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    # Check image limit
    image_count = await ImageService.count_session_images(db, session_id)
    if image_count >= settings.MAX_IMAGES_PER_SESSION:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.MAX_IMAGES_PER_SESSION} images per session"
        )
    
    # Validate file extension
    filename = file.filename or "image.jpg"
    ext = filename.split(".")[-1].lower()
    if ext not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=400,
            detail=f"File type .{ext} not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}"
        )
    
    # Save image
    image = await ImageService.save_uploaded_image(
        db, session_id, filename, file.file
    )
    
    # Build response
    return ImageResponse(
        id=image.id,
        session_id=image.session_id,
        original_filename=image.original_filename,
        original_size=image.original_size,
        current_size=image.current_size,
        width=image.width,
        height=image.height,
        format=image.format,
        thumbnail_url=f"{settings.API_PREFIX}/images/{image.id}/thumbnail",
        image_url=f"{settings.API_PREFIX}/images/{image.id}/current",
        created_at=image.created_at,
        updated_at=image.updated_at
    )


@router.get("/session/{session_id}", response_model=List[ImageResponse])
async def get_session_images(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all images for a session."""
    images = await ImageService.get_session_images(db, session_id)
    
    return [
        ImageResponse(
            id=img.id,
            session_id=img.session_id,
            original_filename=img.original_filename,
            original_size=img.original_size,
            current_size=img.current_size,
            width=img.width,
            height=img.height,
            format=img.format,
            thumbnail_url=f"{settings.API_PREFIX}/images/{img.id}/thumbnail",
            image_url=f"{settings.API_PREFIX}/images/{img.id}/current",
            created_at=img.created_at,
            updated_at=img.updated_at
        )
        for img in images
    ]


@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(
    image_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get image metadata."""
    image = await ImageService.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    return ImageResponse(
        id=image.id,
        session_id=image.session_id,
        original_filename=image.original_filename,
        original_size=image.original_size,
        current_size=image.current_size,
        width=image.width,
        height=image.height,
        format=image.format,
        thumbnail_url=f"{settings.API_PREFIX}/images/{image.id}/thumbnail",
        image_url=f"{settings.API_PREFIX}/images/{image.id}/current",
        created_at=image.created_at,
        updated_at=image.updated_at
    )


@router.get("/{image_id}/current")
async def get_current_image(
    image_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Download current version of image."""
    image = await ImageService.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(
        image.current_path,
        media_type=f"image/{image.format.lower()}",
        filename=image.original_filename
    )


@router.get("/{image_id}/thumbnail")
async def get_thumbnail(
    image_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get image thumbnail."""
    image = await ImageService.get_image(db, image_id)
    if not image or not image.thumbnail_path:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    
    return FileResponse(
        image.thumbnail_path,
        media_type=f"image/{image.format.lower()}"
    )


@router.delete("/{image_id}")
async def delete_image(
    image_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete an image."""
    success = await ImageService.delete_image(db, image_id)
    if not success:
        raise HTTPException(status_code=404, detail="Image not found")
    
    return {"success": True, "message": "Image deleted"}


@router.post("/{image_id}/rotate", response_model=RotateResponse)
async def rotate_image(
    image_id: str,
    request: RotateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Rotate an image by 90, 180, or 270 degrees."""
    # Verify image exists
    image = await ImageService.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Rotate image
    try:
        output_path, new_size, width, height = await ImageService.rotate_image(
            db, image_id, request.degrees
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return RotateResponse(
        image_id=image_id,
        degrees=request.degrees,
        new_size=new_size,
        width=width,
        height=height,
        image_url=f"{settings.API_PREFIX}/images/{image_id}/current"
    )
