"""
Mobile app pairing endpoints
"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.websocket_manager import manager as ws_manager
from app.core.config import settings
from app.services.mobile_service import MobileService
from app.services.image_service import ImageService
from app.schemas.schemas import (
    MobileAppPairingCreate,
    MobileAppPairingResponse,
    QRCodeDataResponse,
    ValidateSecretRequest,
    ValidateSecretResponse,
    MobileImageUploadRequest,
    MobileImageUploadResponse,
    RefreshSecretRequest,
    RefreshSecretResponse,
    ValidateAuthRequest,
    ValidateAuthResponse,
    PairedDeviceInfo
)

router = APIRouter()


@router.post("/pairings", response_model=MobileAppPairingResponse)
async def create_pairing(
    pairing_data: MobileAppPairingCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new mobile app pairing for a session
    
    This endpoint is called when the user wants to generate a QR code
    for linking their mobile device
    """
    try:
        pairing = await MobileService.create_pairing(
            db=db,
            session_id=pairing_data.session_id,
            device_name=pairing_data.device_name
        )
        return pairing
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create pairing: {str(e)}")


@router.get("/pairings/{pairing_id}", response_model=MobileAppPairingResponse)
async def get_pairing(
    pairing_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific pairing by ID
    """
    pairing = await MobileService.get_pairing_by_id(db, pairing_id)
    if not pairing:
        raise HTTPException(status_code=404, detail="Pairing not found")
    return pairing


@router.get("/pairings/qr-data/{pairing_id}", response_model=QRCodeDataResponse)
async def get_qr_code_data(
    pairing_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get QR code data for a pairing
    
    Returns the data that should be encoded in the QR code:
    - Instance URL (derived from request origin)
    - Shared secret (single-use, 2-minute timeout)
    - Pairing ID
    - Session ID
    """
    pairing = await MobileService.get_pairing_by_id(db, pairing_id)
    if not pairing or not pairing.is_active:
        raise HTTPException(status_code=404, detail="Pairing not found or inactive")
    
    # Check if pairing has expired or been used
    if pairing.used:
        raise HTTPException(status_code=410, detail="Pairing secret already used")
    
    if pairing.expires_at and pairing.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Pairing expired")
    
    # Use the configured INSTANCE_URL for mobile devices
    # This must be set to an externally accessible URL (e.g., http://10.0.1.97:8000)
    instance_url = settings.INSTANCE_URL
    
    return QRCodeDataResponse(
        instance_url=instance_url,
        shared_secret=pairing.shared_secret,
        pairing_id=pairing.id,
        session_id=pairing.session_id
    )


@router.get("/pairings/session/{session_id}", response_model=List[MobileAppPairingResponse])
async def get_session_pairings(
    session_id: str,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get all pairings for a session
    """
    pairings = await MobileService.get_session_pairings(
        db=db,
        session_id=session_id,
        active_only=active_only
    )
    return pairings


@router.delete("/pairings/{pairing_id}")
async def delete_pairing(
    pairing_id: str,
    db: Session = Depends(get_db)
):
    """
    Deactivate a pairing
    """
    success = await MobileService.deactivate_pairing(db, pairing_id)
    if not success:
        raise HTTPException(status_code=404, detail="Pairing not found")
    return {"message": "Pairing deactivated successfully"}


@router.post("/pairings/session/{session_id}/revoke-all")
async def revoke_all_pairings(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Revoke all pairings for a session
    """
    count = await MobileService.revoke_all_session_pairings(db, session_id)
    return {"message": f"Revoked {count} pairing(s)"}


@router.post("/upload", response_model=MobileImageUploadResponse)
async def upload_image_from_mobile(
    long_term_secret: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload an image from a mobile device using long-term secret authentication
    
    This endpoint is used by the Android app to upload images shared to it.
    Authentication is done via the long_term_secret obtained after QR code pairing.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[MOBILE UPLOAD] Received upload request, filename: {file.filename}")
    
    # Validate long-term secret and get pairing
    pairing = await MobileService.validate_long_term_secret(db, long_term_secret)
    if not pairing:
        logger.error("[MOBILE UPLOAD] Invalid or expired long-term secret")
        raise HTTPException(status_code=401, detail="Invalid or expired long-term secret")
    
    logger.info(f"[MOBILE UPLOAD] Valid pairing found for session: {pairing.session_id}")
    
    # Upload image using the session from the pairing
    try:
        # Save uploaded image using ImageService
        image = await ImageService.save_uploaded_image(
            db=db,
            session_id=pairing.session_id,
            filename=file.filename or "image.jpg",
            file=file.file
        )
        
        # Broadcast new_image event to all WebSocket clients in this session
        await ws_manager.broadcast_to_session(
            session_id=pairing.session_id,
            message={
                "type": "new_image",
                "image_id": image.id,
                "source": "mobile"
            }
        )
        
        # Get instance URL for building URLs
        # Use configured INSTANCE_URL from settings
        instance_url = settings.INSTANCE_URL
        base_url = f"{instance_url}/api/v1"
        
        return MobileImageUploadResponse(
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
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


@router.post("/validate-secret", response_model=ValidateSecretResponse)
async def validate_shared_secret(
    request: ValidateSecretRequest,
    db: Session = Depends(get_db)
):
    """
    Validate initial shared secret and exchange for long-term authorization
    
    Called when mobile app scans QR code. Returns long-term and refresh secrets
    for ongoing authentication.
    """
    pairing = await MobileService.validate_and_exchange_secrets(db, request.shared_secret)
    if not pairing:
        raise HTTPException(status_code=401, detail="Invalid or expired shared secret")
    
    return ValidateSecretResponse(
        valid=True,
        pairing_id=pairing.id,
        session_id=pairing.session_id,
        device_name=pairing.device_name,
        long_term_secret=pairing.long_term_secret,
        refresh_secret=pairing.refresh_secret,
        long_term_expires_at=pairing.long_term_expires_at,
        refresh_expires_at=pairing.refresh_expires_at
    )


@router.post("/refresh-secret", response_model=RefreshSecretResponse)
async def refresh_secret(
    request: RefreshSecretRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh/renew a long-term secret using refresh secret
    
    Can be used up to 90 days after long-term secret expires
    (within the 180-day refresh secret validity period)
    """
    pairing = await MobileService.refresh_long_term_secret(db, request.refresh_secret)
    if not pairing:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh secret")
    
    return RefreshSecretResponse(
        long_term_secret=pairing.long_term_secret,
        long_term_expires_at=pairing.long_term_expires_at
    )


@router.post("/validate-auth", response_model=ValidateAuthResponse)
async def validate_auth(
    request: ValidateAuthRequest,
    db: Session = Depends(get_db)
):
    """
    Validate current authentication status
    
    Used by Android app to check if long-term secret is still valid
    and whether it needs refresh soon
    """
    pairing = await MobileService.validate_long_term_secret(db, request.long_term_secret)
    if not pairing:
        return ValidateAuthResponse(
            valid=False,
            needs_refresh=False
        )
    
    # Check if needs refresh (within 7 days of expiration)
    needs_refresh = False
    if pairing.long_term_expires_at:
        days_until_expiry = (pairing.long_term_expires_at - datetime.utcnow()).days
        needs_refresh = days_until_expiry <= 7
    
    return ValidateAuthResponse(
        valid=True,
        expires_at=pairing.long_term_expires_at,
        needs_refresh=needs_refresh
    )


@router.get("/pairings/session/{session_id}/list", response_model=List[PairedDeviceInfo])
async def list_paired_devices(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    List all paired devices for a session
    
    Returns only active pairings with long-term secrets.
    Used by web UI for device management.
    """
    pairings = await MobileService.get_session_pairings(
        db=db,
        session_id=session_id,
        active_only=True
    )
    
    # Filter to only pairings that have completed initial exchange
    # (have long_term_secret populated)
    active_pairings = [
        p for p in pairings 
        if p.long_term_secret and p.long_term_expires_at
    ]
    
    return [
        PairedDeviceInfo(
            id=p.id,
            device_name=p.device_name,
            created_at=p.created_at,
            last_used_at=p.last_used_at,
            long_term_expires_at=p.long_term_expires_at,
            is_active=p.is_active
        )
        for p in active_pairings
    ]
