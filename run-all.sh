#!/bin/bash

# Complete startup script for Image Tools (both backend and frontend)

echo "=========================================="
echo "Image Tools - Complete Startup"
echo "=========================================="
echo ""

# Check if we're in the project root
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

echo "This script will start both backend and frontend in separate terminal windows."
echo ""

# Check for required commands
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed"
    exit 1
fi

# Function to start in new terminal (works on Linux with common terminals)
start_in_terminal() {
    local title=$1
    local command=$2
    
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal --title="$title" -- bash -c "$command; exec bash"
    elif command -v xterm &> /dev/null; then
        xterm -title "$title" -e bash -c "$command; exec bash" &
    elif command -v konsole &> /dev/null; then
        konsole --title "$title" -e bash -c "$command; exec bash" &
    else
        echo "Could not detect terminal emulator. Starting in background..."
        bash -c "$command" &
    fi
}

echo "Starting backend..."
start_in_terminal "Image Tools - Backend" "cd backend && source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate && pip install -q -r requirements.txt && mkdir -p storage/temp && echo 'Backend ready on http://localhost:8001' && python -m app.main"

echo "Waiting 3 seconds for backend to initialize..."
sleep 3

echo "Starting frontend..."
start_in_terminal "Image Tools - Frontend" "cd frontend && ([ -d node_modules ] || npm install) && echo 'Frontend ready on http://localhost:5173' && npm run dev"

echo ""
echo "=========================================="
echo "Image Tools is starting!"
echo "=========================================="
echo ""
echo "Backend:  http://localhost:8001"
echo "API Docs: http://localhost:8001/api/v1/docs"
echo "Frontend: http://localhost:5173"
echo ""
echo "Check the new terminal windows for logs."
echo "Press Ctrl+C in each terminal to stop the servers."
echo ""
