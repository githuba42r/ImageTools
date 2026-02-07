# IMAGE TOOLS APP - DETAILED IMPLEMENTATION STRATEGY

**Version:** 1.1  
**Date:** February 6, 2026  
**Project:** Image Tools - Web-based Image Manipulation Application

---

## TABLE OF CONTENTS

1. Executive Summary
2. Project Overview
3. Architecture
4. Technology Stack
5. Environment Configuration
6. Database Schema
7. API Specifications
8. Implementation Stages
9. Timeline and Milestones
10. Deliverables

---

## 1. EXECUTIVE SUMMARY

Image Tools is a dockerized web application designed for quick image manipulation, with a primary focus on compressing large phone camera images (5-8MB) to email-friendly sizes (<500KB). The application features a Vue.js frontend and Python FastAPI backend, deployed as a single container behind a reverse proxy.

### Key Features:
- Multi-image upload with chunked transfer and parallel processing
- Intelligent compression with presets (Email/Web/Custom)
- Bulk operations (compress all, download selected as ZIP)
- Per-image undo functionality (10 operations max)
- Session management with auto-cleanup
- Thumbnail gallery with configurable sizes
- Download options (individual, clipboard, ZIP)
- TUI Image Editor integration
- AI-powered background removal
- AI chatbot for image manipulation
- Settings management with OAuth2 PKCE enrollment
- Optional multi-user support via Authelia cookie detection

### Development Approach:
- 4 implementation stages with clear deliverables
- Modular architecture (components max 400-600 lines)
- Session-based storage with auto-cleanup (7 days default)
- Single-port deployment (port 8000) for simplified reverse proxy setup

---

## 2. PROJECT OVERVIEW

### Problem Statement
Users frequently need to process high-resolution phone camera images for email or web use. Current solutions are either:
- Too complex (professional image editing software)
- Too limited (basic online compressors)
- Lack privacy (upload to third-party services with data retention)

### Solution
A self-hosted, privacy-focused image manipulation tool that provides:
1. Speed: Quick drag-and-drop workflow
2. Privacy: No long-term storage, session-based processing
3. Power: Professional features (AI, advanced editor) when needed
4. Simplicity: One-click presets for common tasks

### Target Users
- Primary: Personal use for the operator
- Secondary: Small teams behind Authelia/Traefik authentication

### Success Criteria
- Upload to Compress to Download workflow in less than 30 seconds
- 5-8MB images reduced to less than 500KB consistently
- All features accessible without authentication
- Docker deployment in less than 10 minutes

---

## 3. ARCHITECTURE

### System Architecture Diagram

```
+---------------------------------------------------------------+
|                 Reverse Proxy (Production)                     |
|               Traefik + Authelia (Optional)                    |
|              Passes X-Forwarded-User Cookie                    |
+---------------------------+-----------------------------------+
                            | Port 8000
+---------------------------+-----------------------------------+
|                    Docker Container                            |
|  +----------------------------------------------------------+  |
|  |               Nginx (Port 8000)                          |  |
|  |  Routes:                                                 |  |
|  |    /app/*     -> Static Vue.js SPA                      |  |
|  |    /api/v1/*  -> FastAPI Backend (Proxy to :8001)      |  |
|  +----------------------------------------------------------+  |
|                                                                |
|  +------------------+         +---------------------------+    |
|  | Vue.js Frontend  |         | FastAPI Backend           |    |
|  | (Static Files)   |<------->| (Port 8001)              |    |
|  |                  |  REST   |                           |    |
|  | - Image Gallery  |   API   | - Upload Handler          |    |
|  | - TUI Editor     |         | - Compression Engine      |    |
|  | - Settings Modal |         | - Session Manager         |    |
|  | - AI Components  |         | - AI Integration          |    |
|  +------------------+         +-------------+-------------+    |
|                                             |                  |
|  +------------------------------------------+---------------+  |
|  |          Volume Mount: /settings                        |  |
|  |  +----------------+  +-------------------------------+  |  |
|  |  | SQLite DB      |  | Temp Image Storage            |  |  |
|  |  | - sessions     |  | - /settings/temp/             |  |  |
|  |  | - images       |  | - Chunked uploads             |  |  |
|  |  | - history      |  | - Processed images            |  |  |
|  |  | - settings     |  | - Auto-cleanup after expiry   |  |  |
|  |  | - users        |  |                               |  |  |
|  |  +----------------+  +-------------------------------+  |  |
|  +---------------------------------------------------------+  |
+---------------------------------------------------------------+
                            |
         +------------------+------------------+
         |   OpenRouter.ai API                 |
         |   - OAuth2 PKCE Auth                |
         |   - AI Chat (Gemini 3 Flash)       |
         |   - Image Manipulation Assistance   |
         +-------------------------------------+
         |   rembg Library (Local)             |
         |   - Background Removal              |
         |   - No API costs, offline capable   |
         +-------------------------------------+
```

### Data Flow Diagrams

#### Upload Flow
```
User Browser -> Chunked Upload -> FastAPI -> Temp Storage -> SQLite Metadata
                                      |
                                Thumbnail Generation
                                      |
                                Return Image ID & URL
```

#### Compression Flow
```
User Request -> FastAPI -> Load Image -> Apply Preset -> Save New Version
                               |
                        Update History Stack
                               |
                        Return Compressed Image
```

#### Undo Flow
```
User Undo -> FastAPI -> Query History -> Load Previous Version -> Replace Current
                            |
                     Delete Latest Version
```

---

## 4. TECHNOLOGY STACK

### Frontend Stack

| Component          | Technology           | Version | Purpose                          |
|--------------------|---------------------|---------|----------------------------------|
| Framework          | Vue.js              | 3.x     | Reactive UI framework            |
| Build Tool         | Vite                | 5.x     | Fast dev server & bundler        |
| State Management   | Pinia               | 2.x     | Centralized state store          |
| Routing            | Vue Router          | 4.x     | SPA routing                      |
| HTTP Client        | Axios               | 1.x     | API communication                |
| Styling            | Tailwind CSS        | 3.x     | Utility-first CSS                |
| Image Editor       | TUI Image Editor    | 3.x     | Full-featured image editor       |
| Notifications      | Vue Toastification  | 2.x     | Toast notifications              |
| Icons              | Heroicons           | 2.x     | SVG icon library                 |

### Backend Stack

| Component          | Technology    | Version | Purpose                          |
|--------------------|--------------|---------|----------------------------------|
| Framework          | FastAPI      | 0.110+  | Async web framework              |
| ASGI Server        | Uvicorn      | 0.27+   | ASGI server                      |
| Process Manager    | Gunicorn     | 21+     | Production process manager       |
| ORM                | SQLAlchemy   | 2.0+    | Database ORM                     |
| Database           | SQLite3      | 3.x     | Embedded database                |
| Image Processing   | Pillow       | 10.x    | Image manipulation               |
| Validation         | Pydantic     | 2.x     | Data validation                  |
| Environment        | python-dotenv| 1.x     | Environment variables            |
| HTTP Client        | httpx        | 0.27+   | Async HTTP for AI APIs           |
| OAuth              | authlib      | 1.3+    | OAuth2 PKCE implementation       |
| Background Removal | rembg        | 2.0+    | AI background removal (Stage 3)  |
| ML Runtime         | onnxruntime  | 1.16+   | ONNX model inference (CPU/GPU)   |
| OpenAI SDK         | openai       | 1.12+   | OpenRouter API client (Stage 4)  |
| Token Counter      | tiktoken     | 0.5+    | Token counting for cost tracking |
| Encryption         | cryptography | 42.0+   | API key encryption/decryption    |

### DevOps & Deployment

| Component           | Technology | Purpose                              |
|---------------------|-----------|--------------------------------------|
| Container           | Docker    | Multi-stage builds                   |
| Web Server          | Nginx     | Static file serving & reverse proxy  |
| Version Control     | Git       | Source control                       |
| Python Env          | venv      | Virtual environment isolation        |
| Package Manager     | npm       | Dependency management                |

### Development Tools

| Component          | Technology | Purpose                    |
|--------------------|-----------|----------------------------|
| Linting (JS)       | ESLint    | JavaScript code quality    |
| Formatting (JS)    | Prettier  | JavaScript code formatting |
| Linting (Python)   | Flake8    | Python code quality        |
| Formatting (Python)| Black     | Python code formatting     |
| Testing (Frontend) | Vitest    | Vue component testing      |
| Testing (Backend)  | Pytest    | Python unit testing        |

---

## 5. ENVIRONMENT CONFIGURATION

### .env.example

```bash
# ============================================================================
# IMAGE TOOLS - ENVIRONMENT CONFIGURATION
# ============================================================================

# ----------------------------------------------------------------------------
# Server Configuration
# ----------------------------------------------------------------------------
SERVER_PORT=8000
SERVER_HOST=0.0.0.0
API_PREFIX=/api/v1
APP_PREFIX=/app
DEBUG=false
LOG_LEVEL=INFO

# ----------------------------------------------------------------------------
# Session Configuration
# ----------------------------------------------------------------------------
SESSION_EXPIRY_DAYS=7
MAX_IMAGES_PER_SESSION=5
SESSION_SECRET_KEY=your-secret-key-here-change-in-production

# ----------------------------------------------------------------------------
# Upload Configuration
# ----------------------------------------------------------------------------
MAX_UPLOAD_SIZE_MB=20
CHUNK_SIZE_MB=5
MAX_PARALLEL_UPLOADS=3
ALLOWED_EXTENSIONS=jpg,jpeg,png,gif,bmp,webp,tiff

# ----------------------------------------------------------------------------
# Storage Configuration
# ----------------------------------------------------------------------------
STORAGE_PATH=/settings
TEMP_STORAGE_PATH=/settings/temp
DATABASE_URL=sqlite:////settings/imagetools.db

# ----------------------------------------------------------------------------
# Compression Presets
# ----------------------------------------------------------------------------
# Email Preset
EMAIL_MAX_WIDTH=800
EMAIL_MAX_HEIGHT=800
EMAIL_QUALITY=85
EMAIL_TARGET_SIZE_KB=500
EMAIL_FORMAT=JPEG

# Web Preset
WEB_MAX_WIDTH=1920
WEB_MAX_HEIGHT=1920
WEB_QUALITY=90
WEB_TARGET_SIZE_KB=500
WEB_FORMAT=JPEG

# High Quality Web Preset
WEB_HQ_MAX_WIDTH=2560
WEB_HQ_MAX_HEIGHT=2560
WEB_HQ_QUALITY=95
WEB_HQ_TARGET_SIZE_KB=1000
WEB_HQ_FORMAT=WEBP

# ----------------------------------------------------------------------------
# Image Processing
# ----------------------------------------------------------------------------
THUMBNAIL_SIZE=300
THUMBNAIL_QUALITY=80
UNDO_STACK_LIMIT=10

# ----------------------------------------------------------------------------
# AI Configuration (OpenRouter.ai - Stages 3-4)
# ----------------------------------------------------------------------------
ENABLE_AI_FEATURES=false

# OpenRouter API Configuration
OPENROUTER_API_URL=https://openrouter.ai/api/v1
OPENROUTER_OAUTH_CALLBACK_URL=http://localhost:8000/app/oauth/callback
OPENROUTER_ENCRYPTION_KEY=

# Background Removal (Stage 3)
BACKGROUND_REMOVAL_METHOD=rembg
REMBG_MODEL=u2net
ENABLE_GPU_ACCELERATION=false

# AI Chat Configuration (Stage 4)
DEFAULT_AI_CHAT_MODEL=google/gemini-3-flash-preview
AI_CHAT_MODEL_CUSTOM=

# Cost Controls
MAX_COST_PER_REQUEST=0.10
MONTHLY_COST_LIMIT=10.00
ENABLE_COST_TRACKING=true
SHOW_COST_WARNINGS=true

# AI Rate Limiting
AI_MAX_REQUESTS_PER_MINUTE=30
AI_TIMEOUT_SECONDS=60

# ----------------------------------------------------------------------------
# Multi-User Support (Authelia Integration)
# ----------------------------------------------------------------------------
ENABLE_MULTI_USER=false
AUTHELIA_COOKIE_NAME=authelia_session
USER_HEADER_NAME=X-Forwarded-User

# ----------------------------------------------------------------------------
# Cleanup Configuration
# ----------------------------------------------------------------------------
CLEANUP_SCHEDULE_CRON=0 2 * * *
# Daily at 2 AM (format: minute hour day month weekday)
CLEANUP_ENABLED=true

# ----------------------------------------------------------------------------
# CORS Configuration (Development Only)
# ----------------------------------------------------------------------------
CORS_ENABLED=true
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# ----------------------------------------------------------------------------
# OAuth2 PKCE Configuration
# ----------------------------------------------------------------------------
OAUTH_STATE_EXPIRY_MINUTES=10
OAUTH_CODE_VERIFIER_LENGTH=128

# ----------------------------------------------------------------------------
# Frontend Configuration
# ----------------------------------------------------------------------------
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_TITLE=Image Tools
VITE_MAX_FILE_SIZE_MB=20
```

