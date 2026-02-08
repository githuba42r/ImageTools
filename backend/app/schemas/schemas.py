from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any


class SessionCreate(BaseModel):
    user_id: Optional[str] = None  # Legacy field
    username: Optional[str] = None  # Remote-User from Authelia
    display_name: Optional[str] = None  # Remote-Name from Authelia
    custom_session_id: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    user_id: Optional[str]
    username: Optional[str]
    display_name: Optional[str]
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


class ModelRecommendation(BaseModel):
    """Recommended model for operations the current model cannot perform"""
    model_id: str = Field(..., description="OpenRouter model ID")
    model_name: str = Field(..., description="Display name of the model")
    reason: str = Field(..., description="Why this model is recommended")
    capabilities: List[str] = Field(..., description="What this model can do")
    cost_prompt: float = Field(..., description="Cost per 1M prompt tokens in USD")
    cost_completion: float = Field(..., description="Cost per 1M completion tokens in USD")
    context_length: Optional[int] = Field(None, description="Context window size")


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    response: str
    operations: List[AIOperation] = []
    model_recommendations: List[ModelRecommendation] = []  # New field for model suggestions
    image_updated: bool = False
    new_image_url: Optional[str] = None
    history_sequence: Optional[int] = None  # Sequence number of the history entry for this version
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


# Mobile App Pairing Schemas

class MobileAppPairingCreate(BaseModel):
    session_id: str = Field(..., description="Session ID to link the mobile app to")
    device_name: Optional[str] = Field(None, description="Optional device identifier")


class MobileAppPairingResponse(BaseModel):
    id: str
    session_id: str
    device_name: Optional[str]
    shared_secret: str
    is_active: bool
    used: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class QRCodeDataResponse(BaseModel):
    """QR code data for mobile app linking"""
    instance_url: str = Field(..., description="URL of the ImageTools instance")
    shared_secret: str = Field(..., description="Shared secret for authentication")
    pairing_id: str = Field(..., description="Pairing ID")
    session_id: str = Field(..., description="Session ID this pairing is linked to")


class ValidateSecretRequest(BaseModel):
    """Request to validate a shared secret"""
    shared_secret: str = Field(..., description="Shared secret to validate")
    device_model: Optional[str] = Field(None, description="Device model (e.g. Samsung Galaxy S21)")
    device_manufacturer: Optional[str] = Field(None, description="Device manufacturer (e.g. Samsung)")
    device_owner: Optional[str] = Field(None, description="Device owner name or email")
    os_version: Optional[str] = Field(None, description="OS version (e.g. Android 13)")
    app_version: Optional[str] = Field(None, description="ImageTools app version")


class ValidateSecretResponse(BaseModel):
    """Response from secret validation with long-term authorization"""
    valid: bool = Field(..., description="Whether the secret is valid")
    pairing_id: str = Field(..., description="Pairing ID")
    session_id: str = Field(..., description="Session ID")
    device_name: Optional[str] = Field(None, description="Device name")
    device_model: Optional[str] = Field(None, description="Device model")
    device_manufacturer: Optional[str] = Field(None, description="Device manufacturer")
    device_owner: Optional[str] = Field(None, description="Device owner")
    os_version: Optional[str] = Field(None, description="OS version")
    app_version: Optional[str] = Field(None, description="App version")
    long_term_secret: str = Field(..., description="Long-term secret for uploads (90 days)")
    refresh_secret: str = Field(..., description="Refresh secret for renewal (180 days)")
    long_term_expires_at: datetime = Field(..., description="Long-term secret expiration")
    refresh_expires_at: datetime = Field(..., description="Refresh secret expiration")


class MobileImageUploadRequest(BaseModel):
    shared_secret: str = Field(..., description="Shared secret from QR code pairing")
    filename: str = Field(..., description="Original filename")


class MobileImageUploadResponse(BaseModel):
    image_id: str
    filename: str
    size: int
    width: int
    height: int
    format: str
    thumbnail_url: str
    image_url: str
    uploaded_at: datetime


class RefreshSecretRequest(BaseModel):
    """Request to refresh long-term secret"""
    refresh_secret: str = Field(..., description="Refresh secret for renewing")


