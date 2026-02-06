from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any


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


class FlipRequest(BaseModel):
    direction: str = Field(..., description="Flip direction: horizontal or vertical")


class FlipResponse(BaseModel):
    image_id: str
    direction: str
    new_size: int
    width: int
    height: int
    image_url: str


# Resize Schemas

class ResizeRequest(BaseModel):
    width: int = Field(..., gt=0, description="Target width in pixels")
    height: int = Field(..., gt=0, description="Target height in pixels")


class ResizeResponse(BaseModel):
    image_id: str
    original_width: int
    original_height: int
    new_width: int
    new_height: int
    new_size: int
    image_url: str


# Background Removal Schemas

class BackgroundRemovalRequest(BaseModel):
    alpha_matting: bool = Field(default=False, description="Use alpha matting for better edge quality")
    alpha_matting_foreground_threshold: int = Field(default=240, ge=0, le=255, description="Foreground threshold (0-255)")
    alpha_matting_background_threshold: int = Field(default=10, ge=0, le=255, description="Background threshold (0-255)")
    model: Optional[str] = Field(default="u2net", description="rembg model (u2net, u2net_human_seg, isnet-general-use, isnet-anime)")


class BackgroundRemovalResponse(BaseModel):
    image_id: str
    original_size: int
    new_size: int
    format: str
    has_transparency: bool
    model_used: str
    compression_ratio: float
    width: int
    height: int
    image_url: str


# AI Chat Schemas

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str  # "user" or "assistant"
    content: str
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    image_id: str = Field(..., description="ID of the image to chat about")
    model: str = Field(default="google/gemini-2.0-flash-exp:free", description="OpenRouter model ID")


class ConversationResponse(BaseModel):
    id: str
    session_id: str
    image_id: str
    model: str
    created_at: datetime
    updated_at: datetime
    total_cost: float
    messages: List[MessageResponse] = []
    
    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="User session ID for API key retrieval")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID, or None for new conversation")
    image_id: str = Field(..., description="ID of the image to manipulate")
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    model: str = Field(default="google/gemini-2.0-flash-exp:free", description="OpenRouter model ID")
    api_key: Optional[str] = Field(None, description="OpenRouter API key (if not in env)")


class AIOperation(BaseModel):
    type: str = Field(..., description="Operation type: brightness, contrast, saturation, rotate, crop, resize, blur, sharpen, sepia, grayscale")
    params: Dict[str, Any] = Field(..., description="Operation parameters")


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    response: str
    operations: List[AIOperation] = []
    image_updated: bool = False
    new_image_url: Optional[str] = None
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    total_conversation_cost: float


class ModelInfo(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    context_length: Optional[int] = None
    pricing: Optional[Dict[str, float]] = None
    
    class Config:
        from_attributes = True


class ModelSearchResponse(BaseModel):
    models: List[ModelInfo]
    total: int


class CostSummary(BaseModel):
    conversation_cost: float
    monthly_cost: float
    monthly_limit: Optional[float] = None
    remaining_budget: Optional[float] = None