---

## 6. DATABASE SCHEMA

### Tables Overview

1. users - User/session pseudo accounts
2. sessions - Session management with expiry
3. images - Image metadata and storage info
4. image_history - Version history for undo functionality
5. settings - User/global settings including AI configuration
6. oauth_states - Temporary OAuth2 PKCE state storage

### SQLAlchemy Models

#### users Table
```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)  # UUID
    username = Column(String, unique=True, nullable=True)  # From Authelia
    is_guest = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sessions = relationship("Session", back_populates="user")
    settings = relationship("Settings", back_populates="user")
```

#### sessions Table
```python
class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True)  # UUID
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_active = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    images = relationship("Image", back_populates="session")
```

#### images Table
```python
class Image(Base):
    __tablename__ = "images"
    
    id = Column(String, primary_key=True)  # UUID
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    original_filename = Column(String, nullable=False)
    current_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    thumbnail_path = Column(String, nullable=True)
    
    # Metadata
    width = Column(Integer)
    height = Column(Integer)
    format = Column(String)
    size_bytes = Column(Integer)
    mime_type = Column(String)
    
    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="images")
    history = relationship("ImageHistory", back_populates="image")
```

#### image_history Table
```python
class ImageHistory(Base):
    __tablename__ = "image_history"
    
    id = Column(String, primary_key=True)  # UUID
    image_id = Column(String, ForeignKey("images.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    operation_type = Column(String, nullable=False)
    operation_params = Column(JSON, nullable=True)
    file_path = Column(String, nullable=False)
    
    # Image metadata at this version
    width = Column(Integer)
    height = Column(Integer)
    size_bytes = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    image = relationship("Image", back_populates="history")
```

#### settings Table
```python
class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(String, primary_key=True)  # UUID
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Display Settings
    thumbnail_size = Column(String, default="medium")  # small, medium, large
    default_download_format = Column(String, default="original")  # original, jpeg, png, webp
    
    # AI Settings (Stages 3-4)
    ai_enabled = Column(Boolean, default=False)
    openrouter_api_key_encrypted = Column(String, nullable=True)
    openrouter_connected = Column(Boolean, default=False)
    
    # Background Removal Settings (Stage 3)
    background_removal_method = Column(String, default="rembg")  # rembg, removebg
    rembg_model = Column(String, default="u2net")  # u2net, u2net_human_seg, isnet-general-use
    
    # AI Chat Settings (Stage 4)
    ai_chat_model = Column(String, default="google/gemini-3-flash-preview")
    ai_chat_model_custom = Column(String, nullable=True)
    
    # Cost Controls
    max_cost_per_request = Column(Float, default=0.10)
    monthly_cost_limit = Column(Float, default=10.00)
    current_month_spend = Column(Float, default=0.00)
    show_cost_warnings = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="settings")
```

#### oauth_states Table
```python
class OAuthState(Base):
    __tablename__ = "oauth_states"
    
    id = Column(String, primary_key=True)  # UUID
    state = Column(String, unique=True, nullable=False)
    code_verifier = Column(String, nullable=False)
    user_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
```

### Database Indexes

```sql
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX idx_images_session_id ON images(session_id);
CREATE INDEX idx_image_history_image_id ON image_history(image_id);
CREATE INDEX idx_image_history_version ON image_history(image_id, version_number);
CREATE INDEX idx_oauth_states_state ON oauth_states(state);
CREATE INDEX idx_oauth_states_expires_at ON oauth_states(expires_at);
```

---

## 7. API SPECIFICATIONS

### Base URL Structure
- Development: http://localhost:8000/api/v1
- Production: https://yourdomain.com/api/v1

### Standard Response Format

Success Response:
```json
{
  "success": true,
  "data": {},
  "error": null,
  "timestamp": "2026-02-06T10:30:00Z"
}
```

Error Response:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {}
  },
  "timestamp": "2026-02-06T10:30:00Z"
}
```

### Core Endpoints Summary

#### Health & Status
- GET /health - Health check

#### Session Management
- POST /session - Create new session
- GET /session/{session_id} - Get session details
- DELETE /session/{session_id} - Delete session

#### Upload (Chunked)
- POST /upload/initiate - Start chunked upload
- POST /upload/{upload_id}/chunk/{chunk_index} - Upload chunk
- POST /upload/{upload_id}/complete - Complete upload
- DELETE /upload/{upload_id} - Cancel upload

#### Image Operations
- GET /images/{image_id} - Get full image
- GET /images/{image_id}/thumbnail - Get thumbnail
- GET /images/{image_id}/metadata - Get metadata
- DELETE /images/{image_id} - Delete image

#### Compression
- POST /images/{image_id}/compress - Compress single image
- POST /images/bulk-compress - Compress multiple images

#### Download
- GET /images/{image_id}/download - Download single image
- POST /images/download-zip - Download multiple as ZIP
- GET /images/{image_id}/clipboard - Get clipboard data

#### History & Undo
- GET /images/{image_id}/history - Get version history
- POST /images/{image_id}/undo - Undo last operation

#### Settings
- GET /settings - Get current settings
- PUT /settings - Update settings
- POST /settings/ai/enroll - Start OAuth enrollment
- POST /settings/ai/callback - OAuth callback handler
- DELETE /settings/ai - Clear AI credentials
- GET /settings/ai/models - List available AI models
- PUT /settings/ai/models - Update AI model selections

#### Editor (Stage 2)
- POST /images/{image_id}/edit - Apply editor operations

#### AI Background Removal (Stage 3)
- POST /images/{image_id}/remove-background - Remove background

#### AI Chat (Stage 4)
- POST /images/{image_id}/ai-chat - Send chat message
- GET /images/{image_id}/ai-chat/{conversation_id} - Get chat history
- DELETE /images/{image_id}/ai-chat/{conversation_id} - Clear chat

---

## 8. IMPLEMENTATION STAGES

---

### STAGE 1: CORE MVP - Upload, Compression & Download

**Duration:** 10-14 days  
**Priority:** Critical  
**Dependencies:** None

#### Goals
- Functional multi-image upload with chunking
- Image compression with presets
- Bulk operations
- Per-image undo (10 operations max)
- Session management with auto-cleanup
- Thumbnail gallery with configurable sizes
- Download options

#### Backend Tasks (Days 1-7)

**Day 1: Project Setup**
Files to create:
- backend/main.py
- backend/app/config.py
- backend/app/database.py
- backend/requirements.txt
- .env.example
- .gitignore

Deliverables:
- FastAPI app runs on localhost:8000
- Environment configuration loaded
- SQLite database initialized
- Health check endpoint working

**Day 1-2: Database Models**
Files to create:
- backend/app/models/user.py
- backend/app/models/session.py
- backend/app/models/image.py
- backend/app/models/history.py
- backend/app/models/settings.py

Deliverables:
- All database tables created
- Relationships working
- Basic CRUD operations tested

**Day 2: Session Management**
Files to create:
- backend/app/services/session_service.py
- backend/app/services/user_service.py
- backend/app/api/v1/endpoints/session.py
- backend/app/schemas/session.py

Deliverables:
- Session create/get/delete endpoints
- Session expiry logic
- Authelia cookie detection

**Day 2-3: File Storage**
Files to create:
- backend/app/core/storage.py
- backend/app/core/cleanup.py

Deliverables:
- File storage to /settings/temp/
- Chunked file handling
- Cleanup functionality

**Day 3-4: Chunked Upload**
Files to create:
- backend/app/services/upload_service.py
- backend/app/api/v1/endpoints/upload.py
- backend/app/schemas/upload.py

Deliverables:
- Chunked upload initiate endpoint
- Chunk upload endpoint
- Upload complete endpoint
- Upload cancellation

**Day 4-5: Image Processing & Compression**
Files to create:
- backend/app/services/image_service.py
- backend/app/services/compression_service.py
- backend/app/services/thumbnail_service.py
- backend/app/api/v1/endpoints/images.py
- backend/app/api/v1/endpoints/compression.py
- backend/app/schemas/image.py
- backend/app/schemas/compression.py

Deliverables:
- Image metadata extraction
- Thumbnail generation
- Compression with presets (Email/Web/Web HQ)
- Bulk compression
- Image serving endpoints

**Day 5-6: History & Undo**
Files to create:
- backend/app/services/history_service.py
- backend/app/api/v1/endpoints/history.py
- backend/app/schemas/history.py

Deliverables:
- Version history tracking
- Undo functionality (10 operations max)
- History retrieval endpoint

**Day 6-7: Download & ZIP**
Files to create:
- backend/app/services/download_service.py
- backend/app/api/v1/endpoints/download.py

Deliverables:
- Single image download
- Clipboard data endpoint
- ZIP download with selection

**Day 7: Cleanup & Testing**
Files to create:
- backend/app/tests/test_upload.py
- backend/app/tests/test_compression.py
- backend/app/tests/test_session.py
- backend/app/tests/test_history.py

Deliverables:
- Cleanup scheduler implementation
- Smoke tests passing
- API documentation

#### Frontend Tasks (Days 1-7, Parallel)

**Day 1: Project Setup**
Files to create:
- frontend/package.json
- frontend/vite.config.js
- frontend/tailwind.config.js
- frontend/index.html
- frontend/src/main.js
- frontend/src/App.vue

Deliverables:
- Vue 3 + Vite running on localhost:5173
- Tailwind CSS configured
- Basic layout structure

**Day 1-2: State Management & Services**
Files to create:
- frontend/src/stores/images.js
- frontend/src/stores/upload.js
- frontend/src/stores/settings.js
- frontend/src/stores/session.js
- frontend/src/services/api.js
- frontend/src/services/imageService.js
- frontend/src/services/uploadService.js
- frontend/src/services/sessionService.js

Deliverables:
- Pinia stores configured
- Axios API client setup
- Service layer for API calls

**Day 2-3: Common Components**
Files to create:
- frontend/src/components/common/Button.vue
- frontend/src/components/common/Modal.vue
- frontend/src/components/common/Toast.vue
- frontend/src/components/common/Spinner.vue
- frontend/src/components/common/ProgressBar.vue
- frontend/src/components/common/Dropdown.vue
- frontend/src/components/common/Tooltip.vue

Deliverables:
- Reusable UI components
- Component storybook/examples

**Day 3-4: Upload Components**
Files to create:
- frontend/src/components/upload/DropZone.vue
- frontend/src/components/upload/ChunkedUploader.vue
- frontend/src/components/upload/UploadProgress.vue
- frontend/src/composables/useImageUpload.js

Deliverables:
- Drag & drop zone working
- Chunked upload with progress
- Parallel upload support (max 3)
- Error handling and retry

**Day 4-5: Gallery Components**
Files to create:
- frontend/src/components/gallery/ImageGallery.vue
- frontend/src/components/gallery/ImageCard.vue
- frontend/src/components/gallery/ImageThumbnail.vue
- frontend/src/components/gallery/ThumbnailSizeToggle.vue
- frontend/src/components/gallery/ImageMetadata.vue

Deliverables:
- Grid layout gallery
- Image cards with actions
- Thumbnail size toggle (small/medium/large)
- Metadata display

**Day 5-6: Compression & Download Components**
Files to create:
- frontend/src/components/compression/CompressionControls.vue
- frontend/src/components/compression/PresetDropdown.vue
- frontend/src/components/gallery/BulkActions.vue
- frontend/src/components/download/DownloadButton.vue
- frontend/src/components/download/ClipboardButton.vue
- frontend/src/components/download/ZipDownloader.vue
- frontend/src/composables/useImageCompression.js
- frontend/src/composables/useDownload.js

Deliverables:
- Compression preset dropdown
- Bulk compress all button
- Individual download buttons
- Copy to clipboard
- ZIP download with selection

**Day 6-7: History & Undo Components**
Files to create:
- frontend/src/components/history/UndoButton.vue
- frontend/src/components/history/HistoryPanel.vue
- frontend/src/composables/useUndo.js

Deliverables:
- Undo button per image
- History visualization
- Undo functionality integrated

**Day 7: Layout & Polish**
Files to create:
- frontend/src/components/layout/AppHeader.vue
- frontend/src/components/layout/MainLayout.vue
- frontend/src/components/layout/AppFooter.vue

Deliverables:
- Header with gear icon for settings
- Main layout structure
- Responsive design (desktop-focused)
- Toast notifications working

#### Stage 1 Testing & Documentation (Days 8-10)

**Testing:**
- Upload flow end-to-end
- Compression with all presets
- Bulk operations
- Undo functionality
- Download and ZIP creation
- Session expiry behavior
- Cleanup task execution

**Documentation:**
- Update README.md with Stage 1 features
- API endpoint documentation
- Component documentation
- Known issues/limitations

#### Stage 1 Deliverables

**Working Features:**
✓ Multi-image upload with chunking and progress
✓ Parallel uploads (max 3 simultaneous)
✓ Image gallery with configurable thumbnail sizes
✓ Compression presets (Email/Web/Web HQ)
✓ Bulk compress all images
✓ Per-image undo (10 operations)
✓ Individual image download
✓ Copy image to clipboard
✓ ZIP download with image selection
✓ Session management with 7-day expiry
✓ Auto-cleanup of expired sessions
✓ Settings gear icon (placeholder for Stage 2+)

**Git Commit:**
```
Stage 1: Core upload, compression, and download functionality

