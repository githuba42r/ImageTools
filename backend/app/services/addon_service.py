"""
Service for browser addon authorization and authentication
"""
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select

from app.models.models import BrowserAddonAuthorization, Session as SessionModel
from app.core.config import settings


class AddonService:
    """Service for managing browser addon OAuth2-style authorization"""
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate a cryptographically secure random token"""
        return secrets.token_hex(length)
    
    @staticmethod
    async def create_authorization(
        db: AsyncSession,
        session_id: str,
        browser_name: Optional[str] = None,
        addon_identifier: Optional[str] = None,
        code_expiry_minutes: int = 5
    ) -> BrowserAddonAuthorization:
        """
        Create a new browser addon authorization with short-lived code
        
        Args:
            db: Database session
            session_id: Session ID to link the authorization to
            browser_name: Browser type ("firefox" or "chrome")
            addon_identifier: Optional addon ID
            code_expiry_minutes: Number of minutes until code expires (default 5)
        
        Returns:
            Created BrowserAddonAuthorization object
        """
        # Verify session exists
        result = await db.execute(select(SessionModel).filter(SessionModel.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Generate authorization with 5-minute timeout
        auth_id = str(uuid.uuid4())
        authorization_code = AddonService.generate_secure_token(32)
        code_expires_at = datetime.utcnow() + timedelta(minutes=code_expiry_minutes)
        
        authorization = BrowserAddonAuthorization(
            id=auth_id,
            session_id=session_id,
            browser_name=browser_name,
            addon_identifier=addon_identifier,
            authorization_code=authorization_code,
            code_used=False,
            code_expires_at=code_expires_at,
            is_active=True
        )
        
        db.add(authorization)
        await db.commit()
        await db.refresh(authorization)
        
        return authorization
    
    @staticmethod
    async def exchange_code_for_tokens(
        db: AsyncSession,
        authorization_code: str
    ) -> Optional[BrowserAddonAuthorization]:
        """
        Exchange authorization code for access and refresh tokens
        
        This is called when the addon first connects with the registration URL.
        It validates the short-lived code and generates:
        - access_token (30 days) for screenshot uploads
        - refresh_token (90 days) for renewing access token
        
        Args:
            db: Database session
            authorization_code: Authorization code from registration URL
        
        Returns:
            BrowserAddonAuthorization with tokens, or None if invalid
        """
        result = await db.execute(
            select(BrowserAddonAuthorization).filter(
                and_(
                    BrowserAddonAuthorization.authorization_code == authorization_code,
                    BrowserAddonAuthorization.is_active == True
                )
            )
        )
        authorization = result.scalar_one_or_none()
        
        if not authorization:
            return None
        
        # Check if already used (single-use)
        if authorization.code_used:
            return None
        
        # Check if expired (5-minute timeout)
        if authorization.code_expires_at < datetime.utcnow():
            # Mark as inactive
            authorization.is_active = False
            await db.commit()
            return None
        
        # Generate access and refresh tokens
        authorization.access_token = AddonService.generate_secure_token(32)
        authorization.access_expires_at = datetime.utcnow() + timedelta(days=30)
        authorization.refresh_token = AddonService.generate_secure_token(32)
        authorization.refresh_expires_at = datetime.utcnow() + timedelta(days=90)
        
        # Mark code as used
        authorization.code_used = True
        authorization.last_used_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(authorization)
        
        return authorization
    
    @staticmethod
    async def validate_access_token(
        db: AsyncSession,
        access_token: str
    ) -> Optional[BrowserAddonAuthorization]:
        """
        Validate an access token for screenshot uploads
        
        Args:
            db: Database session
            access_token: Access token for authentication
        
        Returns:
            BrowserAddonAuthorization if valid, None otherwise
        """
        result = await db.execute(
            select(BrowserAddonAuthorization).filter(
                and_(
                    BrowserAddonAuthorization.access_token == access_token,
                    BrowserAddonAuthorization.is_active == True
                )
            )
        )
        authorization = result.scalar_one_or_none()
        
        if not authorization:
            return None
        
        # Check if access token expired
        if authorization.access_expires_at and authorization.access_expires_at < datetime.utcnow():
            return None
        
        # Update last used timestamp
        authorization.last_used_at = datetime.utcnow()
        await db.commit()
        
        return authorization
    
    @staticmethod
    async def refresh_access_token(
        db: AsyncSession,
        refresh_token: str
    ) -> Optional[BrowserAddonAuthorization]:
        """
        Refresh/renew the access token using refresh token
        
        Can be used within the 90-day refresh token validity period
        
        Args:
            db: Database session
            refresh_token: Refresh token for renewing
        
        Returns:
            BrowserAddonAuthorization with new access token, or None if invalid
        """
        result = await db.execute(
            select(BrowserAddonAuthorization).filter(
                and_(
                    BrowserAddonAuthorization.refresh_token == refresh_token,
                    BrowserAddonAuthorization.is_active == True
                )
            )
        )
        authorization = result.scalar_one_or_none()
        
        if not authorization:
            return None
        
        # Check if refresh token expired
        if authorization.refresh_expires_at and authorization.refresh_expires_at < datetime.utcnow():
            # Refresh window closed, authorization no longer renewable
            authorization.is_active = False
            await db.commit()
            return None
        
        # Generate new access token (30 more days)
        authorization.access_token = AddonService.generate_secure_token(32)
        authorization.access_expires_at = datetime.utcnow() + timedelta(days=30)
        authorization.last_used_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(authorization)
        
        return authorization
    
    @staticmethod
    async def get_authorization_by_id(
        db: AsyncSession,
        auth_id: str
    ) -> Optional[BrowserAddonAuthorization]:
        """Get an authorization by ID"""
        result = await db.execute(
            select(BrowserAddonAuthorization).filter(BrowserAddonAuthorization.id == auth_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_session_authorizations(
        db: AsyncSession,
        session_id: str,
        active_only: bool = True
    ) -> list[BrowserAddonAuthorization]:
        """
        Get all addon authorizations for a session
        
        Args:
            db: Database session
            session_id: Session ID
            active_only: Only return active authorizations (default True)
        
        Returns:
            List of authorizations
        """
        query = select(BrowserAddonAuthorization).filter(
            BrowserAddonAuthorization.session_id == session_id
        )
        
        if active_only:
            query = query.filter(BrowserAddonAuthorization.is_active == True)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def revoke_authorization(
        db: AsyncSession,
        auth_id: str
    ) -> bool:
        """
        Revoke an authorization
        
        Args:
            db: Database session
            auth_id: Authorization ID
        
        Returns:
            True if revoked, False if not found
        """
        result = await db.execute(
            select(BrowserAddonAuthorization).filter(BrowserAddonAuthorization.id == auth_id)
        )
        authorization = result.scalar_one_or_none()
        if not authorization:
            return False
        
        authorization.is_active = False
        await db.commit()
        return True
    
    @staticmethod
    async def revoke_all_session_authorizations(
        db: AsyncSession,
        session_id: str
    ) -> int:
        """
        Revoke all addon authorizations for a session
        
        Args:
            db: Database session
            session_id: Session ID
        
        Returns:
            Number of authorizations revoked
        """
        result = await db.execute(
            select(BrowserAddonAuthorization).filter(
                and_(
                    BrowserAddonAuthorization.session_id == session_id,
                    BrowserAddonAuthorization.is_active == True
                )
            )
        )
        authorizations = result.scalars().all()
        
        count = 0
        for auth in authorizations:
            auth.is_active = False
            count += 1
        
        await db.commit()
        return count
    
    @staticmethod
    def build_registration_url(authorization: BrowserAddonAuthorization, instance_url: str) -> str:
        """
        Build a registration URL for the addon
        
        Format: imagetools://authorize?code=<auth_code>&instance=<url>
        
        Args:
            authorization: BrowserAddonAuthorization object
            instance_url: Base URL of the Image Tools instance
        
        Returns:
            Registration URL string
        """
        return f"imagetools://authorize?code={authorization.authorization_code}&instance={instance_url}"
