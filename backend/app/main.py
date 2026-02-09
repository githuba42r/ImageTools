from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path
import logging
import os
import asyncio
import json

# Custom logging filter to exclude health check requests
class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find('/health') == -1

# Import settings after defining the filter
from app.core.config import settings
from app.core.database import init_db
from app.core.websocket_manager import manager as ws_manager
from app.middleware import InternalAuthMiddleware
from app.api.v1.endpoints import sessions, images, compression, history, background, chat, openrouter_oauth, settings as settings_router, mobile, addon, profiles

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Apply health check filter to uvicorn access logs
logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())

# Load version information from version.json
def load_version_info():
    """Load version information from version.json file."""
    try:
        version_file = Path(__file__).parent.parent.parent / "version.json"
        with open(version_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load version.json: {e}")
        return {"version": "1.2.0", "buildDate": "unknown", "versionCode": 3}

VERSION_INFO = load_version_info()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Image Tools API...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    logger.info("Shutting down Image Tools API...")


# Create FastAPI app
app = FastAPI(
    title="Image Tools API",
    description="Backend API for image manipulation and compression",
    version=VERSION_INFO["version"],
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    lifespan=lifespan
)

# Add Internal Authentication Middleware (must be added before CORS)
# This provides defense-in-depth security for Hardened (B) deployments
app.add_middleware(InternalAuthMiddleware)

# Configure CORS
if settings.CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS enabled for origins: {settings.cors_origins_list}")

# Include routers
app.include_router(sessions.router, prefix=settings.API_PREFIX)
app.include_router(images.router, prefix=settings.API_PREFIX)
app.include_router(compression.router, prefix=settings.API_PREFIX)
app.include_router(profiles.router, prefix=settings.API_PREFIX)
app.include_router(history.router, prefix=settings.API_PREFIX)
app.include_router(background.router, prefix=f"{settings.API_PREFIX}/background", tags=["background"])
app.include_router(openrouter_oauth.router, prefix=f"{settings.API_PREFIX}/openrouter")
app.include_router(chat.router, prefix=f"{settings.API_PREFIX}/chat", tags=["chat"])
app.include_router(settings_router.router, prefix=settings.API_PREFIX)
app.include_router(mobile.router, prefix=f"{settings.API_PREFIX}/mobile", tags=["mobile"])
app.include_router(addon.router, prefix=f"{settings.API_PREFIX}/addon", tags=["addon"])

# Serve frontend static files (if they exist)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/version")
async def get_version():
    """
    Get version information.
    
    This endpoint is unprotected and returns the current version,
    build date, and version code of the backend service.
    """
    return {
        "version": VERSION_INFO["version"],
        "buildDate": VERSION_INFO["buildDate"],
        "versionCode": VERSION_INFO.get("versionCode", 0),
        "service": "ImageTools Backend API"
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str = Query(...)):
    """
    WebSocket endpoint for real-time updates.
    Sends periodic pings and broadcasts session-specific events (e.g. new images from mobile).
    
    Query Parameters:
        session_id: The session ID to subscribe to
    """
    await ws_manager.connect(websocket, session_id)
    logger.info(f"WebSocket client connected for session {session_id}")
    
    try:
        while True:
            # Send ping every 10 seconds to keep connection alive
            await websocket.send_json({"type": "ping", "timestamp": asyncio.get_event_loop().time()})
            await asyncio.sleep(10)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for session {session_id}")
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)
        try:
            await websocket.close()
        except:
            pass


if frontend_dist.exists():
    # Mount static files for assets
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    
    # Serve index.html for SPA routes (catch-all - must be last!)
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve frontend application for non-API routes."""
        # If it's an API route or health check, let it fall through to 404
        if full_path.startswith("api/") or full_path.startswith("uploads/") or full_path == "health":
            return {"detail": "Not Found"}
        
        # Check if requesting a specific file
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        
        # Default to index.html for SPA routing
        return FileResponse(frontend_dist / "index.html")
else:
    logger.warning("Frontend build not found. Only API endpoints will be available.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
