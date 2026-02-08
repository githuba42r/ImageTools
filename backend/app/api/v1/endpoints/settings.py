from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings as app_settings
from app.services.settings_service import SettingsService
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/settings", tags=["settings"])


class UpdateModelRequest(BaseModel):
    model_id: str


class SettingsResponse(BaseModel):
    selected_model_id: Optional[str] = None


class DebugEnrolmentInfo(BaseModel):
    openrouter_oauth_callback_url: str
    instance_url: str


class AppConfigResponse(BaseModel):
    session_expiry_days: int
    max_images_per_session: int
    max_upload_size_mb: int
    debug_enrolment: Optional[DebugEnrolmentInfo] = None


@router.get("/app-config", response_model=AppConfigResponse)
async def get_app_config():
    """Get application configuration."""
    debug_info = None
    if app_settings.DEBUG_ENROLMENT:
        debug_info = DebugEnrolmentInfo(
            openrouter_oauth_callback_url=app_settings.openrouter_oauth_callback_url,
            instance_url=app_settings.INSTANCE_URL
        )
    
    return AppConfigResponse(
        session_expiry_days=app_settings.SESSION_EXPIRY_DAYS,
        max_images_per_session=app_settings.MAX_IMAGES_PER_SESSION,
        max_upload_size_mb=app_settings.MAX_UPLOAD_SIZE_MB,
        debug_enrolment=debug_info
    )


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
