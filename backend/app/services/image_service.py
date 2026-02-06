import uuid
import os
import shutil
import json
from pathlib import Path
from typing import BinaryIO, Optional
from PIL import Image as PILImage, ImageOps
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.models import Image, History
from app.core.config import settings


class ImageService:
    @staticmethod
    def _ensure_storage_dirs():
        """Ensure storage directories exist."""
        Path(settings.STORAGE_PATH).mkdir(parents=True, exist_ok=True)
        Path(settings.TEMP_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    async def save_uploaded_image(
        db: AsyncSession,
        session_id: str,
        filename: str,
        file: BinaryIO
    ) -> Image:
        """Save uploaded image and create database record."""
        ImageService._ensure_storage_dirs()
        
        image_id = str(uuid.uuid4())
        ext = Path(filename).suffix
        
        # Save original file
        original_path = os.path.join(settings.STORAGE_PATH, f"{image_id}_original{ext}")
        with open(original_path, "wb") as f:
            shutil.copyfileobj(file, f)
        
        # Auto-correct orientation based on EXIF data
        with PILImage.open(original_path) as img:
            # Apply EXIF orientation correction
            try:
                img = ImageOps.exif_transpose(img)
            except (AttributeError, KeyError, ZeroDivisionError, ValueError):
                # Image has no EXIF data or malformed EXIF, use as-is
                pass
            
            # Save corrected image
            save_kwargs = {"quality": 95, "optimize": True}
            if img.format == "PNG":
                save_kwargs = {"optimize": True}
            elif img.format == "WEBP":
                save_kwargs = {"quality": 95}
            
            img.save(original_path, **save_kwargs)
            
            width, height = img.size
            img_format = img.format
        
        # Create thumbnail
        thumbnail_path = os.path.join(settings.STORAGE_PATH, f"{image_id}_thumb{ext}")
        ImageService._create_thumbnail(original_path, thumbnail_path)
        
        # Get file size
        file_size = os.path.getsize(original_path)
        
        # Create database record
        image = Image(
            id=image_id,
            session_id=session_id,
            original_filename=filename,
            original_size=file_size,
            current_path=original_path,
            thumbnail_path=thumbnail_path,
            current_size=file_size,
            width=width,
            height=height,
            format=img_format
        )
        
        db.add(image)
        await db.commit()
        await db.refresh(image)
        
        return image
    
    @staticmethod
    def _create_thumbnail(input_path: str, output_path: str):
        """Create thumbnail for image."""
        with PILImage.open(input_path) as img:
            # Apply EXIF orientation if present
            try:
                img = ImageOps.exif_transpose(img)
            except (AttributeError, KeyError, ZeroDivisionError, ValueError):
                # Image has no EXIF data or malformed EXIF, use as-is
                pass
            img.thumbnail((settings.THUMBNAIL_SIZE, settings.THUMBNAIL_SIZE), PILImage.Resampling.LANCZOS)
            img.save(output_path, quality=settings.THUMBNAIL_QUALITY, optimize=True)
    
    @staticmethod
    async def get_image(db: AsyncSession, image_id: str) -> Optional[Image]:
        """Get image by ID."""
        result = await db.execute(
            select(Image).where(Image.id == image_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_session_images(db: AsyncSession, session_id: str) -> list[Image]:
        """Get all images for a session."""
        result = await db.execute(
            select(Image)
            .where(Image.session_id == session_id)
            .order_by(Image.created_at.desc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def delete_image(db: AsyncSession, image_id: str) -> bool:
        """Delete image and all associated files."""
        image = await ImageService.get_image(db, image_id)
        if not image:
            return False
        
        # Delete all history files
        history_records = await db.execute(
            select(History).where(History.image_id == image_id)
        )
        for record in history_records.scalars().all():
            if os.path.exists(record.output_path):
                os.remove(record.output_path)
        
        # Delete current file
        if os.path.exists(image.current_path):
            os.remove(image.current_path)
        
        # Delete thumbnail
        if image.thumbnail_path and os.path.exists(image.thumbnail_path):
            os.remove(image.thumbnail_path)
        
        # Delete database records
        await db.delete(image)
        await db.commit()
        
        return True
    
    @staticmethod
    async def count_session_images(db: AsyncSession, session_id: str) -> int:
        """Count images in session."""
        result = await db.execute(
            select(func.count(Image.id)).where(Image.session_id == session_id)
        )
        return result.scalar()
    
    @staticmethod
    async def rotate_image(db: AsyncSession, image_id: str, degrees: int) -> tuple[str, int, int, int]:
        """
        Rotate an image by specified degrees.
        
        Args:
            db: Database session
            image_id: Image ID
            degrees: Rotation degrees (90, 180, or 270)
            
        Returns:
            Tuple of (output_path, new_size, width, height)
        """
        if degrees not in [90, 180, 270]:
            raise ValueError("Rotation degrees must be 90, 180, or 270")
        
        image = await ImageService.get_image(db, image_id)
        if not image:
            raise ValueError("Image not found")
        
        ImageService._ensure_storage_dirs()
        
        # Generate output path
        ext = Path(image.current_path).suffix
        output_path = os.path.join(
            settings.STORAGE_PATH,
            f"{image_id}_rotated_{uuid.uuid4()}{ext}"
        )
        
        # Rotate image
        with PILImage.open(image.current_path) as img:
            # Convert EXIF rotation to actual rotation
            try:
                img = ImageOps.exif_transpose(img)
            except (AttributeError, KeyError, ZeroDivisionError, ValueError):
                pass
            
            # Rotate the image
            rotated = img.rotate(-degrees, expand=True)
            
            # Save rotated image
            save_kwargs = {"quality": 95, "optimize": True}
            if img.format == "PNG":
                save_kwargs = {"optimize": True}
            elif img.format == "WEBP":
                save_kwargs = {"quality": 95}
                
            rotated.save(output_path, **save_kwargs)
            
            new_width, new_height = rotated.size
        
        # Get file size
        new_size = os.path.getsize(output_path)
        
        # Create history entry
        history_entry = History(
            id=str(uuid.uuid4()),
            image_id=image_id,
            operation_type="rotate",
            operation_params=json.dumps({"degrees": degrees}),
            input_path=image.current_path,
            output_path=output_path,
            file_size=new_size,
            sequence=await ImageService._get_next_sequence(db, image_id)
        )
        db.add(history_entry)
        
        # Update image record
        image.current_path = output_path
        image.current_size = new_size
        image.width = new_width
        image.height = new_height
        
        await db.commit()
        await db.refresh(image)
        
        # Recreate thumbnail
        if image.thumbnail_path and os.path.exists(image.thumbnail_path):
            os.remove(image.thumbnail_path)
        thumbnail_path = os.path.join(settings.STORAGE_PATH, f"{image_id}_thumb{ext}")
        ImageService._create_thumbnail(output_path, thumbnail_path)
        image.thumbnail_path = thumbnail_path
        await db.commit()
        
        return output_path, new_size, new_width, new_height
    
    @staticmethod
    async def _get_next_sequence(db: AsyncSession, image_id: str) -> int:
        """Get next sequence number for history."""
        result = await db.execute(
            select(History)
            .where(History.image_id == image_id)
            .order_by(History.sequence.desc())
        )
        last_entry = result.scalars().first()
        return (last_entry.sequence + 1) if last_entry else 1