- Implemented chunked file upload with progress tracking
- Added compression presets for email and web
- Bulk operations support (compress all, download ZIP)
- Per-image undo stack with 10 operation limit
- Session management with auto-cleanup
- Configurable thumbnail sizes in gallery
- Multiple download options (individual, clipboard, ZIP)
```

---

### STAGE 2: IMAGE EDITOR INTEGRATION

**Duration:** 4-6 days  
**Priority:** High  
**Dependencies:** Stage 1 complete

#### Goals
- Integrate TUI Image Editor
- Modal-based editing interface
- All editor features available (crop, rotate, filters, text, drawing)
- Editor operations in undo stack
- Save edited images

#### Backend Tasks (Days 1-2)

**Day 1: Editor Service**
Files to create:
- backend/app/services/editor_service.py
- backend/app/api/v1/endpoints/editor.py
- backend/app/schemas/editor.py

Key implementations:
- Process TUI editor operations from frontend
- Apply operations to images (crop, rotate, filters, etc.)
- Save edited image to history
- Return updated image metadata

Deliverables:
- Editor operations endpoint
- Support for all TUI editor operation types
- Integration with history service

**Day 2: Testing**
Files to create:
- backend/app/tests/test_editor.py

Deliverables:
- Editor endpoint tests
- Operation validation tests

#### Frontend Tasks (Days 1-4)

**Day 1: TUI Editor Setup**
Files to create:
- Install @toast-ui/vue-image-editor package
- frontend/src/components/editor/EditorModal.vue
- frontend/src/composables/useImageEditor.js

Deliverables:
- TUI Image Editor installed and configured
- Modal wrapper component created
- Editor initialization working

**Day 2-3: Editor Integration**
Files to create:
- frontend/src/components/editor/EditorToolbar.vue
- frontend/src/components/editor/EditorSaveButton.vue
- frontend/src/services/editorService.js

Key implementations:
- Full editor with all tools (crop, rotate, flip, filters, text, drawing, shapes)
- Custom toolbar if needed
- Save and cancel buttons
- Loading states during save

Deliverables:
- Modal opens when "Edit" button clicked on image card
- All TUI editor features accessible
- Apply button sends operations to backend
- Cancel button closes without saving
- Loading spinner during save

**Day 3-4: Integration & Polish**
Key implementations:
- Update ImageCard component to add "Edit" button
- Connect editor to undo stack
- Handle editor errors gracefully
- Responsive editor size

Deliverables:
- Seamless integration with existing gallery
- Edited images update in place
- Undo works for editor operations
- Error handling with toast notifications

#### Stage 2 Testing & Documentation (Days 5-6)

**Testing:**
- Editor opens and closes properly
- All editor tools work (crop, rotate, filters, etc.)
- Save applies changes to image
- Cancel discards changes
- Undo works for editor operations
- Editor operations appear in history

**Documentation:**
- Update README.md with editor features
- Editor usage guide in USER_GUIDE.md
- API documentation for editor endpoints

#### Stage 2 Deliverables

**Working Features:**
✓ TUI Image Editor integration
✓ Modal-based editing interface
✓ All editor features available:
  - Crop
  - Rotate & Flip
  - Filters (grayscale, sepia, blur, sharpen, etc.)
  - Text overlay
  - Drawing (free draw, line, arrow)
  - Shapes (rectangle, circle, triangle)
  - Icon stamps
✓ Editor operations saved to history
✓ Undo works for editor changes
✓ Save/Cancel controls

**Git Commit:**
```
Stage 2: TUI Image Editor integration with modal interface

- Integrated @toast-ui/vue-image-editor
- Modal-based editing with all features enabled
- Editor operations saved to version history
- Undo support for editor changes
- Custom save/cancel controls
```

---

### STAGE 3: AI BACKGROUND REMOVAL

**Duration:** 3-4 days (Revised from 3-5)  
**Priority:** Medium  
**Dependencies:** Stage 1 complete

#### Goals
- OAuth2 PKCE enrollment flow (for Stage 4 preparation)
- Background removal using rembg library (local processing)
- Model selection in settings
- Settings UI with Display and AI sections
- API key encryption and secure storage

#### Research Complete ✓
Research has been completed. Key findings:
- **Background removal:** Use rembg Python library (not OpenRouter)
- **Cost:** $0.00 per image (local processing with rembg)
- **Quality:** Excellent with u2net model
- **OAuth:** Still needed for Stage 4 AI chat feature
- See: AI_RESEARCH_FINDINGS.md for complete details

#### Backend Tasks (Days 1-2)

**Day 1: OAuth2 PKCE Implementation**
Files to create:
- backend/app/integrations/openrouter/__init__.py
- backend/app/integrations/openrouter/oauth.py
- backend/app/core/encryption.py
- backend/app/api/v1/endpoints/oauth.py

Key implementations:
```python
# oauth.py
class OAuth2PKCEHandler:
    def generate_code_verifier(self) -> str:
        """Generate random 128-character code verifier"""
        return base64.urlsafe_b64encode(secrets.token_bytes(96)).decode().rstrip('=')
    
    def create_code_challenge(self, verifier: str) -> str:
        """Create SHA-256 hash of verifier"""
        digest = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip('=')
    
    def build_authorization_url(self, callback_url: str, state: str, challenge: str) -> str:
        """Build OAuth authorization URL"""
        return f"https://openrouter.ai/auth?callback_url={callback_url}&code_challenge={challenge}&code_challenge_method=S256&state={state}"
    
    async def exchange_code_for_key(self, code: str, verifier: str) -> str:
        """Exchange authorization code for API key"""
        response = await httpx.post(
            "https://openrouter.ai/api/v1/auth/keys",
            json={
                "code": code,
                "code_verifier": verifier,
                "code_challenge_method": "S256"
            }
        )
        return response.json()["key"]

# encryption.py
from cryptography.fernet import Fernet

def encrypt_api_key(api_key: str, encryption_key: bytes) -> str:
    f = Fernet(encryption_key)
    return f.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted: str, encryption_key: bytes) -> str:
    f = Fernet(encryption_key)
    return f.decrypt(encrypted.encode()).decode()
