import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import UserSettings
from typing import Optional


class SettingsService:
    @staticmethod
    async def get_settings(db: AsyncSession, session_id: str) -> Optional[UserSettings]:
        """Get user settings for a session."""
        result = await db.execute(
            select(UserSettings).where(UserSettings.session_id == session_id)
        )
        return result.scalars().first()
    
    @staticmethod
    async def update_model(db: AsyncSession, session_id: str, model_id: str) -> UserSettings:
        """Update the selected AI model for a session."""
        # Try to get existing settings
        settings = await SettingsService.get_settings(db, session_id)
        
        if settings:
            # Update existing
            settings.selected_model_id = model_id
        else:
            # Create new
            settings = UserSettings(
                id=str(uuid.uuid4()),
                session_id=session_id,
                selected_model_id=model_id
            )
            db.add(settings)
        
        await db.commit()
        await db.refresh(settings)
        return settings
