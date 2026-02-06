#!/bin/bash

# Frontend startup script for Image Tools

echo "=========================================="
echo "Starting Image Tools Frontend"
echo "=========================================="
echo ""

# Check if we're in the project root
if [ ! -d "frontend" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
    echo "Dependencies installed."
    echo ""
fi

# Run the frontend
echo "=========================================="
echo "Frontend starting on http://localhost:5173"
echo "=========================================="
echo ""
echo "Make sure the backend is running on http://localhost:8081"
echo "Press Ctrl+C to stop the server"
echo ""

npm run dev
