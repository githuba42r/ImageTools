"""
Profile Service
Handles CRUD operations for custom compression profiles
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, or_
from app.models.models import CompressionProfile
from app.schemas.schemas import CompressionProfileCreate, CompressionProfileUpdate
from app.core.config import settings
from typing import List, Optional
import uuid


def get_default_profiles_data() -> List[dict]:
    """Get default profile configurations based on built-in presets."""
    return [
        {
            "name": "Email Optimized",
            "max_width": settings.EMAIL_MAX_WIDTH,
            "max_height": settings.EMAIL_MAX_HEIGHT,
            "quality": settings.EMAIL_QUALITY,
            "target_size_kb": settings.EMAIL_TARGET_SIZE_KB,
            "format": settings.EMAIL_FORMAT,
            "retain_aspect_ratio": True,
            "is_default": False,
            "system_default": True
        },
        {
            "name": "Web Standard",
            "max_width": settings.WEB_MAX_WIDTH,
            "max_height": settings.WEB_MAX_HEIGHT,
            "quality": settings.WEB_QUALITY,
            "target_size_kb": settings.WEB_TARGET_SIZE_KB,
            "format": settings.WEB_FORMAT,
            "retain_aspect_ratio": True,
            "is_default": True,
            "system_default": True
        },
        {
            "name": "Web High Quality",
            "max_width": settings.WEB_HQ_MAX_WIDTH,
            "max_height": settings.WEB_HQ_MAX_HEIGHT,
            "quality": settings.WEB_HQ_QUALITY,
            "target_size_kb": settings.WEB_HQ_TARGET_SIZE_KB,
            "format": settings.WEB_HQ_FORMAT,
            "retain_aspect_ratio": True,
            "is_default": False,
            "system_default": True
        }
    ]


async def create_system_default_profiles(db: AsyncSession) -> List[CompressionProfile]:
    """Create system-wide default profiles (one-time setup)."""
    # Check if system defaults already exist
    result = await db.execute(
        select(CompressionProfile).where(CompressionProfile.system_default == True)
    )
    existing = result.scalars().all()
    
    if existing:
        return list(existing)
    
    # Create system default profiles
    default_profiles_data = get_default_profiles_data()
    created_profiles = []
    
    try:
        for profile_data in default_profiles_data:
            profile = CompressionProfile(
                id=str(uuid.uuid4()),
                session_id=None,  # System defaults have no session
                **profile_data
            )
            db.add(profile)
            created_profiles.append(profile)
        
        await db.commit()
        
        for profile in created_profiles:
            await db.refresh(profile)
        
        return created_profiles
    except Exception as e:
        await db.rollback()
        # If we got an integrity error about session_id NOT NULL,
        # it means the migration hasn't completed yet
        if "NOT NULL constraint failed: compression_profiles.session_id" in str(e):
            # Return empty list - migration will create them later
            return []
        raise


async def create_default_profiles(db: AsyncSession, session_id: str) -> List[CompressionProfile]:
    """
    Deprecated: System defaults are now global, not per-session.
    This function is kept for backward compatibility.
    """
    # Just ensure system defaults exist
    return await create_system_default_profiles(db)


async def copy_profile_for_user(
    db: AsyncSession,
    system_profile_id: str,
    session_id: str,
    new_name: Optional[str] = None
) -> Optional[CompressionProfile]:
    """Create a user copy of a system default profile."""
    # Get the system profile
    result = await db.execute(
        select(CompressionProfile)
        .where(CompressionProfile.id == system_profile_id)
        .where(CompressionProfile.system_default == True)
    )
    system_profile = result.scalars().first()
    
    if not system_profile:
        return None
    
    # Create user copy
    user_profile = CompressionProfile(
        id=str(uuid.uuid4()),
        session_id=session_id,
        name=new_name or system_profile.name,
        max_width=system_profile.max_width,
        max_height=system_profile.max_height,
        quality=system_profile.quality,
        target_size_kb=system_profile.target_size_kb,
        format=system_profile.format,
        retain_aspect_ratio=system_profile.retain_aspect_ratio,
        is_default=False,
        system_default=False
    )
    
    db.add(user_profile)
    await db.commit()
    await db.refresh(user_profile)
    
    return user_profile


async def create_profile(
    db: AsyncSession,
    session_id: str,
    profile_data: CompressionProfileCreate
) -> CompressionProfile:
    """Create a new compression profile"""
    # If this profile is set as default, unset any existing default profiles
    if profile_data.is_default:
        await db.execute(
            update(CompressionProfile)
            .where(CompressionProfile.session_id == session_id)
            .where(CompressionProfile.is_default == True)
            .values(is_default=False)
        )
    
    profile = CompressionProfile(
        id=str(uuid.uuid4()),
        session_id=session_id,
        name=profile_data.name,
        max_width=profile_data.max_width,
        max_height=profile_data.max_height,
        quality=profile_data.quality,
        target_size_kb=profile_data.target_size_kb,
        format=profile_data.format,
        is_default=profile_data.is_default
    )
    
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    
    return profile


async def get_profile(db: AsyncSession, profile_id: str, session_id: str) -> Optional[CompressionProfile]:
    """Get a specific profile by ID (user profile or system default)"""
    result = await db.execute(
        select(CompressionProfile)
        .where(CompressionProfile.id == profile_id)
        .where(
            or_(
                CompressionProfile.session_id == session_id,
                CompressionProfile.system_default == True
            )
        )
    )
    return result.scalars().first()


async def get_profiles(db: AsyncSession, session_id: str) -> List[CompressionProfile]:
    """Get all profiles for a session (includes system defaults and user profiles)"""
    result = await db.execute(
        select(CompressionProfile)
        .where(
            or_(
                CompressionProfile.session_id == session_id,
                CompressionProfile.system_default == True
            )
        )
        .order_by(CompressionProfile.system_default.desc(), CompressionProfile.is_default.desc(), CompressionProfile.name)
    )
    return list(result.scalars().all())


async def get_default_profile(db: AsyncSession, session_id: str) -> Optional[CompressionProfile]:
    """Get the default profile for a session"""
    result = await db.execute(
        select(CompressionProfile)
        .where(CompressionProfile.session_id == session_id)
        .where(CompressionProfile.is_default == True)
    )
    return result.scalars().first()


async def update_profile(
    db: AsyncSession,
    profile_id: str,
    session_id: str,
    profile_data: CompressionProfileUpdate
) -> Optional[CompressionProfile]:
    """
    Update an existing profile.
    If trying to edit a system default, creates a user copy instead.
    """
    profile = await get_profile(db, profile_id, session_id)
    if not profile:
        return None
    
    # If this is a system default, create a user copy instead of editing
    if profile.system_default:
        # Create a copy with the updated values
        update_data = profile_data.model_dump(exclude_unset=True)
        
        new_profile = CompressionProfile(
            id=str(uuid.uuid4()),
            session_id=session_id,
            name=update_data.get('name', profile.name),
            max_width=update_data.get('max_width', profile.max_width),
            max_height=update_data.get('max_height', profile.max_height),
            quality=update_data.get('quality', profile.quality),
            target_size_kb=update_data.get('target_size_kb', profile.target_size_kb),
            format=update_data.get('format', profile.format),
            retain_aspect_ratio=update_data.get('retain_aspect_ratio', profile.retain_aspect_ratio),
            is_default=update_data.get('is_default', False),
            system_default=False
        )
        
        # If setting as default, unset existing defaults
        if new_profile.is_default:
            await db.execute(
                update(CompressionProfile)
                .where(CompressionProfile.session_id == session_id)
                .where(CompressionProfile.is_default == True)
                .values(is_default=False)
            )
        
        db.add(new_profile)
        await db.commit()
        await db.refresh(new_profile)
        return new_profile
    
    # Regular user profile - update in place
    # If this profile is being set as default, unset any existing default profiles
    if profile_data.is_default:
        await db.execute(
            update(CompressionProfile)
            .where(CompressionProfile.session_id == session_id)
            .where(CompressionProfile.is_default == True)
            .where(CompressionProfile.id != profile_id)
            .values(is_default=False)
        )
    
    # Update fields if provided
    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    await db.commit()
    await db.refresh(profile)
    
    return profile


async def delete_profile(db: AsyncSession, profile_id: str, session_id: str) -> bool:
    """Delete a profile (cannot delete system defaults)"""
    profile = await get_profile(db, profile_id, session_id)
    if not profile:
        return False
    
    # Cannot delete system defaults
    if profile.system_default:
        return False
    
    await db.delete(profile)
    await db.commit()
    
    return True
