"""Personal access token lifecycle for MCP clients."""
import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import McpAuthorization

TOKEN_PREFIX = "imt_"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _generate_token() -> str:
    # 32 random bytes → 43 url-safe chars; prefix makes the token self-describing
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


class McpTokenService:
    @staticmethod
    async def create(
        db: AsyncSession, user_id: str, label: str
    ) -> tuple[str, McpAuthorization]:
        """Create a new token. Returns (plaintext_token, row). Plaintext is
        shown to the user once and not stored anywhere else."""
        token = _generate_token()
        row = McpAuthorization(
            id=str(uuid.uuid4()),
            user_id=user_id,
            token_hash=_hash(token),
            label=label,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return token, row

    @staticmethod
    async def validate(db: AsyncSession, token: str) -> Optional[str]:
        """Return user_id if the token is valid and not revoked. Updates
        last_used_at as a side-effect."""
        if not token or not token.startswith(TOKEN_PREFIX):
            return None
        result = await db.execute(
            select(McpAuthorization).where(
                McpAuthorization.token_hash == _hash(token),
                McpAuthorization.revoked_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        await db.execute(
            update(McpAuthorization)
            .where(McpAuthorization.id == row.id)
            .values(last_used_at=datetime.now(timezone.utc))
        )
        await db.commit()
        return row.user_id

    @staticmethod
    async def revoke(db: AsyncSession, token_id: str, user_id: str) -> bool:
        """Revoke a token belonging to user_id. Returns True if revoked."""
        result = await db.execute(
            update(McpAuthorization)
            .where(
                McpAuthorization.id == token_id,
                McpAuthorization.user_id == user_id,
                McpAuthorization.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def list_for_user(
        db: AsyncSession, user_id: str
    ) -> list[McpAuthorization]:
        """List all non-revoked tokens for a user, newest first."""
        result = await db.execute(
            select(McpAuthorization)
            .where(
                McpAuthorization.user_id == user_id,
                McpAuthorization.revoked_at.is_(None),
            )
            .order_by(McpAuthorization.created_at.desc())
        )
        return list(result.scalars().all())
