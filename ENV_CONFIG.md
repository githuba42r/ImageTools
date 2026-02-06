# Image Tools - Environment Configuration

## Quick Setup

### Backend Configuration
The backend configuration is in `/backend/.env` (or uses the root `.env` file).

Key settings:
- `SERVER_PORT`: Backend port (default: 8001)
- `SERVER_HOST`: Backend host (default: 0.0.0.0)
- `API_PREFIX`: API path prefix (default: /api/v1)

### Frontend Configuration
The frontend configuration is in `/frontend/.env`.

Key settings:
- `VITE_API_URL`: Backend API URL for Vite proxy (default: http://localhost:8001)

## Port Conflicts

If you get a port conflict (e.g., Apache is using port 8001), you have two options:

### Option 1: Change Backend Port (Recommended for Development)

1. Update `/frontend/.env`:
   ```
   VITE_API_URL=http://localhost:8081
   ```

2. Start the backend with a different port:
   ```bash
   cd backend
   source venv/bin/activate
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
   ```

3. Restart the frontend to pick up the new proxy configuration

### Option 2: Free Up Port 8001

1. Stop the service using port 8001:
   ```bash
   # Find what's using port 8001
   sudo lsof -i :8001
   
   # Stop Apache if it's using the port
   sudo systemctl stop apache2
   ```

2. Use the default configuration (port 8001)

## Current Configuration

Based on your current setup:
- **Backend**: Running on port 8081 (manually started to avoid Apache conflict)
- **Frontend**: Configured to proxy to port 8081 via `VITE_API_URL`
- **Vite Dev Server**: Running on port 5173

## Testing the Configuration

1. Check backend is accessible:
   ```bash
   curl http://localhost:8081/health
   # Should return: {"status":"healthy"}
   ```

2. Check frontend proxy is working:
   - Open http://localhost:5173 in your browser
   - Open browser dev tools and check Network tab
   - API calls to `/api/v1/*` should be proxied to the backend

## Environment Variables Summary

### Backend (.env in root or backend/)
```bash
SERVER_PORT=8001              # Backend port
SERVER_HOST=0.0.0.0           # Backend host
API_PREFIX=/api/v1            # API path prefix
DEBUG=false                   # Debug mode
LOG_LEVEL=INFO                # Log level
CORS_ENABLED=true             # Enable CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Frontend (.env in frontend/)
```bash
VITE_API_URL=http://localhost:8081  # Backend URL for proxy
```

## Troubleshooting

### "Failed to initialize application: Request failed with status code 404"

This error occurs when the frontend can't reach the backend. Check:

1. Backend is running:
   ```bash
   curl http://localhost:8081/api/v1/compression/presets
   ```

2. Frontend `.env` has correct backend URL:
   ```bash
   cat frontend/.env
   # Should show: VITE_API_URL=http://localhost:8081
   ```

3. Frontend dev server has been restarted after changing `.env`

### Port Already in Use

If you see "Address already in use" error:

1. Find what's using the port:
   ```bash
   sudo lsof -i :<PORT>
   ```

2. Either stop that service or use a different port
