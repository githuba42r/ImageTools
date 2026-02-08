from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.schemas import SessionCreate, SessionResponse
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new session.
    
    If Authelia headers (Remote-User, Remote-Name) are present in the request,
    they will be automatically extracted and stored in the session.
    """
    # Extract Authelia user information from request state (set by middleware)
    remote_user = getattr(request.state, 'remote_user', None)
    remote_name = getattr(request.state, 'remote_name', None)
    
    # Use Authelia headers if available, otherwise use provided data
    username = remote_user or session_data.username
    display_name = remote_name or session_data.display_name
    
    session = await SessionService.create_session(
        db, 
        session_data.user_id,
        username=username,
        display_name=display_name,
        custom_session_id=session_data.custom_session_id
    )
    return session


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get session details."""
    session = await SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/{session_id}/validate")
async def validate_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Validate if session is active."""
    is_valid = await SessionService.validate_session(db, session_id)
    return {"valid": is_valid}
