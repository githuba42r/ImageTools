# Multi-stage build for ImageTools - Single container with frontend + backend

# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Final image with backend + built frontend
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for image processing
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ ./

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Create storage directory
RUN mkdir -p /app/storage/temp

# Expose port 8081 (backend will serve both API and static files)
EXPOSE 8081

# Environment variables
ENV DEBUG=False
ENV LOG_LEVEL=INFO
ENV SERVER_HOST=0.0.0.0
ENV SERVER_PORT=8081
ENV SESSION_EXPIRY_DAYS=7
ENV MAX_IMAGES_PER_SESSION=5
ENV MAX_UPLOAD_SIZE_MB=20

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081"]
