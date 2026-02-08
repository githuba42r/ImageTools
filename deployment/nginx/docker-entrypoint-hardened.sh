#!/bin/sh
set -e

# nginx Entrypoint Script for Internal Authentication (Hardened Deployment)
# 
# This script processes the nginx configuration template and substitutes
# environment variables for internal authentication before starting nginx.
#
# Usage: Mount this script as /docker-entrypoint.sh in your nginx container
#
# Required environment variables:
#   - INTERNAL_AUTH_SECRET: The secret value for X-Internal-Auth header

echo "========================================="
echo "nginx Entrypoint - Internal Auth Setup"
echo "========================================="

# Validate that INTERNAL_AUTH_SECRET is set
if [ -z "$INTERNAL_AUTH_SECRET" ]; then
    echo "ERROR: INTERNAL_AUTH_SECRET environment variable is not set"
    echo "Please set INTERNAL_AUTH_SECRET in your .env file or docker-compose.yml"
    exit 1
fi

echo "✓ INTERNAL_AUTH_SECRET is configured"
echo "  Secret length: ${#INTERNAL_AUTH_SECRET} characters"

# Prepare the internal auth header directive
# This will be substituted into the nginx config template
export INTERNAL_AUTH_HEADER="proxy_set_header X-Internal-Auth \"$INTERNAL_AUTH_SECRET\";"

echo "Processing nginx configuration template..."

# Check if template file exists
if [ ! -f "/etc/nginx/templates/nginx.conf.template" ]; then
    echo "ERROR: nginx.conf.template not found at /etc/nginx/templates/nginx.conf.template"
    echo "Please mount the template file in your docker-compose.yml"
    exit 1
fi

# Substitute environment variables in the template
envsubst '${INTERNAL_AUTH_HEADER}' < /etc/nginx/templates/nginx.conf.template > /etc/nginx/conf.d/default.conf

# Verify the config was generated
if [ ! -f "/etc/nginx/conf.d/default.conf" ]; then
    echo "ERROR: Failed to generate nginx configuration"
    exit 1
fi

echo "✓ nginx configuration generated successfully"
echo "✓ Internal auth header configured"

# Test nginx configuration
nginx -t

if [ $? -ne 0 ]; then
    echo "ERROR: nginx configuration test failed"
    echo "Showing generated configuration for debugging:"
    cat /etc/nginx/conf.d/default.conf
    exit 1
fi

echo "✓ nginx configuration test passed"
echo "========================================="
echo "Starting nginx..."
echo "========================================="

# Start nginx in foreground
exec nginx -g 'daemon off;'
