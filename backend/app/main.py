from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path
from app.core.config import settings
from app.core.database import init_db
from app.api.v1.endpoints import sessions, images, compression, history, background, chat, openrouter_oauth, settings as settings_router
import logging
import os
import asyncio

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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
    version="1.0.0",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    lifespan=lifespan
)

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
app.include_router(history.router, prefix=settings.API_PREFIX)
app.include_router(background.router, prefix=f"{settings.API_PREFIX}/background", tags=["background"])
app.include_router(openrouter_oauth.router, prefix=f"{settings.API_PREFIX}/openrouter")
app.include_router(chat.router, prefix=f"{settings.API_PREFIX}/chat", tags=["chat"])
app.include_router(settings_router.router, prefix=settings.API_PREFIX)

# Serve frontend static files (if they exist)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time connection monitoring.
    Sends periodic ping messages to keep connection alive and detect disconnects.
    """
    await websocket.accept()
    logger.info(f"WebSocket client connected from {websocket.client}")
    
    try:
        while True:
            # Send ping every 10 seconds to keep connection alive
            await websocket.send_json({"type": "ping", "timestamp": asyncio.get_event_loop().time()})
            await asyncio.sleep(10)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from {websocket.client}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
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