class RefreshSecretResponse(BaseModel):
    """Response from refresh operation"""
    long_term_secret: str = Field(..., description="New long-term secret")
    long_term_expires_at: datetime = Field(..., description="New expiration date")


class ValidateAuthRequest(BaseModel):
    """Request to validate current auth status"""
    long_term_secret: str = Field(..., description="Long-term secret to validate")


class ValidateAuthResponse(BaseModel):
    """Response from auth validation"""
    valid: bool = Field(..., description="Whether auth is valid")
    expires_at: Optional[datetime] = Field(None, description="Expiration date if valid")
    needs_refresh: bool = Field(False, description="True if nearing expiration")


class PairedDeviceInfo(BaseModel):
    """Information about a paired device"""
    id: str
    device_name: Optional[str]
    device_model: Optional[str]
    device_manufacturer: Optional[str]
    device_owner: Optional[str]
    os_version: Optional[str]
    app_version: Optional[str]
    created_at: datetime
    last_used_at: Optional[datetime]
    long_term_expires_at: Optional[datetime]
    is_active: bool
    
    class Config:
        from_attributes = True


# Browser Addon Authorization Schemas

class AddonAuthorizationCreate(BaseModel):
    """Request to create a new addon authorization"""
    session_id: str = Field(..., description="Session ID to link the addon to")
    browser_name: Optional[str] = Field(None, description="Browser type: firefox or chrome")
    addon_identifier: Optional[str] = Field(None, description="Optional addon ID")


class AddonAuthorizationResponse(BaseModel):
    """Response with authorization details"""
    id: str
    session_id: str
    browser_name: Optional[str]
    authorization_code: str
    registration_url: str
    code_expires_at: datetime
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class AddonTokenExchangeRequest(BaseModel):
    """Request to exchange authorization code for tokens"""
    authorization_code: str = Field(..., description="Authorization code from registration URL")
    browser_name: Optional[str] = Field(None, description="Browser name (Chrome, Firefox, etc.)")
    browser_version: Optional[str] = Field(None, description="Browser version")
    os_name: Optional[str] = Field(None, description="Operating system")
    user_agent: Optional[str] = Field(None, description="Full user agent string")


class AddonTokenExchangeResponse(BaseModel):
    """Response with access and refresh tokens"""
    access_token: str = Field(..., description="Access token for screenshot uploads (30 days)")
    refresh_token: str = Field(..., description="Refresh token for renewal (90 days)")
    access_expires_at: datetime = Field(..., description="Access token expiration")
    refresh_expires_at: datetime = Field(..., description="Refresh token expiration")
    session_id: str = Field(..., description="Session ID this authorization is linked to")
    instance_url: str = Field(..., description="Image Tools instance URL")


class AddonRefreshTokenRequest(BaseModel):
    """Request to refresh access token"""
    refresh_token: str = Field(..., description="Refresh token for renewing")


class AddonRefreshTokenResponse(BaseModel):
    """Response from token refresh"""
    access_token: str = Field(..., description="New access token")
    access_expires_at: datetime = Field(..., description="New expiration date")


class AddonValidateTokenRequest(BaseModel):
    """Request to validate current token"""
    access_token: str = Field(..., description="Access token to validate")


class AddonValidateTokenResponse(BaseModel):
    """Response from token validation"""
    valid: bool = Field(..., description="Whether token is valid")
    expires_at: Optional[datetime] = Field(None, description="Expiration date if valid")
    needs_refresh: bool = Field(False, description="True if nearing expiration (within 3 days)")
    session_id: Optional[str] = Field(None, description="Session ID if valid")


class AddonScreenshotUploadResponse(BaseModel):
    """Response from screenshot upload"""
    image_id: str
    filename: str
    size: int
    width: int
    height: int
    format: str
    thumbnail_url: str
    image_url: str
    uploaded_at: datetime


class ConnectedAddonInfo(BaseModel):
    """Information about a connected addon"""
    id: str
    browser_name: Optional[str]
    browser_version: Optional[str]
    os_name: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    last_used_at: Optional[datetime]
    access_expires_at: Optional[datetime]
    is_active: bool
    
    class Config:
        from_attributes = True


