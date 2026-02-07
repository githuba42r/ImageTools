# ImageTools Deployment with Nginx Reverse Proxy and Basic Auth

This directory contains deployment configuration for running ImageTools with an Nginx reverse proxy providing HTTP Basic Authentication.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Authentication Methods](#authentication-methods)
- [Configuration](#configuration)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

## Features

- **Nginx Reverse Proxy**: Single entry point for the application
- **HTTP Basic Authentication**: Password protection for the entire application
- **WebSocket Support**: Real-time offline detection and communication
- **Two Authentication Modes**:
  - Simple mode: Single username/password via environment variables
  - Advanced mode: Custom htpasswd file with multiple users
- **Persistent Storage**: Volumes for images, database, and auth credentials
- **Auto-Configuration**: Automatic htpasswd generation with smart overwrite protection
- **Health Monitoring**: Integrated health checks for both services

## Quick Start

### Option 1: Simple Authentication (Single User)

1. Navigate to the deployment directory:
```bash
cd deployment
```

2. Copy the example environment file:
```bash
cp .env.example .env
```

3. Edit `.env` and set your credentials:
```bash
DFLT_USERNAME=admin
DFLT_PASSWORD=your_secure_password_here
APP_NAME=My Image Tools
```

4. Start the services:
```bash
docker-compose up -d
```

5. Access the application at `http://localhost` and log in with your credentials

### Option 2: Multiple Users with Custom htpasswd File

1. Create a custom htpasswd file with multiple users:
```bash
# Create directory for htpasswd
mkdir -p htpasswd

# Add first user (will create file)
htpasswd -c htpasswd/.htpasswd user1

# Add additional users (no -c flag)
htpasswd htpasswd/.htpasswd user2
htpasswd htpasswd/.htpasswd user3
```

2. Create `.env` file WITHOUT DFLT_USERNAME/DFLT_PASSWORD:
```bash
cp .env.example .env
# Edit and remove or comment out DFLT_USERNAME and DFLT_PASSWORD
```

3. Update `docker-compose.yml` to mount your htpasswd directory:
```yaml
services:
  nginx:
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf.template:ro
      - ./nginx/docker-entrypoint.sh:/docker-entrypoint.sh:ro
      - ./htpasswd:/etc/nginx/htpasswd  # ← Use local directory instead of volume
```

4. Start the services:
```bash
docker-compose up -d
```

## Authentication Methods

### Method 1: Simple Mode (Environment Variables)

**Best for**: Single user, quick setup, testing

**How it works**:
- Set `DFLT_USERNAME` and `DFLT_PASSWORD` in `.env`
- On first run, entrypoint script creates htpasswd file automatically
- File is stored in persistent volume `nginx-htpasswd`
- **Will NOT overwrite** existing htpasswd file

**Advantages**:
- Simplest setup
- No manual htpasswd file creation
- Credentials in environment variables (can use secrets management)

**Example**:
```bash
# .env
DFLT_USERNAME=admin
DFLT_PASSWORD=MySecurePass123!
APP_NAME=Image Tools Production
```

### Method 2: Custom htpasswd File

**Best for**: Multiple users, fine-grained control, production environments

**How it works**:
- Create htpasswd file manually with `htpasswd` command
- Mount as volume in docker-compose.yml
- Entrypoint script detects existing file and uses it
- Full control over user management

**Advantages**:
- Multiple users with different passwords
- Standard Apache htpasswd format
- Can use bcrypt, MD5, SHA, or crypt encryption
- Easy to add/remove users without restarting

**Example**:
```bash
# Create htpasswd file with multiple users
mkdir -p htpasswd
htpasswd -c htpasswd/.htpasswd admin
htpasswd htpasswd/.htpasswd user1
htpasswd htpasswd/.htpasswd user2

# Verify users
cat htpasswd/.htpasswd
# Output:
# admin:$apr1$...
# user1:$apr1$...
# user2:$apr1$...
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_NAME` | No | `Image Tools` | Application name displayed in browser auth prompt |
| `DFLT_USERNAME` | Conditional | - | Simple auth: username (required if no htpasswd file) |
| `DFLT_PASSWORD` | Conditional | - | Simple auth: password (required if no htpasswd file) |
| `SESSION_EXPIRY_DAYS` | No | `7` | Days until uploaded images expire |
| `MAX_IMAGES_PER_SESSION` | No | `5` | Maximum images per user session |
| `MAX_UPLOAD_SIZE_MB` | No | `20` | Maximum upload size in megabytes |
| `OPENROUTER_CLIENT_ID` | No | - | OpenRouter OAuth client ID (for AI features) |
| `OPENROUTER_CLIENT_SECRET` | No | - | OpenRouter OAuth client secret |
| `OAUTH_REDIRECT_URL` | No | - | OAuth redirect URL (e.g., `http://yourdomain.com/api/v1/openrouter/callback`) |

### Ports

| Service | Internal Port | External Port | Description |
|---------|---------------|---------------|-------------|
| Nginx | 80 | 80 | HTTP entry point (with basic auth) |
| ImageTools | 8081 | - | Backend (internal only, proxied through nginx) |

### Volumes

| Volume | Purpose | Location in Container |
|--------|---------|----------------------|
| `imagetools-storage` | Uploaded images and SQLite database | `/app/storage` |
| `nginx-htpasswd` | Basic auth credentials (htpasswd file) | `/etc/nginx/htpasswd` |

## Advanced Usage

### Using HTTPS (Recommended for Production)

To add HTTPS, modify the nginx configuration:

1. Update `nginx/nginx.conf` to listen on port 443:
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # ... rest of configuration
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

2. Mount SSL certificates in docker-compose.yml:
```yaml
nginx:
  volumes:
    - ./ssl/cert.pem:/etc/nginx/ssl/cert.pem:ro
    - ./ssl/key.pem:/etc/nginx/ssl/key.pem:ro
```

3. Update port mapping:
```yaml
nginx:
  ports:
    - "80:80"
    - "443:443"
```

### Managing Users

#### Add a New User (Custom htpasswd mode)

```bash
# If using mounted directory
htpasswd htpasswd/.htpasswd newuser

# If using Docker volume, access via container
docker exec -it imagetools-nginx htpasswd /etc/nginx/htpasswd/.htpasswd newuser

# Reload nginx to apply changes
docker exec imagetools-nginx nginx -s reload
```

#### Remove a User

```bash
# If using mounted directory
htpasswd -D htpasswd/.htpasswd username

# If using Docker volume
docker exec -it imagetools-nginx htpasswd -D /etc/nginx/htpasswd/.htpasswd username
docker exec imagetools-nginx nginx -s reload
```

#### Change Password

```bash
# If using mounted directory
htpasswd htpasswd/.htpasswd username

# If using Docker volume
docker exec -it imagetools-nginx htpasswd /etc/nginx/htpasswd/.htpasswd username
docker exec imagetools-nginx nginx -s reload
```

### Backup and Restore

#### Backup

```bash
# Backup images and database
docker run --rm -v imagetools-storage:/data -v $(pwd):/backup alpine \
    tar czf /backup/imagetools-data-backup.tar.gz /data

# Backup htpasswd file
docker run --rm -v nginx-htpasswd:/data -v $(pwd):/backup alpine \
    tar czf /backup/imagetools-htpasswd-backup.tar.gz /data
```

#### Restore

```bash
# Restore images and database
docker run --rm -v imagetools-storage:/data -v $(pwd):/backup alpine \
    tar xzf /backup/imagetools-data-backup.tar.gz -C /

# Restore htpasswd file
docker run --rm -v nginx-htpasswd:/data -v $(pwd):/backup alpine \
    tar xzf /backup/imagetools-htpasswd-backup.tar.gz -C /
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Nginx only
docker-compose logs -f nginx

# ImageTools only
docker-compose logs -f imagetools

# Last 100 lines
docker-compose logs --tail=100
```

### Health Checks

```bash
# Check health endpoint (bypasses auth)
curl http://localhost/health

# Check nginx status
docker inspect imagetools-nginx --format='{{.State.Status}}'

# Check ImageTools status
docker inspect imagetools-app --format='{{.State.Health.Status}}'
```

## Troubleshooting

### Authentication Not Working

**Problem**: Can't log in / "401 Unauthorized" error

**Solutions**:
1. Verify htpasswd file exists:
```bash
docker exec imagetools-nginx ls -la /etc/nginx/htpasswd/.htpasswd
```

2. Check nginx logs:
```bash
docker-compose logs nginx | grep auth
```

3. Verify credentials in .env file (simple mode)
4. Test htpasswd file manually:
```bash
docker exec imagetools-nginx cat /etc/nginx/htpasswd/.htpasswd
```

### htpasswd File Not Being Created

**Problem**: Nginx fails to start with "No htpasswd file" error

**Solutions**:
1. Ensure `DFLT_USERNAME` and `DFLT_PASSWORD` are set in `.env`
2. Check entrypoint script permissions:
```bash
ls -la deployment/nginx/docker-entrypoint.sh
# Should show: -rwxr-xr-x
```

3. Check nginx container logs:
```bash
docker-compose logs nginx
```

### WebSocket Connection Failing

**Problem**: Real-time features not working, "WebSocket connection failed"

**Solutions**:
1. Verify nginx WebSocket configuration is correct
2. Check browser console for WebSocket errors
3. Ensure firewall allows WebSocket connections
4. Test WebSocket endpoint:
```bash
# Using wscat (install: npm install -g wscat)
wscat -c ws://localhost/ws
```

### "413 Request Entity Too Large" Error

**Problem**: Cannot upload large images

**Solutions**:
1. Increase `client_max_body_size` in nginx.conf:
```nginx
client_max_body_size 50M;  # Increase from 20M
```

2. Increase `MAX_UPLOAD_SIZE_MB` in .env:
```bash
MAX_UPLOAD_SIZE_MB=50
```

3. Restart services:
```bash
docker-compose restart
```

### Existing htpasswd File Being Overwritten

**Problem**: Custom htpasswd file is replaced on startup

**Issue**: You have BOTH a custom htpasswd file AND DFLT_USERNAME/DFLT_PASSWORD set

**Solution**: The entrypoint script will NEVER overwrite an existing htpasswd file. If your file is being overwritten, it means:
1. The file doesn't exist in the mounted location
2. The volume mount is incorrect
3. File permissions prevent reading

**Debug**:
```bash
# Check if file exists before starting
ls -la htpasswd/.htpasswd

# Check volume mounts
docker inspect imagetools-nginx | grep -A 10 Mounts

# Start with verbose logging
docker-compose up nginx
```

## Security Considerations

### Production Recommendations

1. **Use Strong Passwords**
   - Minimum 12 characters
   - Mix of uppercase, lowercase, numbers, symbols
   - Use a password manager

2. **Enable HTTPS**
   - Get free certificates from [Let's Encrypt](https://letsencrypt.org/)
   - Use [Certbot](https://certbot.eff.org/) for automatic renewal

3. **Regular Backups**
   - Backup `imagetools-storage` volume daily
   - Backup `nginx-htpasswd` volume weekly
   - Store backups in separate location

4. **Limit Exposure**
   - Don't expose to internet unless necessary
   - Use VPN or IP whitelisting
   - Consider additional firewall rules

5. **Monitor Logs**
   - Check logs regularly for failed login attempts
   - Set up log rotation
   - Consider centralized logging (ELK, Splunk, etc.)

6. **Update Regularly**
   - Keep Docker images up to date
   - Rebuild containers monthly
   ```bash
   docker-compose pull
   docker-compose up -d --build
   ```

7. **Secure Environment Variables**
   - Don't commit `.env` to version control
   - Use Docker secrets in production:
   ```yaml
   secrets:
     db_password:
       file: ./secrets/db_password.txt
   ```

8. **Rate Limiting**
   - Add rate limiting to nginx to prevent brute force:
   ```nginx
   limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
   
   location / {
       limit_req zone=login burst=10;
       # ... rest of config
   }
   ```

### Compliance Notes

- **GDPR**: Images are stored temporarily (default 7 days)
- **Data Retention**: Configure `SESSION_EXPIRY_DAYS` per your policy
- **Access Control**: Basic auth provides user authentication
- **Audit Trail**: Enable nginx access logs for compliance

## File Structure

```
deployment/
├── docker-compose.yml          # Main orchestration file
├── .env.example                # Environment variable template
├── .env                        # Your configuration (create from .env.example)
├── README.md                   # This file
├── nginx/
│   ├── nginx.conf              # Nginx reverse proxy configuration
│   └── docker-entrypoint.sh    # Entrypoint script for htpasswd generation
└── htpasswd/                   # (Optional) Custom htpasswd directory
    └── .htpasswd               # (Optional) Your custom htpasswd file
```

## Support

- **Documentation**: See main README.md in project root
- **Issues**: https://github.com/yourusername/ImageTools/issues
- **WebSocket Architecture**: See `docs/WEBSOCKET_ARCHITECTURE.md`

## License

Same as main ImageTools project.
