import os
from PIL import Image as PILImage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Image, History
from app.core.config import settings
from app.services.image_service import ImageService


class HistoryService:
    @staticmethod
    async def get_image_history(db: AsyncSession, image_id: str) -> list[History]:
        """Get operation history for an image."""
        result = await db.execute(
            select(History)
            .where(History.image_id == image_id)
            .order_by(History.sequence.asc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def undo_operation(db: AsyncSession, image_id: str) -> tuple[str, int]:
        """Undo last operation and revert to previous state."""
        image = await ImageService.get_image(db, image_id)
        if not image:
            raise ValueError(f"Image {image_id} not found")
        
        # Get history entries
        history = await HistoryService.get_image_history(db, image_id)
        
        if not history:
            raise ValueError("No operations to undo")
        
        # Find current state in history
        current_entry = None
        for entry in history:
            if entry.output_path == image.current_path:
                current_entry = entry
                break
        
        if not current_entry:
            raise ValueError("Current state not found in history")
        
        if current_entry.sequence == 1:
            # Revert to original (before first operation)
            first_entry = history[0]
            revert_path = first_entry.input_path
            revert_size = image.original_size
        else:
            # Find previous entry
            previous_entry = None
            for entry in history:
                if entry.sequence == current_entry.sequence - 1:
                    previous_entry = entry
                    break
            
            if not previous_entry:
                raise ValueError("Previous state not found")
            
            revert_path = previous_entry.output_path
            revert_size = previous_entry.file_size
        
        # Get dimensions from the revert file
        with PILImage.open(revert_path) as img:
            revert_width, revert_height = img.size
        
        # Update image record
        image.current_path = revert_path
        image.current_size = revert_size
        image.width = revert_width
        image.height = revert_height
        
        # Delete the current history entry (the one we're undoing)
        await db.delete(current_entry)
        
        # Delete the output file if it exists and is not used by other history entries
        if os.path.exists(current_entry.output_path):
            # Check if any other history entry uses this file
            other_uses = False
            for entry in history:
                if entry.id != current_entry.id and (
                    entry.input_path == current_entry.output_path or 
                    entry.output_path == current_entry.output_path
                ):
                    other_uses = True
                    break
            
            # Only delete if no other history entry references it
            if not other_uses and current_entry.output_path != image.current_path:
                os.remove(current_entry.output_path)
        
        await db.commit()
        await db.refresh(image)
        
        # Recreate thumbnail
        from pathlib import Path
        ext = Path(image.current_path).suffix
        thumbnail_path = os.path.join(settings.STORAGE_PATH, f"{image_id}_thumb{ext}")
        ImageService._create_thumbnail(image.current_path, thumbnail_path)
        image.thumbnail_path = thumbnail_path
        
        await db.commit()
        
        return revert_path, current_entry.sequence - 1
    
    @staticmethod
    async def can_undo(db: AsyncSession, image_id: str) -> bool:
        """Check if undo is available for image."""
        image = await ImageService.get_image(db, image_id)
        if not image:
            return False
        
        history = await HistoryService.get_image_history(db, image_id)
        if not history:
            return False
        
        # Check if current state has a history entry
        # If yes, we can undo to the previous state
        for entry in history:
            if entry.output_path == image.current_path:
                return True
        
        return False
    
    @staticmethod
    async def restore_to_sequence(db: AsyncSession, image_id: str, sequence: int) -> tuple[str, int]:
        """Restore image to a specific history sequence number."""
        image = await ImageService.get_image(db, image_id)
        if not image:
            raise ValueError(f"Image {image_id} not found")
        
        # Get history entries
        history = await HistoryService.get_image_history(db, image_id)
        
        if not history:
            raise ValueError("No history available")
        
        # Find the entry with the specified sequence
        target_entry = None
        for entry in history:
            if entry.sequence == sequence:
                target_entry = entry
                break
        
        if not target_entry:
            raise ValueError(f"History sequence {sequence} not found")
        
        # Get the file path to restore
        restore_path = target_entry.output_path
        restore_size = target_entry.file_size
        
        if not os.path.exists(restore_path):
            raise ValueError(f"History file not found: {restore_path}")
        
        # Get dimensions from the restore file
        with PILImage.open(restore_path) as img:
            restore_width, restore_height = img.size
            restore_format = img.format or "PNG"
        
        # Update image record
        image.current_path = restore_path
        image.current_size = restore_size
        image.width = restore_width
        image.height = restore_height
        image.format = restore_format
        
        # Recreate thumbnail
        if image.thumbnail_path and os.path.exists(image.thumbnail_path):
            os.remove(image.thumbnail_path)
        
        ext = os.path.splitext(restore_path)[1]
        thumbnail_path = os.path.join(settings.STORAGE_PATH, f"{image.id}_thumb{ext}")
        ImageService._create_thumbnail(restore_path, thumbnail_path)
        image.thumbnail_path = thumbnail_path
        
        await db.commit()
        await db.refresh(image)
        
        return restore_path, restore_size
    
    @staticmethod
    async def cleanup_old_history(db: AsyncSession, image_id: str):
        """Remove history entries beyond undo limit."""
        history = await HistoryService.get_image_history(db, image_id)
        
        if len(history) <= settings.UNDO_STACK_LIMIT:
            return
        
        # Keep only recent entries
        entries_to_remove = history[:-settings.UNDO_STACK_LIMIT]
        
        for entry in entries_to_remove:
            # Delete file if it exists
            if os.path.exists(entry.output_path):
                os.remove(entry.output_path)
            
            # Delete database record
            await db.delete(entry)
        
        await db.commit()
