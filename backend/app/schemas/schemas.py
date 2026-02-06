from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class SessionCreate(BaseModel):
    user_id: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    user_id: Optional[str]
    created_at: datetime
    expires_at: datetime
    
    class Config:
        from_attributes = True


class ImageUpload(BaseModel):
    session_id: str
    filename: str


class ImageResponse(BaseModel):
    id: str
    session_id: str
    original_filename: str
    original_size: int
    current_size: int
    width: int
    height: int
    format: str
    thumbnail_url: str
    image_url: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CompressionRequest(BaseModel):
    preset: str = Field(..., description="Preset name: email, web, web_hq, or custom")
    quality: Optional[int] = Field(None, ge=1, le=100)
    max_width: Optional[int] = Field(None, ge=100)
    max_height: Optional[int] = Field(None, ge=100)
    target_size_kb: Optional[int] = Field(None, ge=10)
    format: Optional[str] = Field(None, pattern="^(JPEG|PNG|WEBP)$")


class CompressionResponse(BaseModel):
    image_id: str
    original_size: int
    compressed_size: int
    compression_ratio: float
    image_url: str


class HistoryResponse(BaseModel):
    id: str
    image_id: str
    operation_type: str
    operation_params: Optional[str]
    file_size: int
    created_at: datetime
    sequence: int
    
    class Config:
        from_attributes = True


class UndoResponse(BaseModel):
    image_id: str
    reverted_to_sequence: int
    current_size: int
    image_url: str


class RotateRequest(BaseModel):
    degrees: int = Field(..., description="Rotation degrees: 90, 180, or 270")


class RotateResponse(BaseModel):
    image_id: str
    degrees: int
    new_size: int
    width: int
    height: int
    image_url: str
