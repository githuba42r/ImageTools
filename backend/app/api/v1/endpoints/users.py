from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.schemas import UserCreate, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse)
async def get_or_create_user(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    remote_user = getattr(request.state, 'remote_user', None)
    remote_name = getattr(request.state, 'remote_name', None)
    username = remote_user or user_data.username
    display_name = remote_name or user_data.display_name
    user = await UserService.get_or_create_user(db, username=username, display_name=display_name)
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    user = await UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/{user_id}/validate")
async def validate_user(user_id: str, db: AsyncSession = Depends(get_db)):
    valid = await UserService.validate_user(db, user_id)
    return {"valid": valid, "user_id": user_id}
