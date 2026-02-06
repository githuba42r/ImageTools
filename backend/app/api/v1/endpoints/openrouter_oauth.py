"""
OpenRouter OAuth2 Endpoints

These endpoints proxy the OAuth2 PKCE flow for OpenRouter,
keeping API keys secure on the backend and never exposing them to the frontend.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.services.openrouter_oauth_service import OpenRouterOAuthService

router = APIRouter(tags=["OpenRouter OAuth"])


class OAuthURLRequest(BaseModel):
    """Request to generate OAuth authorization URL"""
    code_challenge: str
    code_challenge_method: str = "S256"


class OAuthURLResponse(BaseModel):
    """OAuth authorization URL response"""
    auth_url: str


class TokenExchangeRequest(BaseModel):
    """Request to exchange authorization code for API key"""
    code: str
    code_verifier: str
    code_challenge_method: str = "S256"


class TokenExchangeResponse(BaseModel):
    """Token exchange response (without exposing the actual key)"""
    success: bool
    key_label: Optional[str] = None
    has_key: bool
    credits_remaining: Optional[float] = None
    credits_total: Optional[float] = None


class KeyStatusResponse(BaseModel):
    """API key status response"""
    has_key: bool
    connected: bool
    key_label: Optional[str] = None
    credits_remaining: Optional[float] = None
    credits_total: Optional[float] = None
    created_at: Optional[str] = None
    last_used_at: Optional[str] = None


class RevokeKeyResponse(BaseModel):
    """Key revocation response"""
    success: bool
    message: str


@router.post("/oauth/authorize-url", response_model=OAuthURLResponse)
async def get_oauth_authorize_url(
    request: OAuthURLRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate OpenRouter OAuth2 authorization URL
    
    The frontend should:
    1. Generate a random code_verifier
    2. Create SHA-256 hash of code_verifier
    3. Base64url encode the hash to get code_challenge
    4. Send code_challenge to this endpoint
    5. Redirect user to the returned auth_url
    
    - **code_challenge**: Base64url-encoded SHA-256 hash of code_verifier
    - **code_challenge_method**: "S256" (recommended) or "plain"
    
    Returns the authorization URL to redirect the user to.
    """
    try:
        service = OpenRouterOAuthService(db)
        auth_url = service.generate_oauth_url(
            code_challenge=request.code_challenge,
            code_challenge_method=request.code_challenge_method
        )
        
        return OAuthURLResponse(auth_url=auth_url)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate OAuth URL: {str(e)}"
        )


@router.post("/oauth/exchange", response_model=TokenExchangeResponse)
async def exchange_oauth_code(
    request: TokenExchangeRequest,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Exchange OAuth authorization code for API key
    
    This endpoint proxies the token exchange with OpenRouter,
    keeping the API key secure on the backend.
    
    After the user authorizes on OpenRouter and is redirected back
    with a 'code' parameter, the frontend should:
    1. Extract the code from the URL
    2. Send the code and original code_verifier to this endpoint
    3. The API key is encrypted and stored server-side
    4. Frontend receives confirmation without seeing the actual key
    
    - **code**: Authorization code from OAuth callback
    - **code_verifier**: Original code verifier (matching the challenge)
    - **code_challenge_method**: Method used in authorization request
    
    Requires X-Session-ID header with current session ID.
    
    Returns success status and key info without exposing the actual key.
    """
    try:
        service = OpenRouterOAuthService(db)
        result = await service.exchange_code_for_key(
            session_id=x_session_id,
            code=request.code,
            code_verifier=request.code_verifier,
            code_challenge_method=request.code_challenge_method
        )
        
        return TokenExchangeResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to exchange code: {str(e)}"
        )


@router.get("/oauth/status", response_model=KeyStatusResponse)
async def get_key_status(
    x_session_id: str = Header(..., alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get OpenRouter API key status for current session
    
    Returns information about the connected API key without
    exposing the actual key value.
    
    Requires X-Session-ID header with current session ID.
    
    Returns:
    - **has_key**: Whether a key is stored for this session
    - **connected**: Whether the key is active and valid
    - **key_label**: Optional label for the key
    - **credits_remaining**: Remaining OpenRouter credits
    - **credits_total**: Total credits limit
    - **created_at**: When key was connected
    - **last_used_at**: When key was last used
    """
    try:
        service = OpenRouterOAuthService(db)
        status_info = await service.get_key_status(x_session_id)
        
        return KeyStatusResponse(**status_info)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get key status: {str(e)}"
        )


@router.post("/oauth/revoke", response_model=RevokeKeyResponse)
async def revoke_key(
    x_session_id: str = Header(..., alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke (disconnect) OpenRouter API key for current session
    
    This deactivates the stored API key, preventing further use.
    The user will need to reconnect to use AI features again.
    
    Requires X-Session-ID header with current session ID.
    
    Returns success status and message.
    """
    try:
        service = OpenRouterOAuthService(db)
        success = await service.revoke_key(x_session_id)
        
        if success:
            return RevokeKeyResponse(
                success=True,
                message="OpenRouter API key disconnected successfully"
            )
        else:
            return RevokeKeyResponse(
                success=False,
                message="No API key found for this session"
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke key: {str(e)}"
        )
