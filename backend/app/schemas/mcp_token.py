from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class McpTokenCreate(BaseModel):
    label: str = Field(min_length=1, max_length=120)


class McpTokenCreateResponse(BaseModel):
    """Response for token creation — includes plaintext token exactly once."""
    id: str
    label: str
    token: str  # plaintext, shown once
    created_at: datetime


class McpTokenInfo(BaseModel):
    """Public info for a token (no plaintext, no hash)."""
    id: str
    label: str
    created_at: datetime
    last_used_at: Optional[datetime]
