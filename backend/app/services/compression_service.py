import uuid
import os
import json
from pathlib import Path
from typing import Dict, Any
from PIL import Image as PILImage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Image, History
from app.core.config import settings
from app.services.image_service import ImageService


class CompressionService:
    @staticmethod
    def _get_preset_config(preset: str) -> Dict[str, Any]:
        """Get compression preset configuration."""
        presets = {
            "email": {
                "max_width": settings.EMAIL_MAX_WIDTH,
                "max_height": settings.EMAIL_MAX_HEIGHT,
                "quality": settings.EMAIL_QUALITY,
                "target_size_kb": settings.EMAIL_TARGET_SIZE_KB,
                "format": settings.EMAIL_FORMAT,
            },
            "web": {
                "max_width": settings.WEB_MAX_WIDTH,
                "max_height": settings.WEB_MAX_HEIGHT,
                "quality": settings.WEB_QUALITY,
                "target_size_kb": settings.WEB_TARGET_SIZE_KB,
                "format": settings.WEB_FORMAT,
            },
            "web_hq": {
                "max_width": settings.WEB_HQ_MAX_WIDTH,
                "max_height": settings.WEB_HQ_MAX_HEIGHT,
                "quality": settings.WEB_HQ_QUALITY,
                "target_size_kb": settings.WEB_HQ_TARGET_SIZE_KB,
                "format": settings.WEB_HQ_FORMAT,
            },
        }
        return presets.get(preset, presets["email"])
    
    @staticmethod
    async def compress_image(
        db: AsyncSession,
        image_id: str,
        preset: str = "email",
        custom_params: Dict[str, Any] = None
    ) -> tuple[str, int, int]:
        """Compress image with given preset or custom parameters."""
        image = await ImageService.get_image(db, image_id)
        if not image:
            raise ValueError(f"Image {image_id} not found")
        
        # Get compression parameters
        if preset == "custom" and custom_params:
            params = custom_params
        else:
            params = CompressionService._get_preset_config(preset)
        
        # Generate output path
        output_id = str(uuid.uuid4())
        output_format = params.get("format", "JPEG").lower()
        if output_format == "jpeg":
            output_format = "jpg"
        output_path = os.path.join(
            settings.STORAGE_PATH,
            f"{image_id}_{output_id}.{output_format}"
        )
        
        # Load and process image
        with PILImage.open(image.current_path) as img:
            # Convert RGBA to RGB for JPEG
            if params.get("format") == "JPEG" and img.mode in ("RGBA", "P", "LA"):
                rgb_img = PILImage.new("RGB", img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
                img = rgb_img
            
            # Resize if needed
            max_width = params.get("max_width")
            max_height = params.get("max_height")
            if max_width and max_height:
                img.thumbnail((max_width, max_height), PILImage.Resampling.LANCZOS)
            
            # Initial save with quality
            quality = params.get("quality", 85)
            img.save(output_path, format=params.get("format", "JPEG"), quality=quality, optimize=True)
        
        # Check target size and adjust quality if needed
        target_size_kb = params.get("target_size_kb")
        if target_size_kb:
            target_size_bytes = target_size_kb * 1024
            current_size = os.path.getsize(output_path)
            
            # Iteratively reduce quality if needed
            attempts = 0
            while current_size > target_size_bytes and quality > 10 and attempts < 10:
                quality -= 5
                with PILImage.open(image.current_path) as img:
                    if params.get("format") == "JPEG" and img.mode in ("RGBA", "P", "LA"):
                        rgb_img = PILImage.new("RGB", img.size, (255, 255, 255))
                        rgb_img.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
                        img = rgb_img
                    
                    if max_width and max_height:
                        img.thumbnail((max_width, max_height), PILImage.Resampling.LANCZOS)
                    
                    img.save(output_path, format=params.get("format", "JPEG"), quality=quality, optimize=True)
                
                current_size = os.path.getsize(output_path)
                attempts += 1
        
        # Get final size
        compressed_size = os.path.getsize(output_path)
        
        # Add to history
        history_entry = History(
            id=str(uuid.uuid4()),
            image_id=image_id,
            operation_type=f"compress_{preset}",
            operation_params=json.dumps(params),
            input_path=image.current_path,
            output_path=output_path,
            file_size=compressed_size,
            sequence=await CompressionService._get_next_sequence(db, image_id)
        )
        db.add(history_entry)
        
        # Update image current path and size
        image.current_path = output_path
        image.current_size = compressed_size
        
        await db.commit()
        
        return output_path, compressed_size, image.original_size
    
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
