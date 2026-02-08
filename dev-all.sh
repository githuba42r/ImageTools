#!/bin/bash

# Development startup script for Image Tools
# Starts both backend and frontend with hot-reload for local development

echo "=========================================="
echo "Image Tools - Development Mode"
echo "=========================================="
echo ""

# Check if we're in the project root
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

# Check for required commands
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "Servers stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "Setting up backend..."
cd backend

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created."
fi

# Activate venv and install dependencies
source venv/bin/activate
echo "Installing/updating backend dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Create storage directories
mkdir -p storage/temp

# Load environment variables from .env.development if it exists
if [ -f ".env.development" ]; then
    echo "Loading environment from .env.development..."
    export $(grep -v '^#' .env.development | xargs)
fi

# Use SERVER_PORT from environment or default to 8081
BACKEND_PORT=${SERVER_PORT:-8081}

echo "Backend setup complete."
echo ""

# Start backend in background
echo "Starting backend server on http://localhost:$BACKEND_PORT..."
./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload > ../backend.log 2>&1 &
BACKEND_PID=$!

cd ..

echo "Waiting for backend to start..."
sleep 3

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "Error: Backend failed to start. Check backend.log for details."
    exit 1
fi

echo "Backend ready!"
echo ""

echo "Setting up frontend..."
cd frontend

# Install npm dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi

echo "Frontend setup complete."
echo ""

# Start frontend in background
echo "Starting frontend server on http://localhost:5173..."
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!

cd ..

# Get local network IP
LOCAL_IP=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -1)

echo ""
echo "=========================================="
echo "Image Tools is running in development mode!"
echo "=========================================="
echo ""
echo "Local Access:"
echo "  Backend:  http://localhost:$BACKEND_PORT"
echo "  API Docs: http://localhost:$BACKEND_PORT/docs"
echo "  Frontend: http://localhost:5173"
echo ""
if [ -n "$LOCAL_IP" ]; then
echo "Network Access (for mobile devices):"
echo "  Backend:  http://$LOCAL_IP:$BACKEND_PORT"
echo "  Frontend: http://$LOCAL_IP:5173"
echo ""
fi
echo "Features:"
echo "  - Hot-reload enabled (changes auto-reload)"
echo "  - Backend logs: backend.log"
echo "  - Frontend logs: frontend.log"
echo "  - Mobile app can connect from network"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Tail logs
tail -f backend.log frontend.log &
TAIL_PID=$!

# Wait for user interrupt
wait $BACKEND_PID $FRONTEND_PID
