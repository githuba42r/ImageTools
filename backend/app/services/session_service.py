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
        """Remove expired sessions and associated data."""
        result = await db.execute(
            delete(Session).where(Session.expires_at < datetime.utcnow())
        )
        await db.commit()
        return result.rowcount
