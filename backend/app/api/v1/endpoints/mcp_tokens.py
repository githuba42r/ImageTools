from fastapi import APIRouter, Depends, HTTPException
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
