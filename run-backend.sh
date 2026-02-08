#!/bin/bash

# Backend startup script for Image Tools

echo "=========================================="
echo "Starting Image Tools Backend"
echo "=========================================="
echo ""

# Check if we're in the project root
if [ ! -d "backend" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

cd backend

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created."
    echo ""
fi

# Activate venv
echo "Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "Dependencies installed."
echo ""

# Create storage directories
echo "Creating storage directories..."
mkdir -p storage/temp
echo "Storage directories ready."
echo ""

# Load environment variables from .env.development if it exists
if [ -f ".env.development" ]; then
    echo "Loading environment from .env.development..."
    export $(grep -v '^#' .env.development | xargs)
fi

# Use SERVER_PORT from environment or default to 8081
BACKEND_PORT=${SERVER_PORT:-8081}

# Run the backend
echo "=========================================="
echo "Backend starting on http://localhost:$BACKEND_PORT"
echo "API docs: http://localhost:$BACKEND_PORT/docs"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python -m uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload
