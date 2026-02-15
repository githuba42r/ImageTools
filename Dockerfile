# syntax=docker/dockerfile:1
# Multi-stage build for ImageTools - Single container with frontend + backend
#
# Build caching strategy:
# - Stage 1 (python-base): System packages - rarely changes
# - Stage 2 (python-deps): Python packages - changes when requirements.txt changes
# - Stage 3 (frontend-deps): Node modules - changes only when dependencies change
# - Stage 4 (frontend-builder): Frontend build - changes when source code changes
# - Stage 5 (final): Combines everything
#
# Docker layer caching note: frontend/package.json uses a fixed placeholder version
# (0.0.0-docker) so version bumps don't invalidate the npm install layer.
# The actual version is served at runtime via the /version endpoint.

# Build arguments
ARG VERSION=dev
ARG BUILD_DATE=unknown

# ==============================================================================
# Stage 1: Python base with system dependencies (rarely changes)
# ==============================================================================
FROM python:3.11-slim AS python-base

# Install system dependencies for image processing
# This layer is cached unless the base image or these packages change
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ==============================================================================
# Stage 2: Python dependencies (changes when requirements.txt changes)
# ==============================================================================
FROM python-base AS python-deps

WORKDIR /app

# Copy only requirements.txt first for better caching
# This layer is rebuilt only when requirements.txt changes
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ==============================================================================
# Stage 3: Frontend dependencies (changes only when dependencies change)
# ==============================================================================
FROM node:20-alpine AS frontend-deps

WORKDIR /app/frontend

# Copy package files for dependency installation
# Note: package.json uses a fixed version (0.0.0-docker) so version bumps
# don't invalidate this layer - the actual version is served at runtime
COPY frontend/package.json frontend/package-lock.json* ./

# Install dependencies - this layer is cached unless actual dependencies change
RUN npm ci --ignore-scripts 2>/dev/null || npm install

# ==============================================================================
# Stage 4: Frontend build (changes when frontend source changes)
# ==============================================================================
FROM frontend-deps AS frontend-builder

WORKDIR /app/frontend

# Copy frontend source code
COPY frontend/ ./

# Build the frontend
# The version is loaded at runtime from /version endpoint, not baked in
RUN npm run build

# ==============================================================================
# Stage 5: Final image
# ==============================================================================
FROM python-deps AS final

# Re-declare build arguments for labels
ARG VERSION=dev
ARG BUILD_DATE=unknown

WORKDIR /app

# Copy backend application code
COPY backend/ ./

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Copy version.json last - this changes frequently but doesn't affect any builds
# It's served by the backend at runtime via the /version endpoint
COPY version.json /version.json

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

# Add version and build date labels
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.title="ImageTools"
LABEL org.opencontainers.image.description="Multi-user image sharing and management platform"

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081"]