```

Deliverables:
- OAuth2 PKCE flow implementation
- Authorization URL generation
- Code exchange endpoint
- API key encryption/decryption
- OAuth state management in database

**Day 1-2: rembg Background Removal Integration**
Files to create:
- backend/app/services/background_service.py
- backend/app/api/v1/endpoints/background.py

Key implementations:
```python
# background_service.py
from rembg import remove
from PIL import Image
import io

class BackgroundRemovalService:
    def __init__(self, model: str = "u2net"):
        self.model = model
        # Models: u2net, u2net_human_seg, isnet-general-use, isnet-anime
    
    async def remove_background(
        self, 
        image_path: str, 
        output_path: str
    ) -> Dict[str, Any]:
        """Remove background from image using rembg"""
        # Load image
        input_image = Image.open(image_path)
        
        # Remove background
        output_image = remove(
            input_image,
            session=self._get_session()
        )
        
        # Save as PNG with transparency
        output_image.save(output_path, 'PNG')
        
        return {
            "original_size": os.path.getsize(image_path),
            "output_size": os.path.getsize(output_path),
            "format": "PNG",
            "has_transparency": True
        }
    
    def _get_session(self):
        """Get or create rembg session with specified model"""
        from rembg import new_session
        return new_session(self.model)
```

Deliverables:
- rembg integration
- Background removal endpoint
- Support for multiple rembg models
- GPU acceleration (if available)
- Integration with history service
- PNG output with transparency

**Day 2: Settings Service**
Update files:
- backend/app/api/v1/endpoints/settings.py
- backend/app/services/settings_service.py

Key implementations:
- Settings CRUD operations
- OAuth initiation endpoint
- OAuth callback handler
- API key storage (encrypted)
- Model configuration endpoints

Deliverables:
- Complete settings API
- OAuth endpoints functional
- Secure API key storage

#### Frontend Tasks (Days 2-3)

**Day 2: Settings Modal Components**
Files to create:
- frontend/src/components/settings/SettingsModal.vue (~500 lines)
- frontend/src/components/settings/AISettings.vue (~400 lines)
- frontend/src/components/settings/DisplaySettings.vue (~250 lines)
- frontend/src/components/settings/OAuth2Enrollment.vue (~350 lines)
- frontend/src/components/settings/SettingsSaveIndicator.vue (~150 lines)
- frontend/src/services/settingsService.js
- frontend/src/composables/useSettings.js

Key implementations:
```javascript
// OAuth2Enrollment.vue
async function initiateOAuth() {
  // Generate PKCE pair
  const verifier = generateCodeVerifier();
  const challenge = await createCodeChallenge(verifier);
  
  // Store verifier in session storage
  sessionStorage.setItem('oauth_verifier', verifier);
  sessionStorage.setItem('oauth_state', state);
  
  // Open OAuth URL in modal/popup
  const authUrl = await settingsService.getOAuthUrl(challenge, state);
  window.location.href = authUrl;
}

async function handleOAuthCallback(code, state) {
  // Retrieve verifier from session storage
  const verifier = sessionStorage.getItem('oauth_verifier');
  const storedState = sessionStorage.getItem('oauth_state');
  
  // Validate state
  if (state !== storedState) throw new Error('Invalid state');
  
  // Exchange code for API key
  await settingsService.exchangeOAuthCode(code, verifier);
  
  // Clear session storage
  sessionStorage.removeItem('oauth_verifier');
  sessionStorage.removeItem('oauth_state');
  
  // Update UI
  aiConnected.value = true;
}
```

**Settings Modal Features:**
- Two tabs: Display Settings & AI Settings
- Display Settings:
  - Thumbnail size selector (Small/Medium/Large)
  - Default download format (Original/JPEG/PNG/WebP)
- AI Settings:
  - OAuth2 enrollment button
  - Connected status indicator (no key displayed)
  - Background removal method selector (rembg/Remove.bg future)
  - rembg model selector (u2net, u2net_human_seg, isnet-general-use)
  - GPU acceleration toggle (if available)
- Save button with countdown spinner (5 seconds)
- Manual close button
- Visual confirmation in modal

Deliverables:
- Complete settings modal
- OAuth flow in UI
- Settings persistence
- Visual feedback on save

**Day 3: Background Removal UI**
Files to create:
- frontend/src/components/ai/BackgroundRemoval.vue (~250 lines)
- frontend/src/services/backgroundService.js
- frontend/src/composables/useBackgroundRemoval.js

Key implementations:
- "Remove Background" button on ImageCard
- Processing spinner during removal
- Success toast notification
- Error modal with details
- Preview before/after (optional)
- Undo button appears after removal

**UI Behavior:**
- Button always visible (rembg doesn't need OAuth)
- Processing spinner shows during removal
- Toast: "Background removed successfully"
- Image updates in place
- Adds to undo history

Deliverables:
- Background removal button on image cards
- Processing indicators
- Success/error feedback
- Integration with undo stack

#### Stage 3 Testing & Documentation (Day 4)

**Testing:**
- OAuth2 PKCE flow end-to-end
- Code verifier generation and validation
- API key encryption/decryption
- rembg background removal on various images
- Different rembg models (u2net, u2net_human_seg, isnet-general-use)
- GPU acceleration (if available)
- Settings persistence
- Background removal with undo
- Error handling for various scenarios

**Documentation:**
- Update README.md with Stage 3 features
- OAuth2 PKCE setup in INSTALLATION.md
- rembg installation guide (CPU vs GPU)
- Background removal usage in USER_GUIDE.md
- Settings configuration in USER_GUIDE.md

#### Stage 3 Deliverables

**Working Features:**
✓ Settings modal with gear icon in header
✓ Display settings (thumbnail size, download format)
✓ AI settings section with OAuth2 enrollment
✓ OAuth2 PKCE flow for OpenRouter.ai
✓ Secure API key storage (encrypted in database)
✓ Background removal using rembg (FREE, local processing)
✓ Multiple rembg models supported (u2net, u2net_human_seg, isnet-general-use)
✓ GPU acceleration option
✓ Background removal replaces image with PNG (transparency)
✓ Undo functionality for background removal
✓ Processing indicators
✓ Toast notifications for success/error
✓ No API costs for background removal

**Cost Analysis:**
- Background removal: $0.00 per image (local rembg processing)
- OAuth setup: One-time, free (prepares for Stage 4)
- No monthly costs for Stage 3 features

**Git Commit:**
```
Stage 3: Background removal with rembg and OAuth2 PKCE preparation

- Implemented OAuth2 PKCE flow for OpenRouter.ai enrollment
- Integrated rembg library for FREE local background removal
- Added settings modal with Display and AI configuration
- Support for multiple rembg models (u2net, u2net_human_seg, etc.)
- GPU acceleration support for faster processing
- Secure API key encryption and storage
- Background removal outputs PNG with transparency
- Full undo support for background removal operations
- Settings persistence with visual confirmation
```
- Model selection working
- Background removal successful
- Undo works for background removal
- Error handling for API failures
- Rate limiting respected
- Feature disabled gracefully without config

**Documentation:**
- Update README.md with AI features
- AI setup guide in INSTALLATION.md
- OpenRouter.ai configuration in DEVELOPER_GUIDE.md
- Background removal usage in USER_GUIDE.md

#### Stage 3 Deliverables

**Working Features:**
✓ Settings modal with gear icon in header
✓ Display settings (thumbnail size, download format)
✓ AI settings section
✓ OAuth2 PKCE enrollment for OpenRouter.ai
✓ Secure API key storage (encrypted)
✓ Model discovery and selection
✓ Model selector with typeahead filter
✓ Model info display (name, description, tags, cost)
✓ AI background removal functionality
✓ Background removal replaces image (undo available)
✓ Processing indicators
✓ Cost estimation display
✓ Graceful degradation when AI disabled
✓ Feature detection and tooltips

**Git Commit:**
```
Stage 3: AI-powered background removal with OpenRouter.ai

- Implemented OAuth2 PKCE enrollment flow
- Added settings modal with display and AI configuration
- Integrated OpenRouter.ai API client
- Background removal with model selection
- Secure API key storage with encryption
- Model discovery with typeahead filtering
- Cost estimation and tracking
- Graceful degradation when AI not configured
```

---

### STAGE 4: AI IMAGE MANIPULATION CHAT

**Duration:** 5-6 days (Revised from 5-7)  
**Priority:** Medium  
**Dependencies:** Stage 3 complete (OAuth2 PKCE functional)

#### Goals
- AI chatbot interface using OpenRouter.ai
- Natural language image manipulation requests
- Multi-turn conversations with context
- Inline image display in chat
- Model selection with cost tracking
- Hybrid approach: AI instructions + local Pillow processing
- Conversation history persistence

#### Research Complete ✓
Research findings:
- **Recommended Model:** Google Gemini 3 Flash Preview (`google/gemini-3-flash-preview`)
- **Cost:** ~$0.004 per conversation turn (~$0.20-2.00/month personal use)
- **Approach:** Hybrid - AI analyzes and provides instructions, backend applies with Pillow
- **Alternative Models:** Claude Opus 4.6 (premium), Gemini 2.5 Flash (budget)
- See: AI_RESEARCH_FINDINGS.md for complete details

#### Backend Tasks (Days 1-3)

**Day 1: OpenRouter Client & Model Discovery**
Files to create:
- backend/app/integrations/openrouter/client.py
- backend/app/integrations/openrouter/models.py
- backend/app/api/v1/endpoints/ai_models.py
- Update backend/app/schemas/ai.py

Key implementations:
```python
# client.py - OpenRouter API client using OpenAI SDK
from openai import AsyncOpenAI

class OpenRouterClient:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://imagetools.local",
                "X-Title": "Image Tools"
            }
        )
    
    async def chat_completion(
        self, model: str, messages: List[dict], 
        max_tokens: int = 1000
    ) -> dict:
        """Send chat completion with vision support"""
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens
        )
        return response
    
    async def get_available_models(self) -> List[dict]:
        """Fetch models from OpenRouter API"""
        # GET https://openrouter.ai/api/v1/models
        pass

# models.py - Model discovery and filtering
class ModelService:
    async def search_models(
        self, query: str, 
        vision_only: bool = True
    ) -> List[ModelInfo]:
        """Search models with typeahead filtering"""
        pass
    
    def calculate_cost(
        self, model: str, 
        input_tokens: int, 
        output_tokens: int
    ) -> float:
        """Calculate message cost from token counts"""
        pass
