# Image Tools - Stage 1 Implementation

Web-based image manipulation application with compression, undo, and bulk operations.

## Stage 1 Features

- Multi-image upload (drag-and-drop or click to browse)
- Session-based storage with automatic cleanup
- Compression presets (Email, Web, Web HQ, Custom)
- Per-image undo functionality (10 operations max)
- Bulk compression for selected images
- Download individual or multiple images
- Thumbnail gallery view
- Real-time compression ratio display

## Project Structure

```
ImageTools/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/  # API route handlers
│   │   ├── core/              # Config, database
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   └── main.py            # FastAPI application
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/        # Vue components
│   │   ├── stores/            # Pinia stores
│   │   ├── services/          # API client
│   │   ├── App.vue
│   │   └── main.js
│   ├── package.json
│   └── vite.config.js
└── .env                       # Environment configuration
```

## Quick Start

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create storage directories
mkdir -p storage/temp

# Run the backend
python -m app.main
```

Backend will run on: http://localhost:8001
API docs: http://localhost:8001/api/v1/docs

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend will run on: http://localhost:5173

## API Endpoints

### Sessions
- `POST /api/v1/sessions` - Create new session
- `GET /api/v1/sessions/{id}` - Get session details
- `GET /api/v1/sessions/{id}/validate` - Validate session

### Images
- `POST /api/v1/images` - Upload image
- `GET /api/v1/images/session/{session_id}` - Get session images
- `GET /api/v1/images/{id}` - Get image metadata
- `GET /api/v1/images/{id}/current` - Download current version
- `GET /api/v1/images/{id}/thumbnail` - Get thumbnail
- `DELETE /api/v1/images/{id}` - Delete image

### Compression
- `POST /api/v1/compression/{image_id}` - Compress image
- `GET /api/v1/compression/presets` - Get available presets

### History
- `GET /api/v1/history/{image_id}` - Get operation history
- `POST /api/v1/history/{image_id}/undo` - Undo last operation
- `GET /api/v1/history/{image_id}/can-undo` - Check undo availability

## Configuration

Edit `.env` file to customize:

```bash
# Session settings
SESSION_EXPIRY_DAYS=7
MAX_IMAGES_PER_SESSION=5

# Compression presets
EMAIL_MAX_WIDTH=800
EMAIL_MAX_HEIGHT=800
EMAIL_QUALITY=85
EMAIL_TARGET_SIZE_KB=500

# Undo limit
UNDO_STACK_LIMIT=10
```

## Development

- Backend uses FastAPI with async SQLAlchemy
- Frontend uses Vue 3 with Composition API and Pinia
- Image processing with Pillow
- Simple console logging (not structured JSON)

## Testing

### Backend
```bash
cd backend
pytest
```

### Manual Testing
1. Start backend and frontend
2. Navigate to http://localhost:5173
3. Upload 2-3 images
4. Test compression with different presets
5. Test undo functionality
6. Test bulk operations
7. Test download
8. Test delete

## Next Steps (Stage 2)

- TUI Image Editor integration
- Advanced editing capabilities
- Editor modal component
