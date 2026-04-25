from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.mcp_token_service import McpTokenService
from app.schemas.mcp_token import (
    McpTokenCreate,
    McpTokenCreateResponse,
    McpTokenInfo,
)

router = APIRouter(prefix="/users/{user_id}/mcp-tokens", tags=["mcp-tokens"])


@router.post("", response_model=McpTokenCreateResponse)
async def create_mcp_token(
    user_id: str,
    payload: McpTokenCreate,
    db: AsyncSession = Depends(get_db),
):
    if not payload.label.strip():
        raise HTTPException(status_code=400, detail="label is required")
    token, row = await McpTokenService.create(db, user_id, payload.label.strip())
    return McpTokenCreateResponse(
        id=row.id, label=row.label, token=token, created_at=row.created_at
    )


@router.get("", response_model=list[McpTokenInfo])
async def list_mcp_tokens(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    rows = await McpTokenService.list_for_user(db, user_id)
    return [
        McpTokenInfo(
            id=r.id,
            label=r.label,
            created_at=r.created_at,
            last_used_at=r.last_used_at,
        )
        for r in rows
    ]


@router.delete("/{token_id}")
async def revoke_mcp_token(
    user_id: str,
    token_id: str,
    db: AsyncSession = Depends(get_db),
):
    ok = await McpTokenService.revoke(db, token_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="token not found or already revoked")
    return {"status": "revoked"}


whoami_router = APIRouter(prefix="/mcp-tokens", tags=["mcp-tokens"])


@whoami_router.get("/whoami")
async def whoami(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a bearer token to its owning user_id. Used by the stdio MCP
    transport to identify which user to fetch images for."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="bearer token required")
    token = authorization.split(" ", 1)[1]
    user_id = await McpTokenService.validate(db, token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="invalid or revoked token")
    return {"user_id": user_id}