```

Key features:
- OpenAI SDK compatibility with OpenRouter
- Model discovery API integration
- Typeahead search for 300+ models
- Vision-capable model filtering
- Cost calculation from pricing data
- Default model: `google/gemini-3-flash-preview`

Deliverables:
- Working OpenRouter client with Gemini 3 Flash
- Model discovery endpoint: GET /api/v1/ai/models
- Model search endpoint: GET /api/v1/ai/models/search?q=gemini
- Cost calculator utility
- Model info caching (5min TTL)

**Day 2: AI Chat Service & Cost Tracking**
Files to create:
- backend/app/services/ai_chat_service.py
- backend/app/api/v1/endpoints/ai_chat.py
- backend/app/services/cost_tracker.py
- Update backend/app/models/conversation.py (new table)

Key implementations:
```python
# ai_chat_service.py
class AIChatService:
    async def send_message(
        session_id: str,
        image_id: str,
        message: str,
        conversation_id: Optional[str] = None,
        model: str = "google/gemini-3-flash-preview"
    ) -> ChatResponse:
        """Send message with image context"""
        # 1. Get user's OpenRouter API key
        # 2. Load conversation history
        # 3. Encode image as base64
        # 4. Build messages with vision
        # 5. Call OpenRouter API
        # 6. Extract usage & calculate cost
        # 7. Store message + response + cost
        # 8. Return response
        pass
    
    async def get_conversation_history(
        conversation_id: str
    ) -> List[Message]:
        """Get all messages in conversation"""
        pass
    
    async def delete_conversation(conversation_id: str):
        """Delete conversation and messages"""
        pass

# cost_tracker.py
class CostTracker:
    async def record_message_cost(
        session_id: str,
        conversation_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float
    ):
        """Record per-message cost"""
        pass
    
    async def get_monthly_cost(session_id: str) -> float:
        """Get current month's total cost"""
        pass
    
    async def check_cost_limit(
        session_id: str, 
        estimated_cost: float
    ) -> bool:
        """Check if request would exceed monthly limit"""
        pass
```

Database schema additions:
```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    image_id TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_cost REAL DEFAULT 0.0,
    FOREIGN KEY (image_id) REFERENCES images(id)
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL, -- 'user' or 'assistant'
    content TEXT NOT NULL,
    tokens_input INTEGER,
    tokens_output INTEGER,
    cost REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE INDEX idx_conversations_session ON conversations(session_id);
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
```

Key features:
- Multi-turn conversation support
- Image context in every message (base64 encoded)
- Per-message cost tracking from OpenRouter usage data
- Monthly cost aggregation
- Cost limit enforcement (check before API call)
- Conversation history persistence

Deliverables:
- Chat endpoint: POST /api/v1/ai/chat
- History endpoint: GET /api/v1/ai/conversations/{id}
- Delete endpoint: DELETE /api/v1/ai/conversations/{id}
- Cost endpoint: GET /api/v1/ai/cost/monthly
- Working conversation with Gemini 3 Flash
- Cost tracking in database

**Day 3: Image Manipulation Pipeline (Hybrid Approach)**
Files to create:
- backend/app/services/image_manipulator.py
- Update backend/app/services/ai_chat_service.py

Key implementations:
```python
# image_manipulator.py - Pillow-based transformations
class ImageManipulator:
    def apply_operation(
        self, image_path: str, 
        operation: dict
    ) -> str:
        """Apply single operation and return new image path"""
        op_type = operation['type']
        
        if op_type == 'brightness':
            self._adjust_brightness(image_path, operation['value'])
        elif op_type == 'contrast':
            self._adjust_contrast(image_path, operation['value'])
        elif op_type == 'saturation':
            self._adjust_saturation(image_path, operation['value'])
        elif op_type == 'rotate':
            self._rotate(image_path, operation['degrees'])
        elif op_type == 'crop':
            self._crop(image_path, operation['box'])
        elif op_type == 'resize':
            self._resize(image_path, operation['size'])
        elif op_type == 'filter':
            self._apply_filter(image_path, operation['filter'])
        # Add more operations as needed
        
        return new_image_path
    
    def parse_ai_instructions(self, ai_response: str) -> List[dict]:
        """Parse AI response into structured operations"""
        # AI returns JSON or structured instructions
        # Example: [{"type": "brightness", "value": 1.2}, 
        #           {"type": "saturation", "value": 0.8}]
        pass

# Integration in ai_chat_service.py
async def send_message(...) -> ChatResponse:
    # ... existing code ...
    
    # After getting AI response:
    if self._wants_to_modify_image(ai_text):
        operations = self.manipulator.parse_ai_instructions(ai_text)
        
        for op in operations:
            new_image_path = self.manipulator.apply_operation(
                current_image_path, op
            )
            # Add to history via history service
            await self.history_service.add_operation(
                image_id=image_id,
                operation_type=op['type'],
                input_path=current_image_path,
                output_path=new_image_path,
                parameters=op
            )
            current_image_path = new_image_path
        
        # Return AI explanation + modified image
        return ChatResponse(
            text=ai_text,
            image_modified=True,
            new_image_url=f"/images/{image_id}/current"
        )
```

System prompt for Gemini 3 Flash:
```python
SYSTEM_PROMPT = """You are an image manipulation assistant. When the user asks to modify the image, respond with:
1. A friendly explanation of what you'll do
2. A JSON block with operations to apply

Available operations:
- brightness: {"type": "brightness", "value": 0.5-2.0}
- contrast: {"type": "contrast", "value": 0.5-2.0}
- saturation: {"type": "saturation", "value": 0.0-2.0}
- rotate: {"type": "rotate", "degrees": -360 to 360}
- crop: {"type": "crop", "box": [x1, y1, x2, y2]}
- resize: {"type": "resize", "size": [width, height]}
- filter: {"type": "filter", "filter": "blur|sharpen|sepia|grayscale"}

Format: Explain in text, then add:
```json
{"operations": [...]}
```

Example:
"I'll make the image brighter and more vibrant!
```json
{"operations": [
  {"type": "brightness", "value": 1.3},
  {"type": "saturation", "value": 1.4}
]}
```
"""
```

Key features:
- Hybrid approach: AI analyzes → Pillow applies transformations
- Structured operation parsing from AI responses
- Integration with existing history service (undo support)
- Support for common operations (no DALL-E needed)
- Graceful handling of unsupported requests

Deliverables:
- Working image manipulation via AI chat
- Support for: brightness, contrast, saturation, rotation, crop, resize, filters
- Integration with undo/redo system
- Error handling for unsupported operations
- User-friendly AI explanations

#### Frontend Tasks (Days 2-5)

**Day 2-3: Chat Interface Components**
Files to create:
- frontend/src/components/ai/AIChatModal.vue (modal container with image + chat)
- frontend/src/components/ai/ChatMessage.vue (message bubble component)
- frontend/src/components/ai/ChatInput.vue (input field + send button)
- frontend/src/components/ai/ModelSelector.vue (typeahead model search)
- frontend/src/components/ai/CostDisplay.vue (cost indicator component)
- frontend/src/components/ai/AIProcessing.vue (loading state)

Key implementations:
```vue
<!-- AIChatModal.vue -->
<template>
  <div class="ai-chat-modal">
    <div class="modal-header">
      <h3>AI Image Assistant</h3>
      <ModelSelector v-model="selectedModel" />
      <CostDisplay :conversation-cost="conversationCost" 
                   :monthly-cost="monthlyCost" />
      <button @click="closeModal">✕</button>
    </div>
    
    <div class="image-preview">
      <img :src="currentImageUrl" alt="Current image" />
    </div>
    
    <div class="chat-messages" ref="messagesContainer">
      <ChatMessage v-for="msg in messages" 
                   :key="msg.id" 
                   :message="msg" />
      <AIProcessing v-if="isProcessing" />
    </div>
    
    <ChatInput @send="sendMessage" 
               :disabled="isProcessing || !hasApiKey" />
  </div>
</template>

<!-- ModelSelector.vue - Typeahead search -->
<template>
  <div class="model-selector">
    <input type="text" 
           v-model="searchQuery"
           @input="searchModels"
           placeholder="Search models..." />
    <div class="model-dropdown" v-if="showResults">
      <div v-for="model in filteredModels" 
           :key="model.id"
           @click="selectModel(model)"
           class="model-option">
        <span class="model-name">{{ model.name }}</span>
        <span class="model-cost">
          ${{ model.pricing.prompt }} / ${{ model.pricing.completion }}
        </span>
      </div>
    </div>
    <div class="selected-model">
      {{ currentModel.name }} 
      <span class="cost-estimate">~$0.004/turn</span>
    </div>
  </div>
</template>

<!-- CostDisplay.vue -->
<template>
  <div class="cost-display">
    <div class="conversation-cost">
      This chat: ${{ conversationCost.toFixed(4) }}
    </div>
    <div class="monthly-cost" :class="costLevelClass">
      This month: ${{ monthlyCost.toFixed(2) }}
      <span v-if="monthlyLimit"> / ${{ monthlyLimit }}</span>
    </div>
  </div>
</template>
```

Key features:
- Modal layout with image preview + chat area
- Message bubbles with role styling (user vs assistant)
- Typeahead model search (searches 300+ models)
- Real-time cost display (per-conversation and monthly)
- Model cost info in dropdown ($input/$output per 1M tokens)
- Processing indicator during AI response
- Auto-scroll to latest message

Deliverables:
- Chat modal opens from "AI Manipulate" button
- Image displayed at top of chat
- Model selector with typeahead search
- Cost display updated after each message
- Message history displayed in chronological order
- Input field with send button (disabled during processing)
- Responsive layout (desktop-focused)

**Day 3-4: Chat Functionality & API Integration**
Files to create/update:
- frontend/src/services/aiService.js (API calls)
- frontend/src/composables/useAIChat.js (chat state management)
- frontend/src/composables/useModelSearch.js (model discovery)

Key implementations:
```javascript
// aiService.js
export const aiService = {
  async sendMessage(imageId, message, conversationId, model) {
    const response = await api.post('/api/v1/ai/chat', {
      image_id: imageId,
      message,
      conversation_id: conversationId,
      model
    });
    return response.data; // { text, image_modified, cost, tokens, ... }
  },
  
  async searchModels(query) {
    const response = await api.get('/api/v1/ai/models/search', {
      params: { q: query, vision_only: true }
    });
    return response.data.models;
  },
  
  async getMonthlyCost() {
    const response = await api.get('/api/v1/ai/cost/monthly');
    return response.data.cost;
  },
  
  async getConversationHistory(conversationId) {
    const response = await api.get(`/api/v1/ai/conversations/${conversationId}`);
    return response.data.messages;
  },
  
  async deleteConversation(conversationId) {
    await api.delete(`/api/v1/ai/conversations/${conversationId}`);
  }
};

