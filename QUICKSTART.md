# Quick Start Guide

## Prerequisites

- Python 3.11+ installed
- Node.js 20+ installed
- npm installed

## Option 1: Run Everything at Once (Recommended)

```bash
# From project root
./run-all.sh
```

This will:
- Create Python venv if needed
- Install backend dependencies
- Install frontend dependencies
- Start backend in a new terminal window
- Start frontend in a new terminal window

Then open your browser to: **http://localhost:5173**

---

## Option 2: Run Manually (Two Terminals)

### Terminal 1 - Backend

```bash
./run-backend.sh
```

Wait until you see: "Uvicorn running on http://0.0.0.0:8001"

### Terminal 2 - Frontend

```bash
./run-frontend.sh
```

Wait until you see: "Local: http://localhost:5173"

Then open your browser to: **http://localhost:5173**

---

## Option 3: Manual Step-by-Step

### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create storage directory
mkdir -p storage/temp

# Run backend
python -m app.main
```

Backend runs on: **http://localhost:8001**
API Documentation: **http://localhost:8001/api/v1/docs**

### Frontend Setup (New Terminal)

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend runs on: **http://localhost:5173**

---

## Testing the Application

1. Open **http://localhost:5173** in your browser
2. Drag and drop 2-3 images to the upload area
3. Click on "Email" preset for one image and click "Compress"
4. Watch the compression ratio appear
5. Click "Undo" to revert
6. Select multiple images with checkboxes
7. Use toolbar to bulk compress selected images
8. Download images
9. Delete an image

---

## Troubleshooting

### Backend won't start
- Check Python version: `python3 --version` (need 3.11+)
- Check if port 8001 is available: `lsof -i :8001`
- Check backend logs for errors

### Frontend won't start
- Check Node version: `node --version` (need 20+)
- Check if port 5173 is available: `lsof -i :5173`
- Try: `cd frontend && rm -rf node_modules && npm install`

### Backend and frontend can't connect
- Make sure backend is running first
- Check backend is on http://localhost:8001
- Check browser console for CORS errors

### "Module not found" errors
- Backend: Make sure venv is activated and dependencies installed
- Frontend: Run `npm install` in frontend directory

---

## Stopping the Servers

Press **Ctrl+C** in each terminal window running the servers.

---

## Next Steps

- Review code in your editor
- Check `STAGE1_IMPLEMENTATION_SUMMARY.md` for detailed implementation info
- Check `README_STAGE1.md` for complete documentation
- Review API documentation at http://localhost:8001/api/v1/docs

---

## File Locations

```
ImageTools/
├── run-all.sh          ← Run everything (recommended)
├── run-backend.sh      ← Run backend only
├── run-frontend.sh     ← Run frontend only
├── QUICKSTART.md       ← This file
├── backend/            ← Python FastAPI backend
└── frontend/           ← Vue 3 frontend
```
