from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.settings_service import SettingsService
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/settings", tags=["settings"])


class UpdateModelRequest(BaseModel):
    model_id: str


class SettingsResponse(BaseModel):
    selected_model_id: Optional[str] = None


@router.get("", response_model=SettingsResponse)
async def get_settings(
    x_session_id: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """Get user settings for the session."""
    settings = await SettingsService.get_settings(db, x_session_id)
    return SettingsResponse(
        selected_model_id=settings.selected_model_id if settings else None
    )


@router.put("/model", response_model=SettingsResponse)
async def update_model(
    request: UpdateModelRequest,
    x_session_id: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """Update the selected AI model."""
    settings = await SettingsService.update_model(db, x_session_id, request.model_id)
    return SettingsResponse(selected_model_id=settings.selected_model_id)
