"""
User identity service.

Replaces the old session_service.  The concept of a "session" (browser-scoped,
expiring) has been replaced by a persistent User identity:

  - Authenticated users (Authelia / nginx basic-auth): UUID generated on first
    login and retrieved by username on every subsequent request.  All browsers
    that share the same authenticated username see the same images, pairings,
    and addon authorizations.

  - Anonymous (unauthenticated) deployments: a single well-known UUID
    (ANONYMOUS_USER_ID) is used so all browsers share one global image store.
    This record is created at startup and never deleted.
"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.models import User, Image
from app.core.config import settings

# Well-known fixed user ID used when no auth proxy is present.
ANONYMOUS_USER_ID = "00000000-0000-0000-0000-000000000000"


class UserService:

    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
        """Return the User record whose username matches, or None."""
        result = await db.execute(
            select(User).where(User.username == username)
        )
        return result.scalars().first()

    @staticmethod
    async def get_user(db: AsyncSession, user_id: str) -> User | None:
        """Return the User record by UUID, or None."""
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_or_create_user(
        db: AsyncSession,
        username: str | None = None,
        display_name: str | None = None,
    ) -> User:
        """
        Return (or create) the canonical User for this request.

        Resolution order:
        1. If *username* is provided (Authelia / auth-proxy mode), look up the
           existing user record by username and return it (updating display_name
           if it changed).  If no record exists yet, create one with a new UUID.
        2. Anonymous mode (no username): always return the single well-known
           ANONYMOUS_USER_ID record, creating it if this is the first startup.
        """
        if username:
            existing = await UserService.get_user_by_username(db, username)
            if existing:
                if display_name and existing.display_name != display_name:
                    existing.display_name = display_name
                    await db.commit()
                    await db.refresh(existing)
                return existing
            # First login for this username — create a new user record
            user = User(
                id=str(uuid.uuid4()),
                username=username,
                display_name=display_name,
            )
        else:
            # Anonymous: upsert the well-known record
            existing = await UserService.get_user(db, ANONYMOUS_USER_ID)
            if existing:
                return existing
            user = User(
                id=ANONYMOUS_USER_ID,
                username=None,
                display_name="Anonymous",
            )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Ensure system default compression profiles exist
        from app.services import profile_service
        await profile_service.create_system_default_profiles(db)

        return user

    @staticmethod
    async def validate_user(db: AsyncSession, user_id: str) -> bool:
        """Check that a user record exists (users never expire)."""
        user = await UserService.get_user(db, user_id)
        return user is not None

    @staticmethod
    async def cleanup_anonymous_old_images(db: AsyncSession, days: int) -> int:
        """
        Delete images belonging to the anonymous user that are older than
        *days* days.  Removes image files from disk and DB records.
        Returns the number of images deleted.
        """
        import os
        from pathlib import Path
        from sqlalchemy import or_

        cutoff = datetime.utcnow() - timedelta(days=days)
        # Eligible for cleanup iff created_at < cutoff AND
        # (pin_expires_at IS NULL OR pin_expires_at < cutoff). The latter
        # means "image's pin expired more than `days` days ago" — so the
        # effective expiration (pin_expires_at + days) is now in the past.
        result = await db.execute(
            select(Image)
            .where(Image.user_id == ANONYMOUS_USER_ID)
            .where(Image.created_at < cutoff)
            .where(or_(Image.pin_expires_at.is_(None), Image.pin_expires_at < cutoff))
        )
        old_images = result.scalars().all()

        if not old_images:
            return 0

        storage_dir = Path(settings.STORAGE_PATH)

        for image in old_images:
            try:
                if image.current_path and os.path.exists(image.current_path):
                    os.remove(image.current_path)
                if image.thumbnail_path and os.path.exists(image.thumbnail_path):
                    os.remove(image.thumbnail_path)
                image_history_dir = storage_dir / image.id / "history"
                if image_history_dir.exists():
                    for f in image_history_dir.glob("*"):
                        if f.is_file():
                            f.unlink()
                    try:
                        image_history_dir.rmdir()
                    except OSError:
                        pass
                image_dir = storage_dir / image.id
                if image_dir.exists():
                    try:
                        image_dir.rmdir()
                    except OSError:
                        pass
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f"Error deleting files for image {image.id}: {e}"
                )

        image_ids = [img.id for img in old_images]
        from sqlalchemy import delete as sa_delete
        await db.execute(sa_delete(Image).where(Image.id.in_(image_ids)))
        await db.commit()

        return len(image_ids)
