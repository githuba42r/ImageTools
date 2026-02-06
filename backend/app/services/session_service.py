import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.models import Session
from app.core.config import settings


class SessionService:
    @staticmethod
    async def create_session(db: AsyncSession, user_id: str = None) -> Session:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(days=settings.SESSION_EXPIRY_DAYS)
        
        session = Session(
            id=session_id,
            user_id=user_id,
            expires_at=expires_at
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
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
