from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
import zipfile
import os
from app.core.database import get_db
from app.core.config import settings
from app.schemas.schemas import (
    ImageResponse, ImageTagsUpdate, PinRequest, PresignedUrlRequest, PresignedUrlResponse,
    RotateRequest, RotateResponse, FlipRequest, FlipResponse, ResizeRequest, ResizeResponse,
)
from app.services.image_service import ImageService
from app.services.user_service import UserService, ANONYMOUS_USER_ID

router = APIRouter(prefix="/images", tags=["images"])


@router.post("", response_model=ImageResponse)
async def upload_image(
    user_id: str = Form(...),
    file: UploadFile = File(...),
    tag: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Upload a new image."""
    # Validate user
    if not await UserService.validate_user(db, user_id):
        raise HTTPException(status_code=401, detail="Invalid user")

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
        db, user_id, filename, file.file, tag=tag
    )

    # Build response
    return ImageService.to_response(image)


@router.get("/user/{user_id}", response_model=List[ImageResponse])
async def get_user_images(
    user_id: str,
    tag: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all images for a user."""
    images = await ImageService.get_user_images(db, user_id, tag=tag)
    return [ImageService.to_response(img) for img in images]


@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(
    image_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get image metadata."""
    image = await ImageService.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    return ImageService.to_response(image)


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
    image = await ImageService.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

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


@router.post("/{image_id}/flip", response_model=FlipResponse)
async def flip_image(
    image_id: str,
    request: FlipRequest,
    db: AsyncSession = Depends(get_db)
):
    """Flip an image horizontally or vertically."""
    image = await ImageService.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        output_path, new_size, width, height = await ImageService.flip_image(
            db, image_id, request.direction
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return FlipResponse(
        image_id=image_id,
        direction=request.direction,
        new_size=new_size,
        width=width,
        height=height,
        image_url=f"{settings.API_PREFIX}/images/{image_id}/current"
    )


@router.post("/{image_id}/resize", response_model=ResizeResponse)
async def resize_image(
    image_id: str,
    request: ResizeRequest,
    db: AsyncSession = Depends(get_db)
):
    """Resize an image to specified dimensions."""
    image = await ImageService.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    original_width = image.width
    original_height = image.height

    try:
        output_path, new_size, width, height = await ImageService.resize_image(
            db, image_id, request.width, request.height
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resize failed: {str(e)}")

    return ResizeResponse(
        image_id=image_id,
        original_width=original_width,
        original_height=original_height,
        new_width=width,
        new_height=height,
        new_size=new_size,
        image_url=f"{settings.API_PREFIX}/images/{image_id}/current"
    )


@router.post("/{image_id}/edit", response_model=ImageResponse)
async def save_edited_image(
    image_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Save edited image from editor."""
    print(f"[EDIT] Received edit request for image: {image_id}")
    print(f"[EDIT] File info: filename={file.filename}, content_type={file.content_type}")

    image = await ImageService.get_image(db, image_id)
    if not image:
        print(f"[EDIT] Image not found: {image_id}")
        raise HTTPException(status_code=404, detail="Image not found")

    print(f"[EDIT] Image found: {image.original_filename}")

    try:
        output_path, new_size, width, height = await ImageService.save_edited_image(
            db, image_id, file.file
        )
        print(f"[EDIT] Image saved successfully: path={output_path}, size={new_size}, dims={width}x{height}")
    except Exception as e:
        print(f"[EDIT] Error saving image: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to save edited image: {str(e)}")

    await db.refresh(image)

    print(f"[EDIT] Returning response with dimensions: {image.width}x{image.height}")

    # Preserve cache-busting query strings on URLs after a content edit so
    # browsers fetch the new bytes; everything else comes from the helper.
    response = ImageService.to_response(image)
    bust = int(image.updated_at.timestamp() * 1000)
    response.thumbnail_url = f"{settings.API_PREFIX}/images/{image.id}/thumbnail?t={bust}"
    response.image_url = f"{settings.API_PREFIX}/images/{image.id}/current?t={bust}"
    return response


@router.put("/{image_id}/tags", response_model=ImageResponse)
async def update_image_tags(
    image_id: str,
    payload: ImageTagsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update tags for an image."""
    image = await ImageService.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    ImageService.set_tags(image, payload.tags)
    await db.commit()
    await db.refresh(image)
    return ImageService.to_response(image)


@router.get("/{image_id}/exif")
async def get_image_exif(
    image_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get EXIF metadata for an image."""
    image = await ImageService.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        exif_data = ImageService.extract_exif(image.current_path)

        if 'GPS' not in exif_data or not exif_data.get('GPS'):
            if image.gps_latitude is not None and image.gps_longitude is not None:
                exif_data['GPS'] = {
                    'latitude': image.gps_latitude,
                    'longitude': image.gps_longitude,
                    'latitude_ref': 'N' if image.gps_latitude >= 0 else 'S',
                    'longitude_ref': 'E' if image.gps_longitude >= 0 else 'W',
                }
                if image.gps_altitude is not None:
                    exif_data['GPS']['altitude'] = image.gps_altitude

        return {"image_id": image_id, "exif": exif_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract EXIF: {str(e)}")


@router.post("/download-zip")
async def download_images_as_zip(
    image_ids: List[str] = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
    """Download multiple images as a ZIP file."""
    if not image_ids:
        raise HTTPException(status_code=400, detail="No images specified")

    images = []
    for image_id in image_ids:
        image = await ImageService.get_image(db, image_id)
        if image:
            images.append(image)

    if not images:
        raise HTTPException(status_code=404, detail="No valid images found")

    date_str = datetime.now().strftime("%Y-%m-%d")
    zip_filename = f"Images-{date_str}.zip"
    zip_path = os.path.join(settings.TEMP_STORAGE_PATH, f"temp_{zip_filename}")

    os.makedirs(settings.TEMP_STORAGE_PATH, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for image in images:
            if os.path.exists(image.current_path):
                zipf.write(image.current_path, arcname=image.original_filename)

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=zip_filename,
        background=lambda: os.remove(zip_path) if os.path.exists(zip_path) else None
    )


@router.put("/{image_id}/pin", response_model=ImageResponse)
async def pin_image_endpoint(
    image_id: str,
    payload: PinRequest,
    db: AsyncSession = Depends(get_db),
):
    """Pin or extend a pin (MCP-only entrypoint).

    Re-pinning never shortens an existing longer pin.
    """
    duration = settings.PIN_DEFAULT_DURATION_DAYS if payload.duration_days is None else payload.duration_days
    try:
        image = await ImageService.pin_image(db, image_id, duration_days=duration)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return ImageService.to_response(image)


@router.delete("/{image_id}/pin", response_model=ImageResponse)
async def unpin_image_endpoint(
    image_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Unpin an image. Used by both the MCP unpin tool and the web UI."""
    image = await ImageService.unpin_image(db, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return ImageService.to_response(image)
