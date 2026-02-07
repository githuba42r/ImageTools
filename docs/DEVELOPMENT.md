# Development Scripts

This directory contains scripts to help with local development of ImageTools.

## Available Scripts

### `./dev-all.sh` (Recommended for Development)
Starts both backend and frontend in a single terminal with hot-reload enabled.

**Features:**
- Single terminal window
- Hot-reload for both backend and frontend
- Automatic dependency installation
- Logs written to `backend.log` and `frontend.log`
- Graceful shutdown with Ctrl+C

**Usage:**
```bash
./dev-all.sh
```

**Ports:**
- Backend: http://localhost:8081
- Frontend: http://localhost:5173
- API Docs: http://localhost:8081/docs

---

### `./run-all.sh`
Starts both backend and frontend in separate terminal windows.

**Features:**
- Separate terminal windows for backend and frontend
- Good for monitoring each service independently
- Works with gnome-terminal, xterm, or konsole

**Usage:**
```bash
./run-all.sh
```

---

### `./run-backend.sh`
Starts only the backend server.

**Usage:**
```bash
./run-backend.sh
```

**Runs at:** http://localhost:8081

---

### `./run-frontend.sh`
Starts only the frontend development server.

**Usage:**
```bash
./run-frontend.sh
```

**Runs at:** http://localhost:5173

**Note:** Make sure backend is running first!

---

## Quick Start

1. **First time setup:**
   ```bash
   ./dev-all.sh
   ```
   This will automatically:
   - Create Python virtual environment
   - Install all backend dependencies
   - Install all frontend dependencies
   - Create required directories
   - Start both servers with hot-reload

2. **Access the application:**
   - Open http://localhost:5173 in your browser
   - Backend API docs: http://localhost:8081/docs

3. **Stop servers:**
   - Press `Ctrl+C` in the terminal

---

## Configuration

### Port Configuration
Default ports are configured in:
- Backend: `backend/app/core/config.py` (PORT = 8081)
- Frontend: `frontend/vite.config.js` (PORT = 5173)

You can override the backend API URL with environment variables:
```bash
VITE_API_URL=http://localhost:9000 ./dev-all.sh
```

### Environment Variables
Create a `.env` file in the `backend/` directory for custom configuration:
```env
SERVER_PORT=8081
DEBUG=True
LOG_LEVEL=DEBUG
SESSION_SECRET_KEY=your-secret-key
OPENROUTER_API_KEY=your-api-key  # Optional
```

---

## Troubleshooting

### Backend won't start
```bash
# Check logs
tail -f backend.log

# Common issues:
# - Port 8081 already in use
# - Missing dependencies
# - Database locked
```

### Frontend won't start
```bash
# Check logs
tail -f frontend.log

# Common issues:
# - Port 5173 already in use
# - Missing node_modules (run: cd frontend && npm install)
```

### Hot-reload not working
- Backend: Uvicorn auto-reloads on .py file changes
- Frontend: Vite HMR auto-reloads on .vue/.js file changes
- If stuck, restart the dev server

---

## Development Workflow

1. **Start development environment:**
   ```bash
   ./dev-all.sh
   ```

2. **Make changes:**
   - Edit files in `backend/` or `frontend/`
   - Changes auto-reload (no restart needed)

3. **View logs:**
   ```bash
   # Tail logs in another terminal
   tail -f backend.log frontend.log
   ```

4. **Test API endpoints:**
   - Open http://localhost:8081/docs
   - Interactive API documentation (Swagger UI)

5. **Commit changes:**
   ```bash
   git add .
   git commit -m "Your commit message"
   ```

---

## Production Deployment

These scripts are for **development only**. For production:

1. Build frontend:
   ```bash
   cd frontend
   npm run build
   ```

2. Run backend with production server:
   ```bash
   cd backend
   source venv/bin/activate
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
   ```

3. Serve frontend build:
   - Use nginx, Apache, or serve the `frontend/dist` folder
   - Configure reverse proxy to backend

---

## Tips

- **Fast restart:** Just kill the terminal and run `./dev-all.sh` again
- **Clear logs:** `rm backend.log frontend.log`
- **Reset database:** `rm backend/storage/imagetools.db` (loses all data!)
- **Update dependencies:** 
  ```bash
  cd backend && source venv/bin/activate && pip install -r requirements.txt
  cd frontend && npm install
  ```
