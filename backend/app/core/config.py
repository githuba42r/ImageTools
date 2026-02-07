from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Server
    SERVER_PORT: int = 8081
    SERVER_HOST: str = "0.0.0.0"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Mobile/External Access
    # URL that mobile devices and external clients will use to connect to this backend
    # Example: http://10.0.1.97:8000 or https://yourdomain.com
    INSTANCE_URL: str = "http://localhost:8000"
    
    # Session
    SESSION_EXPIRY_DAYS: int = 7
    MAX_IMAGES_PER_SESSION: int = 5
    SESSION_SECRET_KEY: str = "change-this-secret-key-in-production"
    
    # Upload
    MAX_UPLOAD_SIZE_MB: int = 20
    CHUNK_SIZE_MB: int = 5
    MAX_PARALLEL_UPLOADS: int = 3
    ALLOWED_EXTENSIONS: str = "jpg,jpeg,png,gif,bmp,webp,tiff"
    
    # Storage
    STORAGE_PATH: str = "./storage"
    TEMP_STORAGE_PATH: str = "./storage/temp"
    DATABASE_URL: str = "sqlite+aiosqlite:///./storage/imagetools.db"
    
    # Compression Presets
    EMAIL_MAX_WIDTH: int = 800
    EMAIL_MAX_HEIGHT: int = 800
    EMAIL_QUALITY: int = 85
    EMAIL_TARGET_SIZE_KB: int = 500
    EMAIL_FORMAT: str = "JPEG"
    
    WEB_MAX_WIDTH: int = 1920
    WEB_MAX_HEIGHT: int = 1920
    WEB_QUALITY: int = 90
    WEB_TARGET_SIZE_KB: int = 500
    WEB_FORMAT: str = "JPEG"
    
    WEB_HQ_MAX_WIDTH: int = 2560
    WEB_HQ_MAX_HEIGHT: int = 2560
    WEB_HQ_QUALITY: int = 95
    WEB_HQ_TARGET_SIZE_KB: int = 1000
    WEB_HQ_FORMAT: str = "WEBP"
    
    # Image Processing
    THUMBNAIL_SIZE: int = 300
    THUMBNAIL_QUALITY: int = 80
    UNDO_STACK_LIMIT: int = 10
    
    # Cleanup
    CLEANUP_SCHEDULE_CRON: str = "0 2 * * *"
    CLEANUP_ENABLED: bool = True
    
    # CORS
    CORS_ENABLED: bool = True
    CORS_ORIGINS: str = "*"  # Allow all origins for development. In production, set specific origins.
    
    # OpenRouter / AI Configuration
    OPENROUTER_APP_NAME: str = "ImageTools"
    # In production, set OPENROUTER_APP_URL to match your deployment URL
    # Example: https://yourdomain.com or http://your-ip:8082
    # The OAuth callback URL will automatically be: {OPENROUTER_APP_URL}/oauth/callback
    OPENROUTER_APP_URL: str = "http://localhost:5173"
    OPENROUTER_API_KEY: str = ""  # Optional fallback API key
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]
    
    @property
    def cors_origins_list(self) -> List[str]:
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def openrouter_oauth_callback_url(self) -> str:
        """Derive OAuth callback URL from app URL"""
        return f"{self.OPENROUTER_APP_URL.rstrip('/')}/oauth/callback"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
