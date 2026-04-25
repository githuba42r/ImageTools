from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.tag_service import TagService

router = APIRouter(prefix="/users/{user_id}/tags", tags=["tags"])


@router.get("")
async def list_user_tags(user_id: str, db: AsyncSession = Depends(get_db)):
    """List distinct tags this user has used, ordered by most recent use."""
    return await TagService.list_user_tags(db, user_id)
