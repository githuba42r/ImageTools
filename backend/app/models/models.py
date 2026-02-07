from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Float, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Image(Base):
    __tablename__ = "images"
    
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    original_filename = Column(String, nullable=False)
    original_size = Column(Integer, nullable=False)
    current_path = Column(String, nullable=False)
    thumbnail_path = Column(String, nullable=True)
    current_size = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    format = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class History(Base):
    __tablename__ = "history"
    
    id = Column(String, primary_key=True, index=True)
    image_id = Column(String, ForeignKey("images.id"), nullable=False, index=True)
    operation_type = Column(String, nullable=False)
    operation_params = Column(Text, nullable=True)
    input_path = Column(String, nullable=False)
    output_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sequence = Column(Integer, nullable=False)


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    image_id = Column(String, ForeignKey("images.id"), nullable=False)
    model = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    total_cost = Column(Float, default=0.0)


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OpenRouterKey(Base):
    """
    Store OpenRouter API keys per session
    Keys are encrypted at rest and associated with browser sessions
    """
    __tablename__ = "openrouter_keys"
    
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True, unique=True)
    encrypted_api_key = Column(Text, nullable=False)  # Encrypted API key
    key_label = Column(String, nullable=True)  # Optional label from OpenRouter
    credits_remaining = Column(Float, nullable=True)  # Cache of remaining credits
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)


class UserSettings(Base):
    """
    Store user settings per session
    Includes selected AI model and other preferences
    """
    __tablename__ = "user_settings"
    
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True, unique=True)
    selected_model_id = Column(String, nullable=True)  # OpenRouter model ID (e.g., "google/gemini-2.0-flash-exp:free")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MobileAppPairing(Base):
    """
    Store mobile app pairings/links to sessions
    
    Authorization Flow:
    1. Initial pairing: shared_secret (2-min, single-use) validates device
    2. After validation: long_term_secret (90 days) for image uploads
    3. Refresh capability: refresh_secret (180 days) can renew long_term_secret
    """
    __tablename__ = "mobile_app_pairings"
    
    id = Column(String, primary_key=True, index=True)  # UUID
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    device_name = Column(String, nullable=True)  # Optional device identifier
    
    # Initial pairing secret (short-lived, single-use)
    shared_secret = Column(String, nullable=False, unique=True, index=True)  # 2-minute timeout
    used = Column(Boolean, default=False)  # Track if initial secret has been used
    
    # Long-term authorization (90 days)
    long_term_secret = Column(String, nullable=True, unique=True, index=True)  # For image uploads
    long_term_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Refresh capability (180 days)
    refresh_secret = Column(String, nullable=True, unique=True, index=True)  # Can renew long-term
    refresh_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Initial pairing expiry (2 min)


class BrowserAddonAuthorization(Base):
    """
    Store browser addon authorizations for screenshot uploads
    
    OAuth2-style Authorization Flow:
    1. User clicks "Connect Addon" in web UI -> generates registration_url
    2. User pastes URL in addon -> addon extracts authorization_code
    3. Addon exchanges code for access_token + refresh_token
    4. Addon uses access_token for screenshot uploads (Bearer token)
    5. When access_token expires, use refresh_token to get new one
    """
    __tablename__ = "browser_addon_authorizations"
    
    id = Column(String, primary_key=True, index=True)  # UUID
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    browser_name = Column(String, nullable=True)  # "firefox" or "chrome"
    addon_identifier = Column(String, nullable=True)  # Optional addon ID
    
    # Authorization code (short-lived, single-use, 5 minutes)
    authorization_code = Column(String, nullable=False, unique=True, index=True)
    code_used = Column(Boolean, default=False)
    code_expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Access token (30 days)
    access_token = Column(String, nullable=True, unique=True, index=True)
    access_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Refresh token (90 days, can renew access token)
    refresh_token = Column(String, nullable=True, unique=True, index=True)
    refresh_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
