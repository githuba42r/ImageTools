#!/bin/sh
set -e

# Entrypoint script for nginx with basic auth
# Handles automatic htpasswd generation from environment variables

HTPASSWD_DIR="/etc/nginx/htpasswd"
HTPASSWD_FILE="$HTPASSWD_DIR/.htpasswd"

echo "[nginx-entrypoint] Starting nginx with basic auth..."

# Create htpasswd directory if it doesn't exist
mkdir -p "$HTPASSWD_DIR"

# Check if htpasswd file already exists
if [ -f "$HTPASSWD_FILE" ]; then
    echo "[nginx-entrypoint] Found existing htpasswd file at $HTPASSWD_FILE"
    echo "[nginx-entrypoint] Will NOT overwrite existing htpasswd file"
    
    # Count number of users in existing file
    USER_COUNT=$(wc -l < "$HTPASSWD_FILE")
    echo "[nginx-entrypoint] Existing htpasswd file contains $USER_COUNT user(s)"
    
else
    echo "[nginx-entrypoint] No existing htpasswd file found"
    
    # Check if simple auth credentials are provided
    if [ -n "$DFLT_USERNAME" ] && [ -n "$DFLT_PASSWORD" ]; then
        echo "[nginx-entrypoint] Creating htpasswd file with provided credentials..."
        echo "[nginx-entrypoint] Username: $DFLT_USERNAME"
        
        # Create htpasswd file with bcrypt encryption
        htpasswd -cb "$HTPASSWD_FILE" "$DFLT_USERNAME" "$DFLT_PASSWORD"
        
        echo "[nginx-entrypoint] Successfully created htpasswd file"
        
        # Set proper permissions
        chmod 644 "$HTPASSWD_FILE"
        
    else
        echo "[nginx-entrypoint] ERROR: No htpasswd file found and no DFLT_USERNAME/DFLT_PASSWORD provided"
        echo "[nginx-entrypoint] Please either:"
        echo "[nginx-entrypoint]   1. Provide DFLT_USERNAME and DFLT_PASSWORD environment variables"
        echo "[nginx-entrypoint]   2. Mount a volume with existing htpasswd file at $HTPASSWD_DIR"
        exit 1
    fi
fi

# Verify htpasswd file is readable
if [ ! -r "$HTPASSWD_FILE" ]; then
    echo "[nginx-entrypoint] ERROR: htpasswd file exists but is not readable"
    exit 1
fi

# Set APP_NAME default if not provided
if [ -z "$APP_NAME" ]; then
    export APP_NAME="Protected Area"
    echo "[nginx-entrypoint] APP_NAME not set, using default: 'Protected Area'"
else
    echo "[nginx-entrypoint] APP_NAME: $APP_NAME"
fi

# Replace APP_NAME in nginx config
echo "[nginx-entrypoint] Configuring nginx with APP_NAME: $APP_NAME"
envsubst '${APP_NAME}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Test nginx configuration
echo "[nginx-entrypoint] Testing nginx configuration..."
nginx -t

echo "[nginx-entrypoint] Starting nginx..."
exec nginx -g 'daemon off;'
