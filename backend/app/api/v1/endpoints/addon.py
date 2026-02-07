"""
Browser addon authorization and screenshot upload endpoints
"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.websocket_manager import manager as ws_manager
from app.core.config import settings
from app.services.addon_service import AddonService
from app.services.image_service import ImageService
from app.schemas.schemas import (
    AddonAuthorizationCreate,
    AddonAuthorizationResponse,
    AddonTokenExchangeRequest,
    AddonTokenExchangeResponse,
    AddonRefreshTokenRequest,
    AddonRefreshTokenResponse,
    AddonValidateTokenRequest,
    AddonValidateTokenResponse,
    AddonScreenshotUploadResponse,
    ConnectedAddonInfo
)

router = APIRouter()


@router.post("/authorize", response_model=AddonAuthorizationResponse)
async def create_authorization(
    auth_data: AddonAuthorizationCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Create a new browser addon authorization
    
    This endpoint is called when the user clicks "Connect Addon" in the web UI.
    It generates an authorization code and registration URL for the addon.
    """
    try:
        authorization = await AddonService.create_authorization(
            db=db,
            session_id=auth_data.session_id,
            browser_name=auth_data.browser_name,
            addon_identifier=auth_data.addon_identifier
        )
        
        # Build registration URL using configured instance URL
        instance_url = settings.INSTANCE_URL
        registration_url = AddonService.build_registration_url(authorization, instance_url)
        
        return AddonAuthorizationResponse(
            id=authorization.id,
            session_id=authorization.session_id,
            browser_name=authorization.browser_name,
            authorization_code=authorization.authorization_code,
            registration_url=registration_url,
            code_expires_at=authorization.code_expires_at,
            is_active=authorization.is_active,
            created_at=authorization.created_at
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create authorization: {str(e)}")


@router.post("/token", response_model=AddonTokenExchangeResponse)
async def exchange_token(
    request: AddonTokenExchangeRequest,
    db: Session = Depends(get_db)
):
    """
    Exchange authorization code for access and refresh tokens
    
    Called when addon first connects with the registration URL.
    Returns long-term tokens for ongoing authentication.
    """
    authorization = await AddonService.exchange_code_for_tokens(db, request.authorization_code)
    if not authorization:
        raise HTTPException(status_code=401, detail="Invalid or expired authorization code")
    
    # Get instance URL for response
    instance_url = settings.INSTANCE_URL
    
    return AddonTokenExchangeResponse(
        access_token=authorization.access_token,
        refresh_token=authorization.refresh_token,
        access_expires_at=authorization.access_expires_at,
        refresh_expires_at=authorization.refresh_expires_at,
        session_id=authorization.session_id,
        instance_url=instance_url
    )


@router.post("/refresh", response_model=AddonRefreshTokenResponse)
async def refresh_token(
    request: AddonRefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh/renew an access token using refresh token
    
    Can be used within the 90-day refresh token validity period
    """
    authorization = await AddonService.refresh_access_token(db, request.refresh_token)
    if not authorization:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    return AddonRefreshTokenResponse(
        access_token=authorization.access_token,
        access_expires_at=authorization.access_expires_at
    )


@router.post("/validate", response_model=AddonValidateTokenResponse)
async def validate_token(
    request: AddonValidateTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Validate current access token status
    
    Used by addon to check if access token is still valid
    and whether it needs refresh soon
    """
    authorization = await AddonService.validate_access_token(db, request.access_token)
    if not authorization:
        return AddonValidateTokenResponse(
            valid=False,
            needs_refresh=False
        )
    
    # Check if needs refresh (within 3 days of expiration)
    needs_refresh = False
    if authorization.access_expires_at:
        days_until_expiry = (authorization.access_expires_at - datetime.utcnow()).days
        needs_refresh = days_until_expiry <= 3
    
    return AddonValidateTokenResponse(
        valid=True,
        expires_at=authorization.access_expires_at,
        needs_refresh=needs_refresh,
        session_id=authorization.session_id
    )


@router.post("/upload", response_model=AddonScreenshotUploadResponse)
async def upload_screenshot(
    file: UploadFile = File(...),
    authorization: str = Header(..., description="Bearer token"),
    db: Session = Depends(get_db)
):
    """
    Upload a screenshot from browser addon using access token authentication
    
    This endpoint is used by the browser addon to upload screenshots.
    Authentication is done via the Authorization header with Bearer token.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[ADDON UPLOAD] Received screenshot upload, filename: {file.filename}")
    
    # Extract token from "Bearer <token>" format
    access_token = authorization
    if authorization.startswith("Bearer "):
        access_token = authorization[7:]
    
    # Validate access token and get authorization
    auth = await AddonService.validate_access_token(db, access_token)
    if not auth:
        logger.error("[ADDON UPLOAD] Invalid or expired access token")
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    
    logger.info(f"[ADDON UPLOAD] Valid authorization found for session: {auth.session_id}")
    
    # Upload screenshot using the session from the authorization
    try:
        # Save uploaded image using ImageService
        image = await ImageService.save_uploaded_image(
            db=db,
            session_id=auth.session_id,
            filename=file.filename or "screenshot.png",
            file=file.file
        )
        
        # Broadcast new_image event to all WebSocket clients in this session
        await ws_manager.broadcast_to_session(
            session_id=auth.session_id,
            message={
                "type": "new_image",
                "image_id": image.id,
                "source": "addon"
            }
        )
        
        # Get instance URL for building URLs
        instance_url = settings.INSTANCE_URL
        base_url = f"{instance_url}/api/v1"
        
        return AddonScreenshotUploadResponse(
            image_id=image.id,
            filename=image.original_filename,
            size=image.current_size,
            width=image.width,
            height=image.height,
            format=image.format,
            thumbnail_url=f"{base_url}/images/{image.id}/thumbnail",
            image_url=f"{base_url}/images/{image.id}/current",
            uploaded_at=image.created_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[ADDON UPLOAD] Failed to upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload screenshot: {str(e)}")


@router.delete("/authorizations/{auth_id}")
async def revoke_authorization(
    auth_id: str,
    db: Session = Depends(get_db)
):
    """
    Revoke an addon authorization
    """
    success = await AddonService.revoke_authorization(db, auth_id)
    if not success:
        raise HTTPException(status_code=404, detail="Authorization not found")
    return {"message": "Authorization revoked successfully"}


@router.post("/authorizations/session/{session_id}/revoke-all")
async def revoke_all_authorizations(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Revoke all addon authorizations for a session
    """
    count = await AddonService.revoke_all_session_authorizations(db, session_id)
    return {"message": f"Revoked {count} authorization(s)"}


@router.get("/authorizations/session/{session_id}/list", response_model=List[ConnectedAddonInfo])
async def list_connected_addons(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    List all connected addons for a session
    
    Returns only active authorizations with access tokens.
    Used by web UI for addon management.
    """
    authorizations = await AddonService.get_session_authorizations(
        db=db,
        session_id=session_id,
        active_only=True
    )
    
    # Filter to only authorizations that have completed token exchange
    # (have access_token populated)
    active_authorizations = [
        a for a in authorizations 
        if a.access_token and a.access_expires_at
    ]
    
    return [
        ConnectedAddonInfo(
            id=a.id,
            browser_name=a.browser_name,
            created_at=a.created_at,
            last_used_at=a.last_used_at,
            access_expires_at=a.access_expires_at,
            is_active=a.is_active
        )
        for a in active_authorizations
    ]