// useAIChat.js composable
export function useAIChat(imageId) {
  const messages = ref([]);
  const conversationId = ref(null);
  const isProcessing = ref(false);
  const conversationCost = ref(0);
  const monthlyCost = ref(0);
  const selectedModel = ref('google/gemini-3-flash-preview');
  
  const sendMessage = async (text) => {
    isProcessing.value = true;
    
    // Add user message to UI immediately
    messages.value.push({
      id: generateId(),
      role: 'user',
      content: text,
      timestamp: new Date()
    });
    
    try {
      const response = await aiService.sendMessage(
        imageId,
        text,
        conversationId.value,
        selectedModel.value
      );
      
      // Add assistant response
      messages.value.push({
        id: response.message_id,
        role: 'assistant',
        content: response.text,
        cost: response.cost,
        timestamp: new Date()
      });
      
      // Update conversation ID if new
      if (!conversationId.value) {
        conversationId.value = response.conversation_id;
      }
      
      // Update costs
      conversationCost.value += response.cost;
      monthlyCost.value = await aiService.getMonthlyCost();
      
      // If image was modified, emit event to refresh image
      if (response.image_modified) {
        emit('image-updated', response.new_image_url);
      }
      
    } catch (error) {
      // Show error message in chat
      messages.value.push({
        id: generateId(),
        role: 'error',
        content: `Error: ${error.message}`,
        timestamp: new Date()
      });
    } finally {
      isProcessing.value = false;
    }
  };
  
  return {
    messages,
    conversationCost,
    monthlyCost,
    selectedModel,
    isProcessing,
    sendMessage,
    clearConversation
  };
}
```

Key features:
- API service methods for all AI endpoints
- Composable for chat state management
- Real-time cost updates after each message
- Image refresh when AI modifies image
- Error handling with user-friendly messages
- Optimistic UI updates (show user message immediately)
- Conversation persistence across modal opens

Deliverables:
- Full chat functionality working end-to-end
- Image updates reflected when AI modifies image
- Conversation history loads on modal reopen
- Cost tracking accurate (per-message and monthly)
- Model selection persists in session settings
- Clear conversation button functional
- Error states handled gracefully

**Day 4-5: Integration & Polish**
Update files:
- frontend/src/components/ImageCard.vue (add AI Manipulate button)
- frontend/src/stores/imageStore.js (integrate with undo)
- frontend/src/components/ai/AIChatModal.vue (final polish)

Key implementations:
```vue
<!-- ImageCard.vue - Add AI Manipulate button -->
<template>
  <div class="image-card">
    <!-- existing buttons -->
    <button @click="openAIChat" 
            :disabled="!hasOpenRouterKey"
            :title="aiButtonTooltip"
            class="btn-ai-manipulate">
      💬 AI Manipulate
    </button>
  </div>
</template>

<script setup>
const hasOpenRouterKey = computed(() => {
  return settingsStore.openrouterApiKey !== null;
});

const aiButtonTooltip = computed(() => {
  return hasOpenRouterKey.value 
    ? 'Chat with AI to manipulate this image'
    : 'Configure OpenRouter API key in Settings to use AI features';
});
</script>
```

Key features:
- "AI Manipulate" button on each image card
- Button disabled with tooltip if OpenRouter API key not configured
- AI operations integrated with undo/redo stack
- Undo button works for AI manipulations
- Model settings saved to session settings
- Conversation history accessible from image context menu
- Polish: animations, transitions, focus management

Deliverables:
- Seamless integration with image gallery
- AI manipulations appear in undo stack
- Undo/redo works correctly with AI operations
- Model selection persists across sessions
- Chat modal responsive and polished
- Feature detection (grayed out if API key missing)
- Keyboard shortcuts (Esc to close, Enter to send)
- Accessibility improvements (ARIA labels, focus trap)

#### Stage 4 Testing & Documentation (Days 6-7)

**Testing:**
- Chat modal opens and closes
- Messages send and receive correctly
- Image manipulations apply successfully
- Multi-turn conversations work
- Conversation history persists
- Undo works for AI manipulations
- Error handling for failed requests
- Cost tracking accurate
- Model selection works

**Documentation:**
- Update README.md with AI chat features
- AI chat usage in USER_GUIDE.md
- API documentation for chat endpoints
- Example prompts and use cases

#### Stage 4 Deliverables

**Working Features:**
✓ OpenRouter API integration with Gemini 3 Flash Preview
✓ AI chatbot modal interface with image context
✓ Natural language image manipulation (hybrid approach)
✓ Multi-turn conversation support with vision
✓ Image displayed inline in chat at top of modal
✓ Conversation history persistence per image
✓ Chat message storage in database
✓ Model discovery and search (typeahead for 300+ models)
✓ Model selector dropdown with cost information
✓ Real-time cost tracking (per-message and monthly totals)
✓ Cost display in chat header
✓ Cost limit enforcement (check before API call)
✓ Undo/redo for AI manipulations
✓ Integration with existing history service
✓ Clear conversation button
✓ Processing indicators with loading states
✓ Error handling with user-friendly messages
✓ Feature detection (button disabled if API key not configured)
✓ Supported operations: brightness, contrast, saturation, rotate, crop, resize, filters
✓ Pillow-based image transformations (local, no generation costs)

**Cost Estimates (Gemini 3 Flash Preview):**
- Per conversation turn: ~$0.004 (typical usage with one image)
- Personal monthly use: $0.20 - $2.00 (50-500 turns)
- Image manipulations: $0.00 (local Pillow processing, no API calls)
- Background removal: $0.00 (local rembg, no API calls)

**Git Commit:**
```
Stage 4: AI-powered image manipulation with Gemini 3 Flash

- Integrated OpenRouter API with OpenAI SDK compatibility
- Implemented Gemini 3 Flash Preview as default model (~$0.004/turn)
- AI chatbot modal for natural language image manipulation
- Hybrid approach: AI analyzes images + Pillow applies transformations
- Multi-turn conversations with vision support (image context)
- Model discovery and typeahead search (300+ models)
- Real-time cost tracking: per-message and monthly totals
- Cost limit enforcement with configurable monthly caps
- Conversation history persistence in database
- Integration with undo/redo system (10-operation limit)
- Support for brightness, contrast, saturation, rotation, crop, resize, filters
- Feature detection: button disabled if API key not configured
- Error handling with graceful fallbacks
- Local image processing with Pillow (no generation API costs)
```

---

## 9. TIMELINE AND MILESTONES

### Overall Timeline: 23-32 days

#### Week 1-2: Stage 1 (Core MVP)
- Days 1-7: Backend implementation
- Days 1-7: Frontend implementation (parallel)
- Days 8-10: Testing and documentation
- Milestone: Working upload, compress, download workflow

#### Week 3: Stage 2 (Image Editor)
- Days 11-14: TUI Editor integration
- Days 15-16: Testing and documentation
- Milestone: Full image editing capabilities

#### Week 3-4: Stage 3 (AI Background Removal)
- Days 17-19: rembg library integration and background removal
- Days 20: Testing and documentation
- Milestone: AI-powered background removal with rembg

#### Week 4-5: Stage 4 (AI Chat)
- Days 21-25: AI chat implementation with OpenRouter
- Days 26: Testing and documentation
- Milestone: AI chatbot for image manipulation with Gemini 3 Flash

#### Week 5: Final Documentation & Polish
- Days 27-29: Complete all documentation
- Days 30-32: Docker setup and deployment testing
- Final Milestone: Production-ready application

### Key Milestones

**Milestone 1 (End of Stage 1):**
- User can upload, compress, and download images
- Session management working
- Undo functionality operational
- Basic documentation complete

**Milestone 2 (End of Stage 2):**
- Image editor fully integrated
- All editing features available
- Editor operations in history

**Milestone 3 (End of Stage 3):**
- Settings modal complete
- OAuth2 PKCE enrollment working (OpenRouter)
- Background removal functional with rembg library
- Multiple rembg models available (u2net, u2net_human_seg, isnet)
- AI features configurable (API keys encrypted)

**Milestone 4 (End of Stage 4):**
- AI chat interface complete with OpenRouter integration
- Gemini 3 Flash Preview working as default model
- Model discovery and typeahead search functional
- Cost tracking operational (per-message and monthly)
- Hybrid image manipulation pipeline working
- All features integrated
- Full documentation delivered
- Docker deployment ready

---

## 10. DELIVERABLES

### Code Deliverables

#### Stage 1 Deliverables
1. Backend API with all Stage 1 endpoints
2. Frontend UI with upload, gallery, compression, download
3. SQLite database with schema
4. Session management system
5. Chunked upload implementation
6. Compression engine with presets
7. Undo/history system
8. Download and ZIP functionality
9. Smoke tests for critical paths

#### Stage 2 Deliverables
1. TUI Image Editor integration
2. Editor modal component
3. Editor API endpoints
4. Editor operations in history

#### Stage 3 Deliverables
1. Settings modal (display settings + AI settings tabs)
2. OAuth2 PKCE implementation for OpenRouter
3. rembg library integration (u2net, u2net_human_seg, isnet models)
4. Background removal service (local processing, no API costs)
5. Model selector for rembg (dropdown in settings)
6. Secure API key storage (Fernet encryption)
7. Feature detection and UI state management

#### Stage 4 Deliverables
1. OpenRouter API client integration (OpenAI SDK compatible)
2. Model discovery API and typeahead search
3. AI chat modal interface with image context
4. Conversation management (persistence, history)
5. Cost tracking service (per-message and monthly)
6. Hybrid image manipulation pipeline (AI + Pillow)
7. Chat API endpoints (send, history, delete)
8. Model selector with cost display
9. Integration with undo/redo system

### Documentation Deliverables

#### 1. README.md
Contents:
- Project overview
- Feature list
- Quick start guide
- Technology stack
- License information
- Contributing guidelines
- Support information

#### 2. INSTALLATION.md
Contents:
- Prerequisites
- Local development setup
- Docker installation
- Environment configuration
- Database setup
- Reverse proxy configuration (Traefik examples)
- SSL/TLS setup
- Troubleshooting common issues

#### 3. ARCHITECTURE.md
Contents:
- System architecture diagrams
- Component relationships
- Data flow diagrams
- Database schema
- API architecture
- Security considerations
- Scalability notes
- Technology choices rationale

#### 4. DEVELOPER_GUIDE.md
Contents:
- Development environment setup
- Project structure explanation
- Code style guidelines
- Component development guide
- API development guide
- Adding new features
- Testing procedures
- Debugging tips
- Git workflow
- Contributing guidelines

#### 5. USER_GUIDE.md
Contents:
- Getting started
- Uploading images
- Using compression presets
- Bulk operations
- Image editing guide
- AI features setup (OAuth enrollment)
- Background removal usage
- AI chat manipulation usage
- Settings configuration
- Download options
- Tips and best practices
- FAQ
- Troubleshooting

### Docker Deliverables

1. Dockerfile (multi-stage build)
2. docker-compose.yml (production)
3. docker-compose.dev.yml (development)
4. nginx.conf
5. start.sh (container startup script)
6. .dockerignore

### Configuration Deliverables

1. .env.example (comprehensive template)
2. .env.development (development defaults)
3. .env.production.example (production template)
4. .gitignore (comprehensive)
5. requirements.txt (Python dependencies)
6. requirements-dev.txt (Python dev dependencies)
7. package.json (Node.js dependencies)

### Testing Deliverables

1. Backend smoke tests (pytest)
   - test_upload.py
   - test_compression.py
   - test_session.py
   - test_history.py
   - test_settings.py
   - test_editor.py
   - test_api_endpoints.py

2. Frontend smoke tests (vitest)
   - Upload component tests
   - Compression tests
   - Gallery tests
   - Modal tests

### Git Deliverables

1. Initial commit: Project structure
2. Stage 1 commit: Core MVP
3. Stage 2 commit: Image editor
4. Stage 3 commit: AI background removal
5. Stage 4 commit: AI chat
6. Documentation commits (ongoing)
7. Git tags: v1.0.0-stage1, v1.0.0-stage2, v1.0.0-stage3, v1.0.0

---

## APPENDICES

### A. File Structure Quick Reference

```
ImageTools/
├── frontend/          # Vue.js app
├── backend/           # Python FastAPI app
├── docs/              # Additional documentation
├── .env.example       # Environment template
├── .gitignore         # Git ignore
├── docker-compose.yml # Docker orchestration
├── Dockerfile         # Container build
├── nginx.conf         # Nginx config
└── README.md          # Main readme
```

### B. Technology Versions

- Python: 3.11+
- Node.js: 20 LTS
- Vue.js: 3.x
- FastAPI: 0.110+
- SQLite: 3.x
- Docker: 20.10+
- Nginx: 1.24+

### C. Key Design Decisions

1. **Single Container:** Simplifies deployment and reverse proxy config
2. **SQLite:** Sufficient for single/small multi-user use, no external DB needed
3. **Session-based Storage:** Privacy-focused, no permanent storage
4. **Chunked Uploads:** Supports large files without timeout issues
5. **Per-image Undo:** User-friendly, limited to 10 operations for storage
6. **Modular Components:** Maintainable, max 400-600 lines per file
7. **OAuth2 PKCE:** Secure API key enrollment without backend secrets
8. **Single Port:** Simplified reverse proxy and firewall configuration

### D. Future Enhancements (Post-Stage 4)

1. Mobile responsive design
2. Image format conversion
3. Batch rename functionality
4. Image rotation/flip quick actions
5. Watermarking
6. Image comparison slider
7. Keyboard shortcuts
8. Drag-to-reorder images
9. Full unit test coverage
10. Performance monitoring
11. Multi-language support
12. Theme customization
13. Plugin system for custom operations
14. Webhook notifications
15. S3/cloud storage integration

---

## CONCLUSION

This implementation strategy provides a comprehensive roadmap for building the Image Tools application across four distinct stages. Each stage builds upon the previous one, with clear deliverables, timelines, and testing requirements.

The modular architecture ensures maintainability, while the staged approach allows for iterative development and testing. The focus on privacy, performance, and user experience aligns with the project's core goals.

Upon completion of all four stages, the Image Tools application will provide a powerful, self-hosted solution for image manipulation with modern AI capabilities, all while maintaining user privacy and simplicity of use.

---

---

## APPENDIX A: AI INTEGRATION RESEARCH FINDINGS

### Research Completed: February 6, 2026

This appendix contains detailed research findings on OpenRouter.ai API capabilities, OAuth2 PKCE implementation, and recommended AI models for Stages 3 and 4.

For complete research details, see: AI_RESEARCH_FINDINGS.md

---

### A.1 OpenRouter.ai Overview

**API Base URL:** https://openrouter.ai/api/v1

**Key Features:**
- Unified API for 300+ AI models
- Automatic model fallback and routing
- Vision models (text + image input)
- Image generation models (select models)
- Multimodal inputs: text, images, PDFs, audio, video
- Streaming responses
- Prompt caching
- Zero data retention option

**Authentication:**
1. Direct API Key (Bearer token)
2. OAuth2 PKCE (user-controlled keys)

---

### A.2 OAuth2 PKCE Implementation Details

**Three-Step Flow:**

**Step 1: Redirect to OpenRouter**
```
https://openrouter.ai/auth
  ?callback_url=https://yourdomain.com/app/oauth/callback
  &code_challenge=BASE64URL(SHA256(code_verifier))
  &code_challenge_method=S256
