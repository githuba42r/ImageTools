"""
Background Removal Service

This service provides background removal functionality using the rembg library.
Uses local CPU processing (FREE, no API costs).
"""

import os
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from PIL import Image as PILImage
from rembg import remove, new_session
import logging

from app.models.models import Image, History
from app.core.config import settings

logger = logging.getLogger(__name__)


class BackgroundRemovalService:
    """Service for removing backgrounds from images using rembg"""
    
    # Available rembg models
    MODELS = {
        "u2net": "General purpose (default)",
        "u2net_human_seg": "Human segmentation",
        "isnet-general-use": "High quality general",
        "isnet-anime": "Anime/illustration",
    }
    
    DEFAULT_MODEL = "u2net"
    
    def __init__(self, db: Session, model: str = DEFAULT_MODEL):
        """
        Initialize background removal service
        
        Args:
            db: Database session
            model: rembg model to use (u2net, u2net_human_seg, etc.)
        """
        self.db = db
        self.model = model if model in self.MODELS else self.DEFAULT_MODEL
        self._session = None
    
    def _get_session(self):
        """Get or create rembg session with specified model"""
        if self._session is None:
            logger.info(f"Initializing rembg session with model: {self.model}")
            self._session = new_session(self.model)
        return self._session
    
    async def remove_background(
        self,
        image_id: str,
        alpha_matting: bool = False,
        alpha_matting_foreground_threshold: int = 240,
        alpha_matting_background_threshold: int = 10,
    ) -> Dict[str, Any]:
        """
        Remove background from an image
        
        Args:
            image_id: Image ID from database
            alpha_matting: Use alpha matting for better edge quality
            alpha_matting_foreground_threshold: Foreground threshold (0-255)
            alpha_matting_background_threshold: Background threshold (0-255)
            
        Returns:
            Dict with result information
        """
        # Get image from database
        image = self.db.query(Image).filter(Image.id == image_id).first()
        if not image:
            raise ValueError(f"Image {image_id} not found")
        
        # Get current image path
        current_path = image.current_path
        if not os.path.exists(current_path):
            raise FileNotFoundError(f"Image file not found: {current_path}")
        
        logger.info(f"Removing background from image: {image_id} using model: {self.model}")
        
        # Load input image
        input_image = PILImage.open(current_path)
        original_format = input_image.format
        original_size = os.path.getsize(current_path)
        
        # Remove background
        try:
            output_image = remove(
                input_image,
                session=self._get_session(),
                alpha_matting=alpha_matting,
                alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
                alpha_matting_background_threshold=alpha_matting_background_threshold,
            )
        except Exception as e:
            logger.error(f"Background removal failed: {str(e)}")
            raise Exception(f"Background removal failed: {str(e)}")
        
        # Generate new filename (always PNG for transparency)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"{image.id}_nobg_{timestamp}.png"
        new_path = os.path.join(settings.UPLOAD_DIR, new_filename)
        
        # Save output as PNG with transparency
        output_image.save(new_path, 'PNG')
        new_size = os.path.getsize(new_path)
        
        logger.info(f"Background removed successfully. Output: {new_path}")
        
        # Add to history
        history_entry = History(
            id=str(uuid.uuid4()),
            image_id=image_id,
            operation_type="background_removal",
            operation_params=f"model={self.model},alpha_matting={alpha_matting}",
            file_path=current_path,
            file_size=original_size,
            created_at=datetime.utcnow(),
            sequence=self._get_next_sequence(image_id)
        )
        self.db.add(history_entry)
        
        # Update image record
        image.current_path = new_path
        image.current_size = new_size
        image.format = "PNG"
        image.updated_at = datetime.utcnow()
        
        # Update dimensions if changed
        width, height = output_image.size
        image.width = width
        image.height = height
        
        self.db.commit()
        self.db.refresh(image)
        
        return {
            "image_id": image_id,
            "original_size": original_size,
            "new_size": new_size,
            "format": "PNG",
            "has_transparency": True,
            "model_used": self.model,
            "compression_ratio": round(new_size / original_size, 2) if original_size > 0 else 0,
            "width": width,
            "height": height,
            "image_url": f"/api/v1/images/{image_id}/current"
        }
    
    def _get_next_sequence(self, image_id: str) -> int:
        """Get next sequence number for history"""
        last_entry = self.db.query(History).filter(
            History.image_id == image_id
        ).order_by(History.sequence.desc()).first()
        
        return (last_entry.sequence + 1) if last_entry else 1
    
    @classmethod
    def get_available_models(cls) -> Dict[str, str]:
        """Get list of available rembg models"""
        return cls.MODELS.copy()
    
    def set_model(self, model: str) -> None:
        """
        Change the rembg model
        
        Args:
            model: Model name (u2net, u2net_human_seg, etc.)
        """
        if model not in self.MODELS:
            raise ValueError(f"Invalid model: {model}. Available: {list(self.MODELS.keys())}")
        
        if model != self.model:
            self.model = model
            self._session = None  # Reset session to load new model
            logger.info(f"Changed rembg model to: {model}")
