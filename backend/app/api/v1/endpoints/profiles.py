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
from app.services.user_service import UserService

router = APIRouter()


@router.post("/profiles", response_model=CompressionProfileResponse, status_code=201)
async def create_profile(
    profile_data: CompressionProfileCreate,
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """Create a new compression profile"""
    # Validate user exists
    user = await UserService.get_user(db, x_user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")

    profile = await profile_service.create_profile(db, x_user_id, profile_data)
    return profile


@router.get("/profiles", response_model=List[CompressionProfileResponse])
async def get_profiles(
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get all compression profiles for the current user"""
    # Validate user exists
    user = await UserService.get_user(db, x_user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")

    # Ensure system default profiles exist
    await profile_service.create_system_default_profiles(db)

    profiles = await profile_service.get_profiles(db, x_user_id)
    return profiles


@router.get("/profiles/{profile_id}", response_model=CompressionProfileResponse)
async def get_profile(
    profile_id: str,
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific compression profile"""
    # Validate user exists
    user = await UserService.get_user(db, x_user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")

    profile = await profile_service.get_profile(db, profile_id, x_user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return profile


@router.put("/profiles/{profile_id}", response_model=CompressionProfileResponse)
async def update_profile(
    profile_id: str,
    profile_data: CompressionProfileUpdate,
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """Update a compression profile"""
    # Validate user exists
    user = await UserService.get_user(db, x_user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")

    profile = await profile_service.update_profile(db, profile_id, x_user_id, profile_data)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return profile


@router.delete("/profiles/{profile_id}", status_code=204)
async def delete_profile(
    profile_id: str,
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """Delete a compression profile"""
    # Validate user exists
    user = await UserService.get_user(db, x_user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")

    success = await profile_service.delete_profile(db, profile_id, x_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Profile not found")

    return None
