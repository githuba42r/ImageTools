from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.schemas.schemas import BackgroundRemovalRequest, BackgroundRemovalResponse
from app.services.background_service import BackgroundRemovalService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{image_id}/remove-background", response_model=BackgroundRemovalResponse)
async def remove_background(
    image_id: str,
    request: BackgroundRemovalRequest,
    db: Session = Depends(get_db)
):
    """
    Remove background from an image using rembg
    
    - **image_id**: ID of the image to process
    - **alpha_matting**: Use alpha matting for better edge quality (slower)
    - **alpha_matting_foreground_threshold**: Foreground threshold (0-255)
    - **alpha_matting_background_threshold**: Background threshold (0-255)
    - **model**: rembg model to use (u2net, u2net_human_seg, isnet-general-use, isnet-anime)
    
    Returns the processed image as PNG with transparency.
    Adds operation to undo history.
    """
    try:
        # Create service with specified model
        service = BackgroundRemovalService(
            db=db,
            model=request.model or "u2net"
        )
        
        # Remove background
        result = await service.remove_background(
            image_id=image_id,
            alpha_matting=request.alpha_matting,
            alpha_matting_foreground_threshold=request.alpha_matting_foreground_threshold,
            alpha_matting_background_threshold=request.alpha_matting_background_threshold,
        )
        
        return BackgroundRemovalResponse(**result)
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Background removal failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Background removal failed: {str(e)}")


@router.get("/models", response_model=dict)
async def get_available_models():
    """
    Get list of available rembg models
    
    Returns a dictionary mapping model names to descriptions.
    """
    return BackgroundRemovalService.get_available_models()
