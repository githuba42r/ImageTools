# Docker Deployment Guide

This guide explains how to build and deploy ImageTools using Docker. The application is packaged as a single Docker image containing both the frontend (Vue.js) and backend (FastAPI).

## Architecture

The Docker deployment uses a **multi-stage build** approach:

1. **Stage 1 (frontend-builder)**: Builds the Vue.js frontend using Node.js
2. **Stage 2 (final image)**: Python-based image containing:
   - FastAPI backend application
   - Pre-built frontend static files
   - All dependencies for image processing (PIL, rembg, etc.)

The backend serves both the API endpoints AND the frontend static files, creating a unified single-container deployment.

## Prerequisites

- Docker 20.10+ 
- Docker Compose 2.0+ (optional, for easier management)
- 2GB+ RAM recommended for image processing operations
- 5GB+ disk space for Docker images and volumes

## Quick Start

### Option 1: Using Docker Compose (Recommended)

```bash
# Build and start the container
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

The application will be available at:
- Frontend: http://localhost:8082
- API: http://localhost:8082/api/v1/
- API Docs: http://localhost:8082/api/v1/docs
- Health Check: http://localhost:8082/health

### Option 2: Using Docker Directly

```bash
# Build the image
docker build -t imagetools .

# Run the container
docker run -d \
  --name imagetools \
  -p 8082:8081 \
  -v imagetools-storage:/app/storage \
  -e OPENROUTER_API_KEY=your_api_key_here \
  imagetools

# View logs
docker logs -f imagetools

# Stop the container
docker stop imagetools
docker rm imagetools
```

## Configuration

### Environment Variables

The following environment variables can be configured in `docker-compose.yml` or passed via `-e` flags:

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `False` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `SERVER_HOST` | `0.0.0.0` | Server bind address |
| `SERVER_PORT` | `8081` | Internal server port (container) |
| `SESSION_EXPIRY_DAYS` | `7` | Session expiration time |
| `MAX_IMAGES_PER_SESSION` | `5` | Maximum images per session |
| `MAX_UPLOAD_SIZE_MB` | `20` | Maximum upload file size |
| `OPENROUTER_API_KEY` | (empty) | OpenRouter API key for AI features |

### Port Mapping

By default, the container exposes port **8081** internally and maps to **8082** on the host to avoid conflicts with common development servers.

To change the host port, modify the port mapping:

```yaml
# docker-compose.yml
ports:
  - "3000:8081"  # Access at http://localhost:3000
```

Or with docker run:

```bash
docker run -p 3000:8081 imagetools
```

### Persistent Storage

The container uses a Docker volume to persist:
- Uploaded images
- Processed images
- Session data (SQLite database)

**Volume location**: `/app/storage` (inside container)

To backup your data:

```bash
# Create backup
docker run --rm \
  -v imagetools-storage:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/imagetools-backup.tar.gz -C /data .

# Restore backup
docker run --rm \
  -v imagetools-storage:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/imagetools-backup.tar.gz -C /data
```

## Building from Source

### Build Process

The Dockerfile uses a multi-stage build:

1. **Frontend Build** (Node.js):
   ```bash
   # Copies package.json and installs npm dependencies
   # Copies frontend source code
   # Runs `npm run build` to create production bundle
   ```

2. **Backend Build** (Python):
   ```bash
   # Installs system dependencies (libgl1, libglib2.0-0)
   # Installs Python packages from requirements.txt
   # Copies backend application code
   # Copies built frontend from previous stage
   ```

### Build Arguments

Currently, the Dockerfile does not use build arguments, but you can add them for customization:

```dockerfile
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim
```

Then build with:

```bash
docker build --build-arg PYTHON_VERSION=3.12 -t imagetools .
```

## Deployment Scenarios

### Development

For development, you may want to:

1. **Enable debug mode**:
   ```yaml
   environment:
     - DEBUG=True
     - LOG_LEVEL=DEBUG
   ```

2. **Mount source code** (requires modifying docker-compose.yml):
   ```yaml
   volumes:
     - ./backend:/app
     - imagetools-storage:/app/storage
   ```

### Production

For production deployment:

1. **Set appropriate environment**:
   ```yaml
   environment:
     - DEBUG=False
     - LOG_LEVEL=WARNING
     - SESSION_EXPIRY_DAYS=30
   ```

2. **Add reverse proxy** (nginx/Traefik) for:
   - HTTPS termination
   - Domain name mapping
   - Load balancing (if scaling)

3. **Consider resource limits**:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 2G
       reservations:
         memory: 512M
   ```

