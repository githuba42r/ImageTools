"""
Service for mobile app pairing and authentication with long-term authorization
"""
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select, or_

from app.models.models import MobileAppPairing, Session as SessionModel
from app.schemas.schemas import MobileAppPairingCreate, MobileAppPairingResponse


class MobileService:
    """Service for managing mobile app pairings with long-term authorization"""
    
    @staticmethod
    def generate_shared_secret() -> str:
        """Generate a cryptographically secure shared secret"""
        # Generate a 32-byte (256-bit) random secret and encode as hex
        return secrets.token_hex(32)
    
    @staticmethod
    async def create_pairing(
        db: AsyncSession,
        session_id: str,
        device_name: Optional[str] = None,
        expiry_minutes: int = 2
    ) -> MobileAppPairing:
        """
        Create a new mobile app pairing for a session with short-lived secret
        
        Args:
            db: Database session
            session_id: Session ID to link the pairing to
            device_name: Optional device identifier
            expiry_minutes: Number of minutes until pairing expires (default 2)
        
        Returns:
            Created MobileAppPairing object
        """
        # Verify session exists
        result = await db.execute(select(SessionModel).filter(SessionModel.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Generate pairing with 2-minute timeout
        pairing_id = str(uuid.uuid4())
        shared_secret = MobileService.generate_shared_secret()
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        pairing = MobileAppPairing(
            id=pairing_id,
            session_id=session_id,
            device_name=device_name,
            shared_secret=shared_secret,
            is_active=True,
            used=False,
            expires_at=expires_at
        )
        
        db.add(pairing)
        await db.commit()
        await db.refresh(pairing)
        
        return pairing
    
    @staticmethod
    async def validate_and_exchange_secrets(
        db: AsyncSession,
        shared_secret: str,
        device_model: Optional[str] = None,
        device_manufacturer: Optional[str] = None,
        device_owner: Optional[str] = None,
        os_version: Optional[str] = None,
        app_version: Optional[str] = None
    ) -> Optional[MobileAppPairing]:
        """
        Validate initial shared secret and exchange for long-term authorization
        
        This is called when the Android app first scans the QR code.
        It validates the short-lived secret and generates:
        - long_term_secret (90 days) for image uploads
        - refresh_secret (180 days) for renewing long-term secret
        
        Args:
            db: Database session
            shared_secret: Initial shared secret from QR code
            device_model: Device model (e.g. "Samsung Galaxy S21")
            device_manufacturer: Device manufacturer (e.g. "Samsung")
            device_owner: Device owner name or email
            os_version: OS version (e.g. "Android 13")
            app_version: ImageTools app version
        
        Returns:
            MobileAppPairing with long-term secrets, or None if invalid
        """
        result = await db.execute(
            select(MobileAppPairing).filter(
                and_(
                    MobileAppPairing.shared_secret == shared_secret,
                    MobileAppPairing.is_active == True
                )
            )
        )
        pairing = result.scalar_one_or_none()
        
        if not pairing:
            return None
        
        # Check if already used (single-use)
        if pairing.used:
            return None
        
        # Check if expired (2-minute timeout)
        if pairing.expires_at and pairing.expires_at < datetime.utcnow():
            # Mark as inactive
            pairing.is_active = False
            await db.commit()
            return None
        
        # Store device metadata
        pairing.device_model = device_model
        pairing.device_manufacturer = device_manufacturer
        pairing.device_owner = device_owner
        pairing.os_version = os_version
        pairing.app_version = app_version
        
        # Generate long-term and refresh secrets
        pairing.long_term_secret = MobileService.generate_shared_secret()
        pairing.long_term_expires_at = datetime.utcnow() + timedelta(days=90)
        pairing.refresh_secret = MobileService.generate_shared_secret()
        pairing.refresh_expires_at = datetime.utcnow() + timedelta(days=180)
        
        # Mark initial secret as used
        pairing.used = True
        pairing.last_used_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(pairing)
        
        return pairing
    
    @staticmethod
    async def validate_long_term_secret(
        db: AsyncSession,
        long_term_secret: str
    ) -> Optional[MobileAppPairing]:
        """
        Validate a long-term secret for image uploads
        
        Args:
            db: Database session
            long_term_secret: Long-term secret for authentication
        
        Returns:
            MobileAppPairing if valid, None otherwise
        """
        result = await db.execute(
            select(MobileAppPairing).filter(
                and_(
                    MobileAppPairing.long_term_secret == long_term_secret,
                    MobileAppPairing.is_active == True
                )
            )
        )
        pairing = result.scalar_one_or_none()
        
        if not pairing:
            return None
        
        # Check if long-term secret expired
        if pairing.long_term_expires_at and pairing.long_term_expires_at < datetime.utcnow():
            return None
        
        # Update last used timestamp
        pairing.last_used_at = datetime.utcnow()
        await db.commit()
        
        return pairing
    
    @staticmethod
    async def refresh_long_term_secret(
        db: AsyncSession,
        refresh_secret: str
    ) -> Optional[MobileAppPairing]:
        """
        Refresh/renew the long-term secret using refresh secret
        
        Can be used up to 90 days after long-term secret expires
        (within the 180-day refresh secret validity period)
        
        Args:
            db: Database session
            refresh_secret: Refresh secret for renewing
        
        Returns:
            MobileAppPairing with new long-term secret, or None if invalid
        """
        result = await db.execute(
            select(MobileAppPairing).filter(
                and_(
                    MobileAppPairing.refresh_secret == refresh_secret,
                    MobileAppPairing.is_active == True
                )
            )
        )
        pairing = result.scalar_one_or_none()
        
        if not pairing:
            return None
        
        # Check if refresh secret expired
        if pairing.refresh_expires_at and pairing.refresh_expires_at < datetime.utcnow():
            # Refresh window closed, pairing no longer renewable
            pairing.is_active = False
            await db.commit()
            return None
        
        # Generate new long-term secret (90 more days)
        pairing.long_term_secret = MobileService.generate_shared_secret()
        pairing.long_term_expires_at = datetime.utcnow() + timedelta(days=90)
        pairing.last_used_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(pairing)
        
        return pairing
    
    @staticmethod
    async def get_pairing_by_id(
        db: AsyncSession,
        pairing_id: str
    ) -> Optional[MobileAppPairing]:
        """Get a pairing by ID"""
        result = await db.execute(select(MobileAppPairing).filter(MobileAppPairing.id == pairing_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_session_pairings(
        db: AsyncSession,
        session_id: str,
        active_only: bool = True
    ) -> list[MobileAppPairing]:
        """
        Get all pairings for a session
        
        Args:
            db: Database session
            session_id: Session ID
            active_only: Only return active pairings (default True)
        
        Returns:
            List of pairings
        """
        query = select(MobileAppPairing).filter(MobileAppPairing.session_id == session_id)
        
        if active_only:
            query = query.filter(MobileAppPairing.is_active == True)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def deactivate_pairing(
        db: AsyncSession,
        pairing_id: str
    ) -> bool:
        """
        Deactivate a pairing
        
        Args:
            db: Database session
            pairing_id: Pairing ID
        
        Returns:
            True if deactivated, False if not found
        """
        result = await db.execute(select(MobileAppPairing).filter(MobileAppPairing.id == pairing_id))
        pairing = result.scalar_one_or_none()
        if not pairing:
            return False
        
        pairing.is_active = False
        await db.commit()
        return True
    
    @staticmethod
    async def revoke_all_session_pairings(
        db: AsyncSession,
        session_id: str
    ) -> int:
        """
        Revoke all pairings for a session
        
        Args:
            db: Database session
            session_id: Session ID
        
        Returns:
            Number of pairings revoked
        """
        result = await db.execute(
            select(MobileAppPairing).filter(
                and_(
                    MobileAppPairing.session_id == session_id,
                    MobileAppPairing.is_active == True
                )
            )
        )
        pairings = result.scalars().all()
        
        count = 0
        for pairing in pairings:
            pairing.is_active = False
            count += 1
        
        await db.commit()
        return count
