import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.models import Session
from app.core.config import settings


class SessionService:
    @staticmethod
    async def create_session(
        db: AsyncSession, 
        user_id: str = None, 
        username: str = None,
        display_name: str = None,
        custom_session_id: str = None
    ) -> Session:
        """Create a new session with optional Authelia user information."""
        # Use custom session ID if provided (for testing), otherwise generate UUID
        session_id = custom_session_id if custom_session_id else str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(days=settings.SESSION_EXPIRY_DAYS)
        
        # Check if session with this ID already exists
        existing = await SessionService.get_session(db, session_id)
        if existing:
            # Update expiry time and user info for existing session
            existing.expires_at = expires_at
            if user_id:
                existing.user_id = user_id
            if username:
                existing.username = username
            if display_name:
                existing.display_name = display_name
            await db.commit()
            await db.refresh(existing)
            return existing
        
        # Create new session
        session = Session(
            id=session_id,
            user_id=user_id,
            username=username,
            display_name=display_name,
            expires_at=expires_at
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        # Ensure system default compression profiles exist (one-time global creation)
        from app.services import profile_service
        await profile_service.create_system_default_profiles(db)
        
        return session
    
    @staticmethod
    async def get_session(db: AsyncSession, session_id: str) -> Session:
        """Get session by ID."""
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def validate_session(db: AsyncSession, session_id: str) -> bool:
        """Check if session exists and is not expired."""
        session = await SessionService.get_session(db, session_id)
        if not session:
            return False
        if session.expires_at < datetime.utcnow():
            return False
        return True
    
    @staticmethod
    async def cleanup_expired_sessions(db: AsyncSession) -> int:
        """Remove expired sessions and associated data, including files on disk."""
        import os
        from pathlib import Path
        from app.models.models import Image
        from app.core.config import settings
        
        # Get all expired sessions first to fetch their images
        result = await db.execute(
            select(Session).where(Session.expires_at < datetime.utcnow())
        )
        expired_sessions = result.scalars().all()
        
        if not expired_sessions:
            return 0
        
        session_ids = [s.id for s in expired_sessions]
        deleted_count = len(session_ids)
        
        # Get all images associated with expired sessions to delete their files
        image_result = await db.execute(
            select(Image).where(Image.session_id.in_(session_ids))
        )
        images_to_delete = image_result.scalars().all()
        
        # Delete image files and thumbnails from disk
        storage_dir = Path(settings.STORAGE_DIR)
        for image in images_to_delete:
            try:
                # Delete main image file
                if image.current_path and os.path.exists(image.current_path):
                    os.remove(image.current_path)
                    
                # Delete thumbnail file
                if image.thumbnail_path and os.path.exists(image.thumbnail_path):
                    os.remove(image.thumbnail_path)
                    
                # Clean up history files (if they exist in a subdirectory)
                # History files are typically stored in storage/<image_id>/history/
                image_history_dir = storage_dir / image.id / "history"
                if image_history_dir.exists() and image_history_dir.is_dir():
                    for history_file in image_history_dir.glob("*"):
                        if history_file.is_file():
                            os.remove(history_file)
                    # Remove history directory if empty
                    try:
                        image_history_dir.rmdir()
                    except OSError:
                        pass  # Directory not empty, that's okay
                
                # Remove image directory if it exists and is empty
                image_dir = storage_dir / image.id
                if image_dir.exists() and image_dir.is_dir():
                    try:
                        image_dir.rmdir()
                    except OSError:
                        pass  # Directory not empty, that's okay
                        
            except Exception as e:
                # Log error but continue cleanup
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error deleting files for image {image.id}: {e}")
        
        # Delete sessions from database (CASCADE will handle related records)
        await db.execute(
            delete(Session).where(Session.id.in_(session_ids))
        )
        await db.commit()
        
        return deleted_count