```

**Step 2: User Authorizes**
- User logs into OpenRouter
- Grants permission
- Redirected with code parameter

**Step 3: Exchange Code for Key**
```
POST https://openrouter.ai/api/v1/auth/keys
{
  "code": "auth_code_from_redirect",
  "code_verifier": "original_verifier",
  "code_challenge_method": "S256"
}

Response: { "key": "sk-or-v1-..." }
```

**Frontend Implementation:**
```javascript
// Generate PKCE pair
async function generatePKCE() {
  const verifier = base64url(crypto.getRandomValues(new Uint8Array(96)));
  const challenge = base64url(await sha256(verifier));
  return { verifier, challenge };
}

// Store verifier in sessionStorage
const { verifier, challenge } = await generatePKCE();
sessionStorage.setItem('oauth_verifier', verifier);

// Redirect user
window.location.href = `https://openrouter.ai/auth?callback_url=${callbackUrl}&code_challenge=${challenge}&code_challenge_method=S256`;
```

**Backend Implementation:**
```python
import hashlib
import base64
import secrets

def generate_code_verifier():
    return base64.urlsafe_b64encode(secrets.token_bytes(96)).decode().rstrip('=')

def create_code_challenge(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip('=')
```

**Security Considerations:**
- Store code_verifier in session storage (not cookies)
- Validate callback URLs
- Use HTTPS only
- Implement CSRF protection
- Encrypt API keys in database

---

### A.3 Stage 3: Background Removal Technology Decision

**Research Conclusion:**
OpenRouter does not have dedicated background removal models. After evaluating options:

**Recommended Solution: rembg Python Library**

**Why rembg:**
- Open source (MIT license)
- No API costs
- Fast processing (1-3 seconds)
- High quality results (u2net model)
- Self-contained, no external dependencies
- No rate limits

**Installation:**
```bash
pip install rembg[gpu]  # GPU acceleration
pip install rembg       # CPU only
```

**Usage:**
```python
from rembg import remove
from PIL import Image

def remove_background(input_path, output_path):
    input_image = Image.open(input_path)
    output_image = remove(input_image)
    output_image.save(output_path, 'PNG')
```

**Available Models:**
- u2net (default) - Best general purpose
- u2net_human_seg - Optimized for people
- isnet-general-use - Fast and accurate
- isnet-anime - For anime/cartoon images
- silueta - Alternative segmentation

**Cost Comparison:**
- rembg: $0.00 per image (local processing)
- Remove.bg API: ~$0.20 per image
- OpenRouter (would need workaround): ~$0.01-0.05 per image

**Implementation Strategy:**
1. Stage 3: Implement rembg as primary solution
2. No OAuth needed for background removal
3. Optional: Add Remove.bg as premium alternative in settings
4. Settings toggle: "Use cloud-based removal (higher quality)"

**Stage 3 Modified Approach:**
- OAuth2 PKCE still needed for Stage 4 (AI chat)
- Implement OAuth in Stage 3 for future use
- Background removal doesn't require OpenRouter
- Can still show as "AI" feature (technically it is ML)

---

### A.4 Stage 4: AI Chat - Recommended Models

After analyzing 300+ models on OpenRouter, these are the top recommendations:

#### Primary Recommendation: Google Gemini 3 Flash Preview

**Model ID:** `google/gemini-3-flash-preview`

**Capabilities:**
- Input: text, image, audio, video, PDF
- Output: text with reasoning
- Context: 1M tokens (1,048,576)
- Vision: Excellent image understanding
- Speed: Fast inference
- Reasoning: Configurable levels (minimal, low, medium, high)
- Tool use: Supported

**Pricing:**
- Prompt: $0.50 per 1M tokens
- Completion: $3.00 per 1M tokens
- Image: $0.50 per 1M tokens
- Reasoning: $3.00 per 1M tokens

**Cost Per Conversation Turn:**
- Image input: ~$0.0005
- User message (500 tokens): ~$0.00025
- AI response (1000 tokens): ~$0.003
- **Total: ~$0.004 per turn**

**Why Recommended:**
- Best balance of cost, speed, and quality
- Excellent at understanding image manipulation requests
- Strong multi-turn conversation capability
- Low latency for interactive chat
- Handles complex visual reasoning
- Good at generating actionable instructions

**Example Use Cases:**
- "Make this image warmer and increase contrast"
- "Crop to focus on the person in the center"
- "Apply a vintage film look"
- "Adjust exposure, it's too dark"
- "Make it look like a watercolor painting"

#### Alternative Models

**1. Anthropic Claude Opus 4.6** (Premium)
- Model ID: `anthropic/claude-opus-4.6`
- Context: 1M tokens
- Pricing: $5-$25 per 1M tokens
- Best for: Complex multi-step manipulations
- Cost per turn: ~$0.03

**2. Google Gemini 2.5 Flash** (Budget)
- Model ID: `google/gemini-2.5-flash`
- Context: 1M tokens
- Pricing: $0.075-$0.30 per 1M tokens
- Best for: Simple adjustments, cost-conscious users
- Cost per turn: ~$0.001

**3. Mistral Pixtral Large** (Open Source)
- Model ID: `mistralai/pixtral-large-2411`
- Context: 128K tokens
- Pricing: $2-$6 per 1M tokens
- Best for: Users preferring open source
- Cost per turn: ~$0.005

#### Model Comparison Matrix

| Model | Input | Context | Cost/Turn | Speed | Quality | Best For |
|-------|-------|---------|-----------|-------|---------|----------|
| Gemini 3 Flash | text+image+video+audio | 1M | $0.004 | Fast | Excellent | Default choice |
| Claude Opus 4.6 | text+image | 1M | $0.03 | Medium | Superior | Professional work |
| Gemini 2.5 Flash | text+image+video+audio | 1M | $0.001 | Very Fast | Good | Budget option |
| Pixtral Large | text+image | 128K | $0.005 | Medium | Very Good | Open source |

---

### A.5 Model Discovery and Selection

**Dynamic Model Loading:**
```python
async def get_vision_models():
    response = requests.get("https://openrouter.ai/api/v1/models")
    all_models = response.json()['data']
    
    # Filter for vision-capable models
    vision_models = [
        model for model in all_models
        if 'image' in model['architecture']['input_modalities']
        and 'text' in model['architecture']['output_modalities']
    ]
    
    # Sort by pricing (lowest first)
    vision_models.sort(key=lambda m: float(m['pricing']['prompt']))
    
    return vision_models
```

**Model Metadata Structure:**
```json
{
  "id": "google/gemini-3-flash-preview",
  "name": "Google: Gemini 3 Flash Preview",
  "description": "High speed, high value thinking model...",
  "context_length": 1048576,
  "architecture": {
    "modality": "text+image+file+audio+video->text",
    "input_modalities": ["text", "image", "file", "audio", "video"],
    "output_modalities": ["text"]
  },
  "pricing": {
    "prompt": "0.0000005",
    "completion": "0.000003",
    "image": "0.0000005"
  }
}
```

**Model Selector UI Requirements:**
- Typeahead search by name
- Filter by tags (vision, reasoning, fast, etc.)
- Display: name, description, tags, estimated cost
- Show "Recommended" badge on default
- Allow favoriting models
- Display current selection in chat interface

---

### A.6 Image Manipulation Implementation Approach

Since OpenRouter models output text (not image edits), use a hybrid approach:

**Method 1: Text Instructions → Local Processing**
```
User: "Make this image 20% brighter"
AI: Analyzes and responds with structured instructions
Backend: Applies using Pillow
```

**Method 2: Image Generation**
```
User: "Make this look like an oil painting"
AI: Generates new image with style applied
Backend: Replaces original
```

**Method 3: Hybrid (Recommended)**
- Technical adjustments (brightness, contrast, etc.) → Local processing
- Artistic transformations (styles, effects) → Image generation (if supported)
- AI decides which approach based on request

**Implementation:**
```python
async def process_ai_chat_request(image_path, message, history):
    # Send to vision model
    response = await openrouter.chat(
        model="google/gemini-3-flash-preview",
        messages=[
            *history,
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": message},
                    {"type": "image_url", "image_url": {"url": encode_image(image_path)}}
                ]
            }
        ]
    )
    
    # Parse AI response for operations
    ai_text = response.choices[0].message.content
    operations = parse_image_operations(ai_text)
    
    # Apply operations
    result_path = apply_operations(image_path, operations)
    
    return result_path, ai_text
