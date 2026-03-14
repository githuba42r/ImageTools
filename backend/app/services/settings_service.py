import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import UserSettings
from typing import Optional


class SettingsService:
    @staticmethod
    async def get_settings(db: AsyncSession, user_id: str) -> Optional[UserSettings]:
        """Get user settings for a user."""
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        return result.scalars().first()
    
    @staticmethod
    async def update_model(db: AsyncSession, user_id: str, model_id: str) -> UserSettings:
        """Update the selected AI model for a user."""
        # Try to get existing settings
        settings = await SettingsService.get_settings(db, user_id)
        
        if settings:
            # Update existing
            settings.selected_model_id = model_id
        else:
            # Create new
            settings = UserSettings(
                id=str(uuid.uuid4()),
                user_id=user_id,
                selected_model_id=model_id
            )
            db.add(settings)
        
        await db.commit()
        await db.refresh(settings)
        return settings
