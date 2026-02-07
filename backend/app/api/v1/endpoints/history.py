from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel
from app.core.database import get_db
from app.core.config import settings
from app.schemas.schemas import HistoryResponse, UndoResponse
from app.services.history_service import HistoryService
from app.services.image_service import ImageService

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/{image_id}", response_model=List[HistoryResponse])
async def get_history(
    image_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get operation history for an image."""
    # Verify image exists
    image = await ImageService.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    history = await HistoryService.get_image_history(db, image_id)
    
    return [
        HistoryResponse(
            id=h.id,
            image_id=h.image_id,
            operation_type=h.operation_type,
            operation_params=h.operation_params,
            file_size=h.file_size,
            created_at=h.created_at,
            sequence=h.sequence
        )
        for h in history
    ]


@router.post("/{image_id}/undo", response_model=UndoResponse)
async def undo_operation(
    image_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Undo the last operation on an image."""
    # Verify image exists
    image = await ImageService.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Check if undo is available
    can_undo = await HistoryService.can_undo(db, image_id)
    if not can_undo:
        raise HTTPException(status_code=400, detail="No operations to undo")
    
    try:
        revert_path, sequence = await HistoryService.undo_operation(db, image_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Get updated image
    updated_image = await ImageService.get_image(db, image_id)
    
    return UndoResponse(
        image_id=image_id,
        reverted_to_sequence=sequence,
        current_size=updated_image.current_size,
        image_url=f"{settings.API_PREFIX}/images/{image_id}/current"
    )


@router.get("/{image_id}/can-undo")
async def check_can_undo(
    image_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Check if undo is available for an image."""
    can_undo = await HistoryService.can_undo(db, image_id)
    return {"can_undo": can_undo}


class RestoreRequest(BaseModel):
    sequence: int


@router.post("/{image_id}/restore", response_model=UndoResponse)
async def restore_to_sequence(
    image_id: str,
    request: RestoreRequest,
    db: AsyncSession = Depends(get_db)
):
    """Restore image to a specific history sequence."""
    # Verify image exists
    image = await ImageService.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    try:
        restore_path, restore_size = await HistoryService.restore_to_sequence(
            db, image_id, request.sequence
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Get updated image
    updated_image = await ImageService.get_image(db, image_id)
    
    return UndoResponse(
        image_id=image_id,
        reverted_to_sequence=request.sequence,
        current_size=updated_image.current_size,
        image_url=f"{settings.API_PREFIX}/images/{image_id}/current"
    )
