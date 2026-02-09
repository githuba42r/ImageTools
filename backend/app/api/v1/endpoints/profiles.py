"""
Compression Profile API Endpoints
Allows users to create, read, update, and delete custom compression profiles
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.schemas.schemas import (
    CompressionProfileCreate,
    CompressionProfileUpdate,
    CompressionProfileResponse
)
from app.services import profile_service
from app.services.session_service import SessionService

router = APIRouter()


@router.post("/profiles", response_model=CompressionProfileResponse, status_code=201)
async def create_profile(
    profile_data: CompressionProfileCreate,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db)
):
    """Create a new compression profile"""
    # Validate session exists
    session = await SessionService.get_session(db, x_session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    profile = await profile_service.create_profile(db, x_session_id, profile_data)
    return profile


@router.get("/profiles", response_model=List[CompressionProfileResponse])
async def get_profiles(
    x_session_id: str = Header(..., alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get all compression profiles for the current session"""
    # Validate session exists
    session = await SessionService.get_session(db, x_session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Ensure system default profiles exist
    await profile_service.create_system_default_profiles(db)
    
    profiles = await profile_service.get_profiles(db, x_session_id)
    return profiles


@router.get("/profiles/{profile_id}", response_model=CompressionProfileResponse)
async def get_profile(
    profile_id: str,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific compression profile"""
    # Validate session exists
    session = await SessionService.get_session(db, x_session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    profile = await profile_service.get_profile(db, profile_id, x_session_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return profile


@router.put("/profiles/{profile_id}", response_model=CompressionProfileResponse)
async def update_profile(
    profile_id: str,
    profile_data: CompressionProfileUpdate,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db)
):
    """Update a compression profile"""
    # Validate session exists
    session = await SessionService.get_session(db, x_session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    profile = await profile_service.update_profile(db, profile_id, x_session_id, profile_data)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return profile


@router.delete("/profiles/{profile_id}", status_code=204)
async def delete_profile(
    profile_id: str,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db)
):
    """Delete a compression profile"""
    # Validate session exists
    session = await SessionService.get_session(db, x_session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    success = await profile_service.delete_profile(db, profile_id, x_session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return None
