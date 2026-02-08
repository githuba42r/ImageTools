"""
Internal Authentication Middleware

This middleware implements defense-in-depth security by validating an internal
authentication header (X-Internal-Auth) on all incoming requests, and extracts
user authentication information from Authelia headers.

Design:
- Validates X-Internal-Auth header against configured secret (when enabled)
- Extracts Remote-User and Remote-Name headers from Authelia
- Stores user information in request.state for use by endpoints
- Bypasses validation for API endpoints (/api/v1/mobile/*, /api/v1/addon/*)
- Bypasses validation for health check endpoint (/health)
- Returns 403 Forbidden if header is missing or invalid
- Only active when REQUIRE_INTERNAL_AUTH is enabled

Security benefits:
- Protects against compromised containers on Docker network
- Protects against accidental backend port exposure
- Protects against Docker host network attacks
- Provides fail-safe against proxy misconfiguration
- Integrates with Authelia for user authentication
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class InternalAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate internal authentication header for defense-in-depth security.
    
    This middleware checks for the X-Internal-Auth header on all requests except:
    - API endpoints: /api/v1/mobile/* and /api/v1/addon/* (use token-based auth)
    - Health check: /health
    - Version info: /version
    - Static assets and frontend routes
    
    If REQUIRE_INTERNAL_AUTH is disabled, this middleware does nothing.
    """
    
    # Paths that bypass internal auth validation
    BYPASS_PATHS = [
        "/health",  # Health check endpoint
        "/version",  # Version information endpoint
    ]
    
    # Path prefixes that bypass internal auth (API endpoints with their own auth)
    BYPASS_PREFIXES = [
        "/api/v1/mobile/",  # Mobile API uses long-term secrets
        "/api/v1/addon/",   # Addon API uses OAuth tokens
    ]
    
    def __init__(self, app):
        super().__init__(app)
        
        # Log middleware initialization
        if settings.REQUIRE_INTERNAL_AUTH:
            if not settings.INTERNAL_AUTH_SECRET:
                logger.error("REQUIRE_INTERNAL_AUTH is true but INTERNAL_AUTH_SECRET is not set")
                raise ValueError("REQUIRE_INTERNAL_AUTH is true but INTERNAL_AUTH_SECRET is not set")
            
            logger.info("Internal authentication middleware enabled")
            logger.info(f"Internal auth secret configured (length: {len(settings.INTERNAL_AUTH_SECRET)} characters)")
            logger.info(f"Bypass paths: {self.BYPASS_PATHS}")
            logger.info(f"Bypass prefixes: {self.BYPASS_PREFIXES}")
        else:
            logger.info("Internal authentication middleware disabled (REQUIRE_INTERNAL_AUTH=false)")
    
    async def dispatch(self, request: Request, call_next):
        """
        Process each request and validate internal auth header if required.
        Also extracts Authelia user information from headers.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/endpoint in the chain
            
        Returns:
            Response from next middleware/endpoint, or 403 Forbidden
        """
        
        # Extract Authelia user information from headers (always, regardless of internal auth)
        remote_user = request.headers.get("Remote-User")
        remote_name = request.headers.get("Remote-Name")
        
        # Store user information in request state for endpoints to access
        request.state.remote_user = remote_user
        request.state.remote_name = remote_name
        
        # Log user information if available
        if remote_user:
            logger.debug(f"Authelia user detected: {remote_user} ({remote_name or 'no display name'})")
        
        # Skip validation if internal auth is disabled
        if not settings.REQUIRE_INTERNAL_AUTH:
            return await call_next(request)
        
        # Get the request path
        path = request.url.path
        
        # Check if path should bypass internal auth
        if self._should_bypass(path):
            logger.debug(f"Internal auth bypass for path: {path}")
            return await call_next(request)
        
        # Validate internal auth header
        if not self._validate_internal_auth(request):
            # Get client IP for logging
            client_ip = request.client.host if request.client else "unknown"
            
            # Log the security event
            header_value = request.headers.get("X-Internal-Auth", None)
            if header_value is None:
                logger.warning(f"Internal auth validation failed: Missing X-Internal-Auth header | Path: {path} | Client: {client_ip}")
            else:
                # Don't log the actual wrong value (security)
                logger.warning(f"Internal auth validation failed: Invalid X-Internal-Auth header | Path: {path} | Client: {client_ip}")
            
            logger.info("Request blocked by internal auth middleware")
            
            # Return generic 403 Forbidden (security through obscurity)
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden"}
            )
        
        # Header is valid, continue to next middleware/endpoint
        logger.debug(f"Internal auth validation succeeded for path: {path}")
        return await call_next(request)
    
    def _should_bypass(self, path: str) -> bool:
        """
        Check if the given path should bypass internal auth validation.
        
        Args:
            path: The request path to check
            
        Returns:
            True if path should bypass validation, False otherwise
        """
        # Check exact path matches
        if path in self.BYPASS_PATHS:
            return True
        
        # Check path prefixes
        for prefix in self.BYPASS_PREFIXES:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _validate_internal_auth(self, request: Request) -> bool:
        """
        Validate the X-Internal-Auth header against the configured secret.
        
        Args:
            request: The HTTP request to validate
            
        Returns:
            True if header is present and matches secret, False otherwise
        """
        # Get the header value
        header_value = request.headers.get("X-Internal-Auth")
        
        # Check if header is present
        if header_value is None:
            return False
        
        # Compare with configured secret (constant-time comparison for security)
        import secrets
        expected = settings.INTERNAL_AUTH_SECRET
        
        # Use constant-time comparison to prevent timing attacks
        return secrets.compare_digest(header_value, expected)
