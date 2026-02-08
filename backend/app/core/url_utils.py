"""
Utility functions for URL detection from request headers
"""
from fastapi import Request
from app.core.config import settings


def get_instance_url(request: Request) -> str:
    """
    Get the instance URL, auto-detecting from reverse proxy headers when possible.
    
    When deployed behind a reverse proxy (nginx, Traefik, etc.), this function
    will automatically detect the public URL from X-Forwarded-* headers.
    
    Priority order:
    1. X-Forwarded-Host + X-Forwarded-Proto headers (set by reverse proxy)
    2. Host header + scheme from request
    3. INSTANCE_URL environment variable (fallback)
    
    Args:
        request: FastAPI Request object
        
    Returns:
        str: The detected or configured instance URL (e.g., "https://yourdomain.com")
    """
    # Try to get forwarded host from reverse proxy headers
    forwarded_host = request.headers.get("x-forwarded-host")
    forwarded_proto = request.headers.get("x-forwarded-proto")
    
    if forwarded_host:
        # Use forwarded protocol if available, otherwise default to https for security
        proto = forwarded_proto if forwarded_proto else "https"
        return f"{proto}://{forwarded_host}"
    
    # Try to build from Host header if available
    host = request.headers.get("host")
    if host:
        # Use the request's URL scheme (http or https)
        scheme = request.url.scheme
        return f"{scheme}://{host}"
    
    # Fallback to configured INSTANCE_URL
    return settings.INSTANCE_URL