```

**Supported Operations (Pillow-based):**
- Brightness, contrast, saturation adjustments
- Color temperature changes
- Rotation, flip, crop
- Filters (grayscale, sepia, blur, sharpen)
- Resize
- Color balance

**AI-Generated Operations (Future):**
- Style transfers
- Artistic effects
- Complex compositing
- Generative fills

---

### A.7 Cost Estimation and Tracking

**Estimated Monthly Costs:**

**Light Personal Use:**
- 20 background removals: $0.00 (rembg)
- 50 AI chat turns: $0.20 (Gemini 3 Flash)
- Total: **$0.20/month**

**Moderate Use:**
- 50 background removals: $0.00
- 150 AI chat turns: $0.60
- Total: **$0.60/month**

**Heavy Use:**
- 200 background removals: $0.00
- 500 AI chat turns: $2.00
- Total: **$2.00/month**

**Cost Tracking Implementation:**
```python
class CostTracker:
    def __init__(self):
        self.conversation_costs = {}
    
    def calculate_request_cost(self, model, tokens_in, tokens_out, image_count):
        model_info = get_model_pricing(model)
        
        prompt_cost = tokens_in * float(model_info['pricing']['prompt'])
        completion_cost = tokens_out * float(model_info['pricing']['completion'])
        image_cost = image_count * float(model_info['pricing'].get('image', 0))
        
        return prompt_cost + completion_cost + image_cost
    
    def add_to_conversation(self, conversation_id, cost):
        if conversation_id not in self.conversation_costs:
            self.conversation_costs[conversation_id] = 0
        self.conversation_costs[conversation_id] += cost
```

**Cost Display in UI:**
- Show cost per message
- Running total for conversation
- Warning at threshold (e.g., $0.10)
- Monthly usage summary
- Cost comparison between models

---

### A.8 API Key Security

**Encryption Strategy:**
```python
from cryptography.fernet import Fernet
import os

# Generate encryption key (store in env)
ENCRYPTION_KEY = os.getenv('OPENROUTER_ENCRYPTION_KEY')

def encrypt_api_key(api_key: str) -> str:
    f = Fernet(ENCRYPTION_KEY.encode())
    encrypted = f.encrypt(api_key.encode())
    return encrypted.decode()

def decrypt_api_key(encrypted_key: str) -> str:
    f = Fernet(ENCRYPTION_KEY.encode())
    decrypted = f.decrypt(encrypted_key.encode())
    return decrypted.decode()
```

**Storage:**
- Store encrypted in settings table
- Never log API keys
- Never return in API responses
- Use separate encryption key (not in database)
- Rotate encryption key periodically

**Environment Variables:**
```bash
OPENROUTER_ENCRYPTION_KEY=base64_encoded_32_byte_key
```

---

### A.9 Error Handling and Fallbacks

**Common OpenRouter Errors:**

**Rate Limiting (429):**
```python
async def call_with_retry(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except RateLimitError:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
```

**Invalid Model (404):**
- Fallback to default model
- Notify user of model change
- Update settings

**Insufficient Credits (402):**
- Clear error message
- Link to OpenRouter account
- Suggest checking credit balance

**Model Unavailable (503):**
- Try backup model
- Queue request for retry
- Notify user of delay

---

### A.10 Implementation Updates for Stages 3 & 4

**Stage 3 Updated Scope:**

**Background Removal:**
- Use rembg Python library (primary)
- No OpenRouter API needed for this feature
- GPU acceleration if available
- Model selection: u2net, u2net_human_seg, isnet-general-use

**Settings UI:**
- Still implement OAuth2 PKCE (for Stage 4 prep)
- Add "Background Removal Method" dropdown:
  - Local (rembg) - Free
  - Cloud (Remove.bg) - Premium (future)
- Show AI as "enabled" if OAuth complete

**Dependencies to Add:**
```txt
rembg==2.0.50
onnxruntime-gpu==1.16.3  # GPU version
# OR
onnxruntime==1.16.3      # CPU version
```

**Stage 4 Updated Scope:**

**AI Chat:**
- Default model: google/gemini-3-flash-preview
- Dynamic model discovery from OpenRouter API
- Model selector with search/filter
- Cost tracking per message
- Conversation history persistence
- Hybrid manipulation approach (text instructions + local processing)

**Model Selector Features:**
- Fetch models on settings open
- Filter vision-capable models
- Display pricing, context length, capabilities
- Allow saving favorite models
- Show estimated cost per turn
- Recommended badge on default

**Settings Storage:**
```python
class Settings(Base):
    # ... existing fields ...
    
    # AI Configuration
    ai_chat_model = Column(String, default="google/gemini-3-flash-preview")
    ai_chat_model_custom = Column(String, nullable=True)
    background_removal_method = Column(String, default="rembg")
    background_removal_model = Column(String, default="u2net")
    
    # Cost Controls
    max_cost_per_request = Column(Float, default=0.10)
    monthly_cost_limit = Column(Float, default=10.00)
    show_cost_warnings = Column(Boolean, default=True)
```

---

### A.11 Updated Technology Stack

**Additional Python Dependencies:**
```txt
# Image Processing
rembg==2.0.50
onnxruntime-gpu==1.16.3  # or onnxruntime for CPU

# AI Integration  
openai==1.12.0  # OpenRouter uses OpenAI-compatible API
httpx==0.26.0   # Async HTTP client
tiktoken==0.5.2 # Token counting

# Security
cryptography==42.0.0
```

**No Additional Frontend Dependencies:**
- OAuth2 PKCE handled with native crypto API
- Model selection uses existing components

---

### A.12 Updated Environment Variables

Add to .env.example:

```bash
# ----------------------------------------------------------------------------
# AI Configuration (Stages 3-4)
# ----------------------------------------------------------------------------

# OpenRouter API
OPENROUTER_API_URL=https://openrouter.ai/api/v1
OPENROUTER_OAUTH_CALLBACK_URL=http://localhost:8000/app/oauth/callback

# Encryption for storing API keys
OPENROUTER_ENCRYPTION_KEY=generate-with-Fernet-generate_key()

# Background Removal
BACKGROUND_REMOVAL_METHOD=rembg
REMBG_MODEL=u2net
ENABLE_GPU_ACCELERATION=false

# AI Chat
DEFAULT_AI_CHAT_MODEL=google/gemini-3-flash-preview
MAX_COST_PER_REQUEST=0.10
MONTHLY_COST_LIMIT=10.00
ENABLE_COST_TRACKING=true

# Rate Limiting
OPENROUTER_MAX_REQUESTS_PER_MINUTE=30
OPENROUTER_TIMEOUT_SECONDS=60
```

---

### A.13 Implementation Timeline Updates

**Stage 3 Revised (3-4 days):**
- Day 1: OAuth2 PKCE implementation
- Day 2: rembg integration for background removal
- Day 3: Settings UI (Display + AI sections)
- Day 4: Testing and documentation

**Stage 4 Revised (5-6 days):**
- Day 1: OpenRouter client and model discovery
- Day 2: AI chat service and API endpoints
- Day 3-4: Chat UI components and integration
- Day 5: Cost tracking and model selector
- Day 6: Testing and documentation

**Total Timeline: 23-32 days** (slightly reduced from original 24-35 days)

---

### A.14 Testing Considerations

**Stage 3 Tests:**
- OAuth2 PKCE flow end-to-end
- Code verifier generation and validation
- API key encryption/decryption
- rembg background removal quality
- Different rembg models (u2net, u2net_human_seg)
- GPU vs CPU performance comparison
- Settings persistence

**Stage 4 Tests:**
- OpenRouter API connectivity
- Model discovery and filtering
- Vision model image understanding
- Multi-turn conversation handling
- Cost calculation accuracy
- Rate limiting and retries
- Error handling for various failure modes
- Conversation history persistence

---

### A.15 Documentation Updates Required

**DEVELOPER_GUIDE.md additions:**
- OAuth2 PKCE implementation details
- OpenRouter API integration patterns
- rembg installation and configuration
- GPU acceleration setup
- Cost tracking implementation
- Error handling strategies

**USER_GUIDE.md additions:**
- How to enroll OpenRouter API key
- Model selection guide
- Cost estimation and tracking
- Background removal options
- AI chat best practices
- Example prompts for image manipulation

**INSTALLATION.md additions:**
- rembg installation options (CPU vs GPU)
- OpenRouter account setup
- OAuth callback configuration
- Environment variable setup for AI features

---

## CONCLUSION (UPDATED)

This implementation strategy has been updated with comprehensive AI research findings from OpenRouter.ai. Key updates include:

1. **Stage 3 Background Removal:** Using rembg library instead of OpenRouter for better quality, zero cost, and no rate limits
2. **Stage 4 AI Chat:** Gemini 3 Flash Preview as default model with excellent balance of cost ($0.004/turn) and quality
3. **OAuth2 PKCE:** Detailed implementation guide for secure API key enrollment
4. **Cost Tracking:** Estimated monthly costs of $0.20-$2.00 for typical personal use
5. **Model Selection:** Dynamic discovery with user-configurable choices

The revised approach maintains all original goals while optimizing for cost, performance, and user experience based on actual API capabilities.

**Research Documents:**
- Detailed findings: AI_RESEARCH_FINDINGS.md
- Implementation strategy: This document

---

**Document Version:** 1.1  
**Last Updated:** February 6, 2026  
**Status:** Research Complete - Ready for Implementation
