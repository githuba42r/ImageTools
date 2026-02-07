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
            
            # Get format and dimensions before any modifications
            img_format = img.format or 'JPEG'  # Default to JPEG if format is None
            width, height = img.size
            
            # Save corrected image
            save_kwargs = {"quality": 95, "optimize": True}
            if img_format == "PNG":
                save_kwargs = {"optimize": True}
            elif img_format == "WEBP":
                save_kwargs = {"quality": 95}
            
            img.save(original_path, format=img_format, **save_kwargs)
        
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
            
            # Determine output format from file extension
            file_ext = os.path.splitext(output_path)[1].upper().replace('.', '')
            img_format = file_ext if file_ext else 'JPEG'
            
            # Convert RGBA to RGB for JPEG format (JPEG doesn't support transparency)
            if img.mode == 'RGBA' and img_format in ['JPEG', 'JPG']:
                rgb_img = PILImage.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])  # Use alpha channel as mask
                img = rgb_img
            elif img.mode not in ['RGB', 'L'] and img_format in ['JPEG', 'JPG']:
                # Convert any other non-RGB mode to RGB for JPEG
                img = img.convert('RGB')
            
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
    async def flip_image(db: AsyncSession, image_id: str, direction: str) -> tuple[str, int, int, int]:
        """
        Flip an image horizontally or vertically.
        
        Args:
            db: Database session
            image_id: Image ID
            direction: "horizontal" or "vertical"
            
        Returns:
            Tuple of (output_path, new_size, width, height)
        """
        if direction not in ["horizontal", "vertical"]:
            raise ValueError("Direction must be 'horizontal' or 'vertical'")
        
        image = await ImageService.get_image(db, image_id)
        if not image:
            raise ValueError("Image not found")
        
        ImageService._ensure_storage_dirs()
        
        # Generate output path
        ext = Path(image.current_path).suffix
        output_path = os.path.join(
            settings.STORAGE_PATH,
            f"{image_id}_flipped_{uuid.uuid4()}{ext}"
        )
        
        # Flip image
        with PILImage.open(image.current_path) as img:
            # Convert EXIF rotation to actual rotation
            try:
                img = ImageOps.exif_transpose(img)
            except (AttributeError, KeyError, ZeroDivisionError, ValueError):
                pass
            
            # Flip the image
            if direction == "horizontal":
                flipped = img.transpose(PILImage.FLIP_LEFT_RIGHT)
            else:  # vertical
                flipped = img.transpose(PILImage.FLIP_TOP_BOTTOM)
            
            # Save flipped image
            save_kwargs = {"quality": 95, "optimize": True}
            if img.format == "PNG":
                save_kwargs = {"optimize": True}
            elif img.format == "WEBP":
                save_kwargs = {"quality": 95}
                
            flipped.save(output_path, **save_kwargs)
            
            new_width, new_height = flipped.size
        
        # Get file size
        new_size = os.path.getsize(output_path)
        
        # Create history entry
        history_entry = History(
            id=str(uuid.uuid4()),
            image_id=image_id,
            operation_type="flip",
            operation_params=json.dumps({"direction": direction}),
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
    async def resize_image(
        db: AsyncSession,
        image_id: str,
        width: int,
        height: int
    ) -> tuple[str, int, int, int]:
        """
        Resize an image to specified dimensions.
        
        Args:
            db: Database session
            image_id: Image ID
            width: Target width in pixels
            height: Target height in pixels
            
        Returns:
            Tuple of (output_path, new_size, width, height)
        """
        if width <= 0 or height <= 0:
            raise ValueError("Width and height must be greater than 0")
        
        image = await ImageService.get_image(db, image_id)
        if not image:
            raise ValueError("Image not found")
        
        ImageService._ensure_storage_dirs()
        
        # Generate output path
        ext = Path(image.current_path).suffix
        output_path = os.path.join(
            settings.STORAGE_PATH,
            f"{image_id}_resized_{uuid.uuid4()}{ext}"
        )
        
        # Resize image
        with PILImage.open(image.current_path) as img:
            # Convert EXIF rotation to actual rotation
            try:
                img = ImageOps.exif_transpose(img)
            except (AttributeError, KeyError, ZeroDivisionError, ValueError):
                pass
            
            # Resize using high-quality resampling
            resized = img.resize((width, height), PILImage.Resampling.LANCZOS)
            
            # Save resized image
            save_kwargs = {"quality": 95, "optimize": True}
            if img.format == "PNG":
                save_kwargs = {"optimize": True}
            elif img.format == "WEBP":
                save_kwargs = {"quality": 95}
                
            resized.save(output_path, **save_kwargs)
            
            new_width, new_height = resized.size
        
        # Get file size
        new_size = os.path.getsize(output_path)
        
        # Create history entry
        history_entry = History(
            id=str(uuid.uuid4()),
            image_id=image_id,
            operation_type="resize",
            operation_params=json.dumps({"width": width, "height": height}),
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
    async def save_edited_image(
        db: AsyncSession,
        image_id: str,
        file: BinaryIO
    ) -> tuple[str, int, int, int]:
        """
        Save an edited image from the editor.
        
        Args:
            db: Database session
            image_id: Image ID
            file: File object with edited image data
            
        Returns:
            Tuple of (output_path, new_size, width, height)
        """
        import time
        start_time = time.time()
        
        print(f"[EDIT TIMING] Starting save_edited_image for {image_id}")
        
        image = await ImageService.get_image(db, image_id)
        if not image:
            raise ValueError("Image not found")
        print(f"[EDIT TIMING] Got image from DB: {time.time() - start_time:.2f}s")
        
        ImageService._ensure_storage_dirs()
        
        # Generate output path
        ext = Path(image.current_path).suffix
        output_path = os.path.join(
            settings.STORAGE_PATH,
            f"{image_id}_edited_{uuid.uuid4()}{ext}"
        )
        
        # Save edited image to temporary file first
        temp_start = time.time()
        temp_path = os.path.join(settings.TEMP_STORAGE_PATH, f"temp_{uuid.uuid4()}{ext}")
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file, f)
        print(f"[EDIT TIMING] Saved to temp file: {time.time() - temp_start:.2f}s")
        
        # Open and process the edited image
        process_start = time.time()
        with PILImage.open(temp_path) as img:
            # Apply EXIF orientation if present
            try:
                img = ImageOps.exif_transpose(img)
            except (AttributeError, KeyError, ZeroDivisionError, ValueError):
                pass
            
            # Determine format for saving
            img_format = img.format or 'PNG'  # Default to PNG if format not detected
            
            # Convert RGBA to RGB if saving as JPEG (JPEG doesn't support transparency)
            if img.mode == 'RGBA' and img_format in ['JPEG', 'JPG']:
                # Create a white background
                rgb_img = PILImage.new('RGB', img.size, (255, 255, 255))
                # Paste the RGBA image on the white background
                rgb_img.paste(img, mask=img.split()[3])  # Use alpha channel as mask
                img = rgb_img
            elif img.mode not in ('RGB', 'L') and img_format in ['JPEG', 'JPG']:
                # Convert any other non-RGB mode to RGB for JPEG
                img = img.convert('RGB')
            
            # Save with quality settings based on format
            save_kwargs = {}
            if img_format in ['JPEG', 'JPG']:
                save_kwargs = {"quality": 95, "optimize": True}
            elif img_format == "PNG":
                save_kwargs = {"optimize": True}
            elif img_format == "WEBP":
                save_kwargs = {"quality": 95}
            else:
                save_kwargs = {"quality": 95}
            
            save_start = time.time()
            img.save(output_path, format=img_format, **save_kwargs)
            print(f"[EDIT TIMING] Saved main image: {time.time() - save_start:.2f}s")
            
            new_width, new_height = img.size
        print(f"[EDIT TIMING] Processed image: {time.time() - process_start:.2f}s")
        
        # Remove temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # Get file size
        new_size = os.path.getsize(output_path)
        
        # Create history entry
        history_start = time.time()
        history_entry = History(
            id=str(uuid.uuid4()),
            image_id=image_id,
            operation_type="edit",
            operation_params=json.dumps({"source": "advanced_editor"}),
            input_path=image.current_path,
            output_path=output_path,
            file_size=new_size,
            sequence=await ImageService._get_next_sequence(db, image_id)
        )
        db.add(history_entry)
        print(f"[EDIT TIMING] Created history entry: {time.time() - history_start:.2f}s")
        
        # Update image record
        update_start = time.time()
        image.current_path = output_path
        image.current_size = new_size
        image.width = new_width
        image.height = new_height
        
        await db.commit()
        await db.refresh(image)
        print(f"[EDIT TIMING] Updated image record: {time.time() - update_start:.2f}s")
        
        # Recreate thumbnail
        thumb_start = time.time()
        if image.thumbnail_path and os.path.exists(image.thumbnail_path):
            os.remove(image.thumbnail_path)
        thumbnail_path = os.path.join(settings.STORAGE_PATH, f"{image_id}_thumb{ext}")
        ImageService._create_thumbnail(output_path, thumbnail_path)
        image.thumbnail_path = thumbnail_path
        await db.commit()
        print(f"[EDIT TIMING] Created thumbnail: {time.time() - thumb_start:.2f}s")
        
        print(f"[EDIT TIMING] Total time: {time.time() - start_time:.2f}s")
        
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
    
    @staticmethod
    def extract_exif(image_path: str) -> dict:
        """Extract EXIF metadata from an image."""
        try:
            with PILImage.open(image_path) as img:
                exif_data = {}
                
                # Get basic EXIF data
                exif = img._getexif() if hasattr(img, '_getexif') else None
                
                if exif:
                    from PIL.ExifTags import TAGS, GPSTAGS
                    
                    # Common EXIF tags to extract
                    interesting_tags = {
                        'Make', 'Model', 'DateTime', 'DateTimeOriginal',
                        'ExposureTime', 'FNumber', 'ISO', 'ISOSpeedRatings',
                        'FocalLength', 'Flash', 'WhiteBalance', 'Software',
                        'Orientation', 'XResolution', 'YResolution'
                    }
                    
                    gps_info = {}
                    
                    for tag_id, value in exif.items():
                        tag_name = TAGS.get(tag_id, tag_id)
                        
                        # Handle GPS data separately
                        if tag_name == 'GPSInfo':
                            for gps_tag_id, gps_value in value.items():
                                gps_tag_name = GPSTAGS.get(gps_tag_id, gps_tag_id)
                                gps_info[gps_tag_name] = gps_value
                        elif tag_name in interesting_tags:
                            # Convert value to string representation
                            if isinstance(value, bytes):
                                try:
                                    value = value.decode('utf-8')
                                except:
                                    value = str(value)
                            elif isinstance(value, tuple):
                                # Handle rational numbers (like exposure time)
                                if len(value) == 2 and value[1] != 0:
                                    value = f"{value[0]}/{value[1]}"
                                else:
                                    value = str(value)
                            
                            exif_data[tag_name] = str(value)
                    
                    # Process GPS data if available
                    if gps_info:
                        exif_data['GPS'] = ImageService._parse_gps_info(gps_info)
                
                # Add basic image info
                exif_data['Format'] = img.format
                exif_data['Mode'] = img.mode
                exif_data['Size'] = f"{img.size[0]}x{img.size[1]}"
                
                return exif_data
                
        except Exception as e:
            return {'error': f'Failed to extract EXIF: {str(e)}'}
    
    @staticmethod
    def _parse_gps_info(gps_info: dict) -> dict:
        """Parse GPS information and convert to decimal degrees."""
        result = {}
        
        try:
            # Get GPS coordinates
            lat = gps_info.get('GPSLatitude')
            lat_ref = gps_info.get('GPSLatitudeRef')
            lon = gps_info.get('GPSLongitude')
            lon_ref = gps_info.get('GPSLongitudeRef')
            
            if lat and lon and lat_ref and lon_ref:
                # Convert to decimal degrees
                lat_decimal = ImageService._convert_to_degrees(lat)
                if lat_ref == 'S':
                    lat_decimal = -lat_decimal
                    
                lon_decimal = ImageService._convert_to_degrees(lon)
                if lon_ref == 'W':
                    lon_decimal = -lon_decimal
                
                result['latitude'] = lat_decimal
                result['longitude'] = lon_decimal
                result['latitude_ref'] = lat_ref
                result['longitude_ref'] = lon_ref
            
            # Get altitude if available
            altitude = gps_info.get('GPSAltitude')
            altitude_ref = gps_info.get('GPSAltitudeRef')
            if altitude:
                # Altitude is typically a tuple (numerator, denominator)
                if isinstance(altitude, tuple) and len(altitude) == 2 and altitude[1] != 0:
                    altitude_meters = altitude[0] / altitude[1]
                    # altitude_ref: 0 = above sea level, 1 = below sea level
                    if altitude_ref == 1:
                        altitude_meters = -altitude_meters
                    result['altitude'] = altitude_meters
            
            # Get timestamp if available
            date_stamp = gps_info.get('GPSDateStamp')
            time_stamp = gps_info.get('GPSTimeStamp')
            if date_stamp:
                result['date'] = date_stamp
            if time_stamp:
                # time_stamp is typically a tuple of (hours, minutes, seconds)
                if isinstance(time_stamp, tuple) and len(time_stamp) == 3:
                    result['time'] = f"{int(time_stamp[0]):02d}:{int(time_stamp[1]):02d}:{int(time_stamp[2]):02d}"
        
        except Exception as e:
            result['error'] = f'Failed to parse GPS data: {str(e)}'
        
        return result
    
    @staticmethod
    def _convert_to_degrees(value):
        """Convert GPS coordinates from degrees/minutes/seconds to decimal degrees."""
        # value is typically ((degrees_num, degrees_den), (minutes_num, minutes_den), (seconds_num, seconds_den))
        d = value[0][0] / value[0][1] if value[0][1] != 0 else value[0][0]
        m = value[1][0] / value[1][1] if value[1][1] != 0 else value[1][0]
        s = value[2][0] / value[2][1] if value[2][1] != 0 else value[2][0]
        
        return d + (m / 60.0) + (s / 3600.0)


