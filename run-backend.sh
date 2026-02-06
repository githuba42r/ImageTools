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

# Run the backend
echo "=========================================="
echo "Backend starting on http://localhost:8001"
echo "API docs: http://localhost:8001/api/v1/docs"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python -m app.main