4. **Use external database** (optional):
   - Currently uses SQLite (file-based)
   - For multi-container setups, consider PostgreSQL
   - Would require backend code modifications

### Behind Reverse Proxy

Example nginx configuration:

```nginx
server {
    listen 80;
    server_name imagetools.example.com;
    
    client_max_body_size 20M;
    
    location / {
        proxy_pass http://localhost:8082;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running operations
        proxy_read_timeout 600s;
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
    }
}
```

## Troubleshooting

### Container won't start

**Check logs**:
```bash
docker logs imagetools
```

**Common issues**:
- Port already in use: Change host port mapping
- Permission denied: Ensure Docker has necessary permissions
- Out of memory: Increase Docker memory limit

### Health check failing

Test the health endpoint:
```bash
curl http://localhost:8082/health
```

Expected response:
```json
{"status":"healthy"}
```

If failing:
- Container may still be starting (wait 10-30 seconds)
- Port mapping may be incorrect
- Backend process may have crashed (check logs)

### Frontend not loading

**Verify frontend files exist**:
```bash
docker exec imagetools ls -la /app/frontend/dist/
```

Should show `index.html` and `assets/` directory.

**Check backend is serving files**:
```bash
curl -I http://localhost:8082/
```

Should return HTTP 200 with HTML content.

### Image processing fails

**Check system dependencies**:
```bash
docker exec imagetools python -c "from PIL import Image; from rembg import remove; print('OK')"
```

If this fails, the image may need rebuilding with correct dependencies.

### API Key not working

**Verify environment variable**:
```bash
docker exec imagetools printenv | grep OPENROUTER
```

**Set it properly**:
```bash
# In docker-compose.yml
environment:
  - OPENROUTER_API_KEY=sk-or-v1-xxxxx

# Or create .env file
echo "OPENROUTER_API_KEY=sk-or-v1-xxxxx" > .env
docker-compose up -d
```

## Performance Optimization

### Image Size

Current image size: ~2.5GB (due to scientific Python libraries)

To reduce:
1. Use multi-stage builds (already implemented)
2. Remove unnecessary dependencies
3. Use Alpine-based images (may have compatibility issues with some libraries)

### Startup Time

Typical startup: 5-15 seconds

Factors affecting startup:
- Database initialization
- Model loading (for background removal)
- System resource availability

### Runtime Performance

- **CPU**: Image processing is CPU-intensive
- **Memory**: 512MB minimum, 2GB recommended
- **Disk I/O**: Fast storage improves image operations

### Scaling

To run multiple instances:

```yaml
version: '3.8'

services:
  imagetools:
    image: imagetools
    deploy:
      replicas: 3
    ports:
      - "8082-8084:8081"
    volumes:
      - imagetools-storage:/app/storage
```

**Note**: SQLite is file-based and not ideal for multi-container setups. Consider PostgreSQL for horizontal scaling.

## Security Considerations

1. **Secrets Management**:
   - Don't commit `.env` files
   - Use Docker secrets or external secret management
   - Rotate API keys regularly

2. **Network Isolation**:
   - Run behind reverse proxy
   - Don't expose port directly to internet
   - Use firewall rules

3. **File Upload Security**:
   - Max file size enforced (20MB default)
   - File type validation in backend
   - Temporary files cleaned up after processing

4. **Updates**:
   - Regularly rebuild with updated base images
   - Monitor for security advisories
   - Keep dependencies up to date

## Maintenance

### Updating the Application

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up --build -d

# Verify health
curl http://localhost:8082/health
```

### Cleaning Up

```bash
# Remove stopped containers
docker-compose down

# Remove volumes (deletes data!)
docker-compose down -v

# Remove old images
docker image prune -a

# Remove build cache
docker builder prune
```

### Monitoring

**View logs**:
```bash
docker-compose logs -f --tail=100
```

**Check resource usage**:
```bash
docker stats imagetools
```

**Check disk usage**:
```bash
docker system df
```

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangzhou.com/)
- [Vue.js Documentation](https://vuejs.org/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review application logs
3. Open an issue in the project repository
4. Consult the main README.md for application-specific help
