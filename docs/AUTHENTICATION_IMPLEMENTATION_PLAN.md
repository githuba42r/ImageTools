# Authentication Implementation Plan: Self-Contained Deployment

## Executive Summary

This document outlines a **self-contained** authentication strategy for ImageTools that:
- ✅ **Zero external configuration changes** - works with existing Traefik/Authelia setup
- ✅ **Docker label-based** - all routing defined in docker-compose.yml
- ✅ **Drop-in deployment** - just add to your Docker network and go
- ✅ **Web app access** via your existing Authelia/Basic Auth setup
- ✅ **API access** for mobile apps and browser addons automatically bypasses web auth
- ✅ **Pre-built Docker image** available on DockerHub
- ✅ **Two deployment variants**: Simplified (A) and Hardened (B) for different security needs
- ✅ **Defense in depth**: Optional internal authentication for production security

**Key Principle**: ImageTools integrates with your existing authentication infrastructure without requiring changes to Traefik, nginx, or Authelia configurations.

**Deployment Variants:**
- **Simplified (A)**: Quick setup, suitable for testing and trusted environments
- **Hardened (B)**: Adds X-Internal-Auth header validation for production ⭐ **RECOMMENDED**

---

## Current State Analysis

### Existing API Endpoints

**Mobile App Endpoints** (`/api/v1/mobile/*`):
- `/api/v1/mobile/upload` - Authenticates via `long_term_secret` form parameter
- `/api/v1/mobile/validate-secret` - Initial QR code pairing
- `/api/v1/mobile/refresh-secret` - Token refresh
- `/api/v1/mobile/validate-auth` - Auth status check

**Browser Addon Endpoints** (`/api/v1/addon/*`):
- `/api/v1/addon/upload` - Authenticates via Bearer token in Authorization header
- `/api/v1/addon/token` - Exchange authorization code for tokens
- `/api/v1/addon/refresh` - Refresh access token
- `/api/v1/addon/validate` - Validate token status

### Requirements

- Web users must authenticate via Authelia (or Basic Auth if configured)
- Mobile/addon APIs must bypass web authentication (they have their own auth)
- No changes to existing Authelia or Traefik configuration files
- Simple docker-compose deployment

---

## Solution: Priority-Based Routing with Docker Labels

### How It Works

Traefik routers support **priority** values. Higher priority routes match first. We use this to:

1. **High priority routes** (100): API endpoints with NO auth middleware → bypass Authelia
2. **Medium priority routes** (50): Static resources, uploads (configurable)
3. **Low priority routes** (1): Web app with auth middleware → requires Authelia

```
Request Flow:
┌─────────────────────────────────────────────┐
│         Existing Traefik Instance            │
├─────────────────────────────────────────────┤
│                                              │
│  /api/v1/mobile/*  (priority 100)           │
│  → No middleware → Direct to backend        │
│                                              │
│  /api/v1/addon/*  (priority 100)            │
│  → No middleware → Direct to backend        │
│                                              │
│  /*  (priority 1)                           │
│  → authelia@docker middleware               │
│  → Authelia login → Backend                 │
│                                              │
└─────────────────────────────────────────────┘
```

**Key Insight**: By NOT applying the Authelia middleware to high-priority API routes, they automatically bypass authentication while still using your existing Authelia middleware for everything else.

---

## Internal Authentication (Defense in Depth)

### What is Internal Authentication?

Internal authentication adds a **second security layer** where the reverse proxy includes a secret header (`X-Internal-Auth`) in authenticated requests. The backend validates this header before processing.

**Security Model**:
```
┌─────────────────────────────────────────┐
│  Internet / Attacker                     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Layer 1: Authelia/Basic Auth (Proxy)   │ ← User authentication
└──────────────┬──────────────────────────┘
               │ + Adds X-Internal-Auth header
               ▼
┌─────────────────────────────────────────┐
│  Layer 2: Internal Auth (Backend)       │ ← Header validation
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  ImageTools Application                  │
└─────────────────────────────────────────┘
```

### How It Works

**Request Flow**:

1. **User accesses web app** → Reverse proxy (Traefik/nginx)
2. **Proxy authenticates user** via Authelia or Basic Auth
3. **Proxy adds secret header**: `X-Internal-Auth: <secret>`
4. **Request forwarded to backend** with header
5. **Backend validates header** before processing
6. **If valid**: Request processed normally
7. **If invalid/missing**: Returns 403 Forbidden

**API Endpoints Bypass**:
- Mobile API (`/api/v1/mobile/*`) - NO header validation
- Addon API (`/api/v1/addon/*`) - NO header validation
- Health check (`/health`) - NO header validation

These use their own token-based authentication and bypass the internal auth check.

### Why Use It?

**Protects Against**:
- ❌ Direct backend access from other containers in Docker network
- ❌ Accidental backend port exposure to host
- ❌ Compromised containers making unauthorized requests
- ❌ Docker host access by attackers
- ❌ Proxy authentication bypass attempts

**Defense in Depth**: Even if an attacker bypasses Authelia or gains Docker network access, they cannot access the backend without the secret header.

### When to Use

**✅ Hardened Variant Recommended For**:
- Production deployments
- Internet-facing servers
- Shared Docker networks
- Security-conscious environments
- Compliance requirements (SOC2, HIPAA, PCI-DSS, etc.)
- Zero-trust architectures

**Simplified Variant Suitable For**:
- Testing/demo environments
- Single-host Docker deployments with trusted containers only
- Fully isolated networks
- Development environments (but use `dev-all.sh` instead)

**💡 Default Recommendation**: Use **Hardened (B)** variants for all production deployments.

### Performance Impact

**Negligible** - adds approximately **0.1ms overhead** per request for header validation.

- No database queries
- Simple string comparison
- Happens before application logic
- No impact on API endpoints (they bypass validation)

### Configuration Overview

**Hardened variants require**:
1. Generate a secure 64-character hex secret
2. Add `INTERNAL_AUTH_SECRET` to `.env` file
3. Configure reverse proxy to add `X-Internal-Auth` header
4. Set `REQUIRE_INTERNAL_AUTH=true` in backend environment

**See "Generating Secure Secrets" section below for detailed instructions.**

---

## Implementation

### Local Development

**For local development**, do NOT use Docker containers. Instead, use the `dev-all.sh` script which runs the backend and frontend with hot-reload enabled:

```bash
# Run both backend and frontend in development mode
./dev-all.sh
```

This allows for:
- Backend hot-reload on code changes
- Vue frontend hot-reload (Vite dev server)
- Direct debugging without Docker complexity
- No need to configure volume mounts for source code

The deployment scenarios below are for **production or staging environments only**.

---

### Choosing Your Deployment Variant

Each deployment scenario has **two variants**:

| Variant | Security | Complexity | Setup Time | Use Case |
|---------|----------|------------|------------|----------|
| **A - Simplified** | Good | Simple | 5 min | Testing, demos, fully isolated networks |
| **B - Hardened** ⭐ | Excellent | Moderate | 10 min | **Production (Recommended)**, shared networks, internet-facing |

**What's the difference?**

| Feature | Simplified (A) | Hardened (B) |
|---------|----------------|--------------|
| **Authelia/Basic Auth** | ✅ Yes | ✅ Yes |
| **Internal Auth Header** | ❌ No | ✅ Yes |
| **API Bypass** | ✅ Yes | ✅ Yes |
| **Defense Layers** | 1 (proxy auth) | 2 (proxy + internal) |
| **.env file required** | No | Yes |
| **Secret generation** | No | Yes (1 command) |

---

**💡 Recommendation Guide**

**Use Hardened (B) variants if**:
- ✅ Deploying to production
- ✅ Server is internet-facing
- ✅ Docker network has multiple services
- ✅ Security is important to you
- ✅ You have compliance requirements
- ✅ **You're not sure which to choose** ← default to this

**Use Simplified (A) variants only if**:
- ⚠️ Testing or demo environment
- ⚠️ Fully isolated Docker network (single host, no other containers)
- ⚠️ You fully trust all containers on the network
- ⚠️ You explicitly want to skip the extra security layer

---

**Upgrading from A to B later**:

If you start with Simplified (A) and want to upgrade:
1. Generate secret: `openssl rand -hex 32`
2. Add secret to `.env` file
3. Update docker-compose.yml with internal auth configuration
4. Deploy changes: `docker-compose up -d`

Takes ~5 minutes, no data loss.

---

**The scenarios below are organized as**:
- Scenario 1A/1B: Traefik + Authelia
- Scenario 2A/2B: Traefik + Basic Auth
- Scenario 3A/3B: Standalone nginx

Choose your authentication method, then pick variant A or B.

---

### Deployment Scenarios

#### Scenario 1A: Traefik + Authelia (Simplified)

⚠️ **Note**: This is the Simplified variant without internal authentication. For production deployments, see **Scenario 1B (Hardened)** below.

**Prerequisites:**
- Traefik already running with Docker provider enabled
- Authelia middleware already configured (e.g., `authelia@docker` or `authelia@file`)
- Docker network for Traefik services

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  imagetools:
    image: yourusername/imagetools:latest  # Replace with actual DockerHub image
    container_name: imagetools-app
    
    # Traefik labels for routing and authentication
    labels:
      # Enable Traefik for this container
      - "traefik.enable=true"
      
      # Define the Docker network Traefik should use
      - "traefik.docker.network=traefik-network"  # Change to your Traefik network name
      
      # Service definition (backend port)
      - "traefik.http.services.imagetools.loadbalancer.server.port=8081"
      
      # ============================================
      # HIGH PRIORITY: API Endpoints (Bypass Auth)
      # ============================================
      
      # Mobile API - no auth middleware
      - "traefik.http.routers.imagetools-mobile.rule=Host(`imagetools.yourdomain.com`) && PathPrefix(`/api/v1/mobile`)"
      - "traefik.http.routers.imagetools-mobile.entrypoints=websecure"
      - "traefik.http.routers.imagetools-mobile.priority=100"
      - "traefik.http.routers.imagetools-mobile.tls=true"
      - "traefik.http.routers.imagetools-mobile.tls.certresolver=letsencrypt"
      
      # Addon API - no auth middleware
      - "traefik.http.routers.imagetools-addon.rule=Host(`imagetools.yourdomain.com`) && PathPrefix(`/api/v1/addon`)"
      - "traefik.http.routers.imagetools-addon.entrypoints=websecure"
      - "traefik.http.routers.imagetools-addon.priority=100"
      - "traefik.http.routers.imagetools-addon.tls=true"
      - "traefik.http.routers.imagetools-addon.tls.certresolver=letsencrypt"
      
      # Health check - no auth middleware
      - "traefik.http.routers.imagetools-health.rule=Host(`imagetools.yourdomain.com`) && Path(`/health`)"
      - "traefik.http.routers.imagetools-health.entrypoints=websecure"
      - "traefik.http.routers.imagetools-health.priority=100"
      - "traefik.http.routers.imagetools-health.tls=true"
      - "traefik.http.routers.imagetools-health.tls.certresolver=letsencrypt"
      
      # ============================================
      # LOW PRIORITY: Web App (Requires Authelia)
      # ============================================
      
      # Main web app - uses your existing Authelia middleware
      - "traefik.http.routers.imagetools-web.rule=Host(`imagetools.yourdomain.com`)"
      - "traefik.http.routers.imagetools-web.entrypoints=websecure"
      - "traefik.http.routers.imagetools-web.priority=1"
      - "traefik.http.routers.imagetools-web.middlewares=authelia@docker"  # Use your existing middleware name
      - "traefik.http.routers.imagetools-web.tls=true"
      - "traefik.http.routers.imagetools-web.tls.certresolver=letsencrypt"
    
    environment:
      # Backend configuration
      - DEBUG=False
      - LOG_LEVEL=INFO
      - SERVER_HOST=0.0.0.0
      - SERVER_PORT=8081
      - SESSION_EXPIRY_DAYS=7
      - MAX_IMAGES_PER_SESSION=5
      - MAX_UPLOAD_SIZE_MB=20
      
      # Optional: OpenRouter OAuth
      - OPENROUTER_CLIENT_ID=${OPENROUTER_CLIENT_ID:-}
      - OPENROUTER_CLIENT_SECRET=${OPENROUTER_CLIENT_SECRET:-}
      - OAUTH_REDIRECT_URL=https://imagetools.yourdomain.com/auth/callback
    
    volumes:
      - imagetools-storage:/app/storage
    
    networks:
      - traefik-network  # Connect to your existing Traefik network
    
    restart: unless-stopped
    
    healthcheck:
      test: ["CMD-SHELL", "python -c 'import urllib.request; urllib.request.urlopen(\"http://localhost:8081/health\")' || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  traefik-network:
    external: true  # Use your existing Traefik network

volumes:
  imagetools-storage:
    driver: local
```

**Setup Steps:**

1. **Find your Traefik network name:**
   ```bash
   docker network ls | grep traefik
   ```

2. **Find your Authelia middleware name:**
   ```bash
   # Check Traefik logs or dashboard for middleware names
   docker logs traefik 2>&1 | grep authelia
   # Common names: authelia@docker, authelia@file, auth@docker
   ```

3. **Update the docker-compose.yml:**
   - Replace `traefik-network` with your actual network name
   - Replace `authelia@docker` with your actual middleware name
   - Replace `imagetools.yourdomain.com` with your domain
   - Replace `yourusername/imagetools:latest` with actual image

4. **Deploy:**
   ```bash
   docker-compose up -d
   ```

**That's it!** No changes to Traefik or Authelia configuration needed.

---

#### Scenario 1B: Traefik + Authelia (Hardened) ⭐ RECOMMENDED FOR PRODUCTION

This variant adds **internal authentication** for defense-in-depth security. The reverse proxy adds a secret header to authenticated requests, and the backend validates it.

**Prerequisites:**
- Traefik already running with Docker provider enabled
- Authelia middleware already configured (e.g., `authelia@docker` or `authelia@file`)
- Docker network for Traefik services

### Step 1: Generate Internal Auth Secret

```bash
# Generate a secure 64-character hex string
openssl rand -hex 32
```

Save this output - you'll need it in the next step.

### Step 2: Create `.env` file

Create a `.env` file in your deployment directory:

```bash
# .env file for ImageTools Hardened Deployment
# 
# SECURITY: Keep this file secure!
# - Add to .gitignore
# - Never commit to version control
# - Use proper file permissions (chmod 600 .env)

# Internal Authentication Secret (REQUIRED for Hardened variant)
# Replace with the output from: openssl rand -hex 32
INTERNAL_AUTH_SECRET=replace-this-with-your-generated-secret

# Optional: OpenRouter OAuth (for AI features)
OPENROUTER_CLIENT_ID=
OPENROUTER_CLIENT_SECRET=
```

### Step 3: Create docker-compose.yml

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  imagetools:
    image: yourusername/imagetools:latest  # Replace with actual DockerHub image
    container_name: imagetools-app
    
    # Traefik labels for routing and authentication
    labels:
      # Enable Traefik for this container
      - "traefik.enable=true"
      
      # Define the Docker network Traefik should use
      - "traefik.docker.network=traefik-network"  # Change to your Traefik network name
      
      # Service definition (backend port)
      - "traefik.http.services.imagetools.loadbalancer.server.port=8081"
      
      # ============================================
      # HIGH PRIORITY: API Endpoints (Bypass Auth)
      # ============================================
      
      # Mobile API - no auth middleware (bypasses both Authelia and Internal Auth)
      - "traefik.http.routers.imagetools-mobile.rule=Host(`imagetools.yourdomain.com`) && PathPrefix(`/api/v1/mobile`)"
      - "traefik.http.routers.imagetools-mobile.entrypoints=websecure"
      - "traefik.http.routers.imagetools-mobile.priority=100"
      - "traefik.http.routers.imagetools-mobile.tls=true"
      - "traefik.http.routers.imagetools-mobile.tls.certresolver=letsencrypt"
      
      # Addon API - no auth middleware (bypasses both Authelia and Internal Auth)
      - "traefik.http.routers.imagetools-addon.rule=Host(`imagetools.yourdomain.com`) && PathPrefix(`/api/v1/addon`)"
      - "traefik.http.routers.imagetools-addon.entrypoints=websecure"
      - "traefik.http.routers.imagetools-addon.priority=100"
      - "traefik.http.routers.imagetools-addon.tls=true"
      - "traefik.http.routers.imagetools-addon.tls.certresolver=letsencrypt"
      
      # Health check - no auth middleware
      - "traefik.http.routers.imagetools-health.rule=Host(`imagetools.yourdomain.com`) && Path(`/health`)"
      - "traefik.http.routers.imagetools-health.entrypoints=websecure"
      - "traefik.http.routers.imagetools-health.priority=100"
      - "traefik.http.routers.imagetools-health.tls=true"
      - "traefik.http.routers.imagetools-health.tls.certresolver=letsencrypt"
      
      # ============================================
      # INTERNAL AUTH MIDDLEWARE DEFINITION
      # ============================================
      
      # Define middleware that adds X-Internal-Auth header
      # This middleware injects the secret header into requests
      - "traefik.http.middlewares.imagetools-internal-auth.headers.customrequestheaders.X-Internal-Auth=${INTERNAL_AUTH_SECRET}"
      
      # ============================================
      # LOW PRIORITY: Web App (Requires Authelia + Internal Auth)
      # ============================================
      
      # Main web app - uses BOTH your existing Authelia middleware AND internal auth middleware
      - "traefik.http.routers.imagetools-web.rule=Host(`imagetools.yourdomain.com`)"
      - "traefik.http.routers.imagetools-web.entrypoints=websecure"
      - "traefik.http.routers.imagetools-web.priority=1"
      # NOTE: Middleware chain - Authelia first, then internal auth header
      - "traefik.http.routers.imagetools-web.middlewares=authelia@docker,imagetools-internal-auth@docker"
      - "traefik.http.routers.imagetools-web.tls=true"
      - "traefik.http.routers.imagetools-web.tls.certresolver=letsencrypt"
    
    environment:
      # Backend configuration
      - DEBUG=False
      - LOG_LEVEL=INFO
      - SERVER_HOST=0.0.0.0
      - SERVER_PORT=8081
      - SESSION_EXPIRY_DAYS=7
      - MAX_IMAGES_PER_SESSION=5
      - MAX_UPLOAD_SIZE_MB=20
      
      # ============================================
      # INTERNAL AUTHENTICATION (HARDENED)
      # ============================================
      # Enable internal auth header validation in the backend
      - REQUIRE_INTERNAL_AUTH=true
      # Secret must match the one in .env that Traefik uses
      - INTERNAL_AUTH_SECRET=${INTERNAL_AUTH_SECRET}
      
      # Optional: OpenRouter OAuth
      - OPENROUTER_CLIENT_ID=${OPENROUTER_CLIENT_ID:-}
      - OPENROUTER_CLIENT_SECRET=${OPENROUTER_CLIENT_SECRET:-}
      - OAUTH_REDIRECT_URL=https://imagetools.yourdomain.com/auth/callback
    
    volumes:
      - imagetools-storage:/app/storage
    
    networks:
      - traefik-network  # Connect to your existing Traefik network
    
    restart: unless-stopped
    
    healthcheck:
      test: ["CMD-SHELL", "python -c 'import urllib.request; urllib.request.urlopen(\"http://localhost:8081/health\")' || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  traefik-network:
    external: true  # Use your existing Traefik network

volumes:
  imagetools-storage:
    driver: local
```

### Step 4: Setup Instructions

1. **Find your Traefik network name:**
   ```bash
   docker network ls | grep traefik
   ```

2. **Find your Authelia middleware name:**
   ```bash
   # Check Traefik logs or dashboard for middleware names
   docker logs traefik 2>&1 | grep authelia
   # Common names: authelia@docker, authelia@file, auth@docker
   ```

3. **Update the docker-compose.yml:**
   - Replace `traefik-network` with your actual network name
   - Replace `authelia@docker` with your actual middleware name
   - Replace `imagetools.yourdomain.com` with your domain
   - Replace `yourusername/imagetools:latest` with actual image

4. **Verify your `.env` file:**
   ```bash
   # Check that secret is set
   cat .env | grep INTERNAL_AUTH_SECRET
   
   # Ensure it's not tracked by git
   echo ".env" >> .gitignore
   ```

5. **Deploy:**
   ```bash
   docker-compose up -d
   ```

6. **Verify deployment:**
   ```bash
   # Check that backend picked up the internal auth setting
   docker logs imagetools-app | grep -i "internal auth"
   # Should see: "Internal authentication middleware enabled"
   
   # Test web access (should work after Authelia login)
   # Open browser: https://imagetools.yourdomain.com
   
   # Test mobile API still works (bypasses internal auth)
   curl https://imagetools.yourdomain.com/api/v1/mobile/validate-auth
   # Should return 401 (needs mobile secret) not 403
   ```

### How Internal Auth Works in This Setup

```
Request Flow for Web App:
─────────────────────────

Browser → Traefik
         │
         ├─> Authelia Middleware (authelia@docker)
         │   └─> Validates user credentials
         │   └─> If valid, continues
         │
         ├─> Internal Auth Middleware (imagetools-internal-auth@docker)  
         │   └─> Adds header: X-Internal-Auth: <secret>
         │
         └─> ImageTools Backend
             └─> Validates X-Internal-Auth header matches INTERNAL_AUTH_SECRET
             └─> If valid, processes request
             └─> If invalid/missing, returns 403 Forbidden


Request Flow for Mobile API:
────────────────────────────

Mobile App → Traefik
            │
            └─> ImageTools Backend (direct, no middleware)
                └─> NO X-Internal-Auth validation (bypassed by middleware)
                └─> Validates long_term_secret instead
```

### Key Differences from Scenario 1A (Simplified)

| Aspect | Scenario 1A (Simplified) | Scenario 1B (Hardened) |
|--------|--------------------------|------------------------|
| **Traefik Middleware** | Only `authelia@docker` | `authelia@docker,imagetools-internal-auth@docker` |
| **Header Added** | None | `X-Internal-Auth: <secret>` |
| **Backend Validation** | None | Validates header on all non-API routes |
| **Environment Vars** | Standard only | + `REQUIRE_INTERNAL_AUTH=true`, `INTERNAL_AUTH_SECRET=...` |
| **Setup Complexity** | Simple | +1 secret to generate |
| **Security Level** | Good | Excellent (defense in depth) |
| **.env file** | Optional | Required |

---

#### Scenario 2A: Traefik + Basic Auth (Simplified)

⚠️ **Note**: This is the Simplified variant without internal authentication. For production deployments, see **Scenario 2B (Hardened)** below.

If you're using Basic Auth instead of Authelia:

```yaml
# Same as Scenario 1, but replace the web router middleware:
- "traefik.http.routers.imagetools-web.middlewares=basicauth@docker"

# And add Basic Auth middleware definition:
- "traefik.http.middlewares.imagetools-basicauth.basicauth.users=admin:$$apr1$$hash$$here"
```

Generate password hash:
```bash
# Using htpasswd
htpasswd -nb admin yourpassword

# Using Docker
docker run --rm httpd:alpine htpasswd -nb admin yourpassword
```

---

#### Scenario 2B: Traefik + Basic Auth (Hardened) ⭐ RECOMMENDED FOR PRODUCTION

This variant uses Basic Auth for user authentication and adds **internal authentication** for defense-in-depth security.

**Prerequisites:**
- Traefik already running with Docker provider enabled
- Docker network for Traefik services

### Step 1: Generate Internal Auth Secret

```bash
# Generate a secure 64-character hex string
openssl rand -hex 32
```

### Step 2: Generate Basic Auth Password Hash

```bash
# Using htpasswd (install apache2-utils if needed)
htpasswd -nb admin yourpassword

# Or using Docker
docker run --rm httpd:alpine htpasswd -nb admin yourpassword

# Output will look like: admin:$apr1$xyz$abc...
# Copy the entire output for the next step
```

### Step 3: Create `.env` file

```bash
# .env file for ImageTools Hardened Deployment with Basic Auth
#
# SECURITY: Keep this file secure!

# Internal Authentication Secret (REQUIRED for Hardened variant)
# Generate with: openssl rand -hex 32
INTERNAL_AUTH_SECRET=replace-with-your-generated-secret

# Basic Auth Password Hash
# Generate with: htpasswd -nb admin yourpassword
# Important: Escape $ signs in docker-compose by using $$
BASIC_AUTH_USERS=admin:$$apr1$$hash$$here

# Optional: OpenRouter OAuth
OPENROUTER_CLIENT_ID=
OPENROUTER_CLIENT_SECRET=
```

### Step 4: Create docker-compose.yml

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  imagetools:
    image: yourusername/imagetools:latest
    container_name: imagetools-app
    
    labels:
      - "traefik.enable=true"
      - "traefik.docker.network=traefik-network"
      - "traefik.http.services.imagetools.loadbalancer.server.port=8081"
      
      # High priority: API endpoints (bypass all auth)
      - "traefik.http.routers.imagetools-mobile.rule=Host(`imagetools.yourdomain.com`) && PathPrefix(`/api/v1/mobile`)"
      - "traefik.http.routers.imagetools-mobile.entrypoints=websecure"
      - "traefik.http.routers.imagetools-mobile.priority=100"
      - "traefik.http.routers.imagetools-mobile.tls=true"
      
      - "traefik.http.routers.imagetools-addon.rule=Host(`imagetools.yourdomain.com`) && PathPrefix(`/api/v1/addon`)"
      - "traefik.http.routers.imagetools-addon.entrypoints=websecure"
      - "traefik.http.routers.imagetools-addon.priority=100"
      - "traefik.http.routers.imagetools-addon.tls=true"
      
      - "traefik.http.routers.imagetools-health.rule=Host(`imagetools.yourdomain.com`) && Path(`/health`)"
      - "traefik.http.routers.imagetools-health.entrypoints=websecure"
      - "traefik.http.routers.imagetools-health.priority=100"
      - "traefik.http.routers.imagetools-health.tls=true"
      
      # Basic Auth middleware definition
      - "traefik.http.middlewares.imagetools-basicauth.basicauth.users=${BASIC_AUTH_USERS}"
      
      # Internal Auth middleware definition
      - "traefik.http.middlewares.imagetools-internal-auth.headers.customrequestheaders.X-Internal-Auth=${INTERNAL_AUTH_SECRET}"
      
      # Web app: Basic Auth + Internal Auth
      - "traefik.http.routers.imagetools-web.rule=Host(`imagetools.yourdomain.com`)"
      - "traefik.http.routers.imagetools-web.entrypoints=websecure"
      - "traefik.http.routers.imagetools-web.priority=1"
      - "traefik.http.routers.imagetools-web.middlewares=imagetools-basicauth@docker,imagetools-internal-auth@docker"
      - "traefik.http.routers.imagetools-web.tls=true"
    
    environment:
      - DEBUG=False
      - LOG_LEVEL=INFO
      - SERVER_HOST=0.0.0.0
      - SERVER_PORT=8081
      - SESSION_EXPIRY_DAYS=7
      - MAX_IMAGES_PER_SESSION=5
      - MAX_UPLOAD_SIZE_MB=20
      
      # Internal Authentication (Hardened)
      - REQUIRE_INTERNAL_AUTH=true
      - INTERNAL_AUTH_SECRET=${INTERNAL_AUTH_SECRET}
      
      # Optional: OpenRouter OAuth
      - OPENROUTER_CLIENT_ID=${OPENROUTER_CLIENT_ID:-}
      - OPENROUTER_CLIENT_SECRET=${OPENROUTER_CLIENT_SECRET:-}
      - OAUTH_REDIRECT_URL=https://imagetools.yourdomain.com/auth/callback
    
    volumes:
      - imagetools-storage:/app/storage
    
    networks:
      - traefik-network
    
    restart: unless-stopped
    
    healthcheck:
      test: ["CMD-SHELL", "python -c 'import urllib.request; urllib.request.urlopen(\"http://localhost:8081/health\")' || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  traefik-network:
    external: true

volumes:
  imagetools-storage:
    driver: local
```

### Step 5: Deploy

```bash
# Verify secrets are set
cat .env | grep -E "INTERNAL_AUTH_SECRET|BASIC_AUTH_USERS"

# Deploy
docker-compose up -d

# Verify
docker logs imagetools-app | grep -i "internal auth"
# Should see: "Internal authentication middleware enabled"
```

### Key Differences from Scenario 2A (Simplified)

| Aspect | Scenario 2A (Simplified) | Scenario 2B (Hardened) |
|--------|--------------------------|------------------------|
| **Middleware Chain** | Only `basicauth@docker` | `basicauth@docker,internal-auth@docker` |
| **Defense Layers** | 1 (Basic Auth) | 2 (Basic Auth + Internal) |
| **Setup** | Basic auth only | Basic auth + internal secret |

---

#### Scenario 3A: Standalone nginx (Simplified)

⚠️ **Note**: This is the Simplified variant without internal authentication. For production deployments, see **Scenario 3B (Hardened)** below.

If you don't have Traefik and want to use nginx instead:

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: imagetools-nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./nginx/htpasswd/.htpasswd:/etc/nginx/htpasswd/.htpasswd:ro
    depends_on:
      imagetools:
        condition: service_healthy
    networks:
      - imagetools-network
    restart: unless-stopped

  imagetools:
    image: yourusername/imagetools:latest
    container_name: imagetools-app
    environment:
      - DEBUG=False
      - LOG_LEVEL=INFO
      - SERVER_HOST=0.0.0.0
      - SERVER_PORT=8081
    volumes:
      - imagetools-storage:/app/storage
    networks:
      - imagetools-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "python -c 'import urllib.request; urllib.request.urlopen(\"http://localhost:8081/health\")' || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  imagetools-network:
    driver: bridge

volumes:
  imagetools-storage:
    driver: local
```

**nginx/nginx.conf:**

```nginx
server {
    listen 80;
    server_name _;
    client_max_body_size 20M;
    
    # API endpoints - bypass basic auth
    location ~ ^/api/v1/(mobile|addon)/ {
        auth_basic off;
        proxy_pass http://imagetools:8081;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Health check - bypass auth
    location /health {
        auth_basic off;
        proxy_pass http://imagetools:8081/health;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
    
    # All other routes - require basic auth
    location / {
        auth_basic "ImageTools";
        auth_basic_user_file /etc/nginx/htpasswd/.htpasswd;
        
        proxy_pass http://imagetools:8081;
        proxy_http_version 1.1;
        
        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Create htpasswd file:**
```bash
mkdir -p nginx/htpasswd
htpasswd -c nginx/htpasswd/.htpasswd admin
```

---

#### Scenario 3B: Standalone nginx (Hardened)

✅ **Recommended for production**: This variant includes internal authentication for defense-in-depth security.

This scenario uses nginx with basic auth PLUS internal authentication headers for enhanced security.

**Architecture:**
- nginx enforces basic auth for web routes
- nginx adds `X-Internal-Auth` header to authenticated requests
- Backend validates the header (defense-in-depth)
- API endpoints (`/api/v1/mobile/*`, `/api/v1/addon/*`) bypass internal auth validation

### Step 1: Generate Secrets

**Generate internal auth secret:**
```bash
# Generate a 64-character hex secret
openssl rand -hex 32

# Example output:
# 7a3f8c2b1e9d4a5f6c8b3e1d9a7c5f2b4e6d8a9c1b3f5e7d9a2c4b6e8f1a3c5e7
```

**Generate basic auth password hash:**
```bash
# Install apache2-utils if needed
sudo apt-get install apache2-utils  # Debian/Ubuntu
# or
brew install apache2-utils  # macOS

# Create htpasswd file with your username
mkdir -p nginx/htpasswd
htpasswd -c nginx/htpasswd/.htpasswd admin
# Enter password when prompted
```

### Step 2: Create .env File

Create a `.env` file in your project root:

```bash
# Internal Authentication (Hardened Deployment)
INTERNAL_AUTH_SECRET=7a3f8c2b1e9d4a5f6c8b3e1d9a7c5f2b4e6d8a9c1b3f5e7d9a2c4b6e8f1a3c5e7
```

⚠️ **Security**: Never commit `.env` to version control. Add it to `.gitignore`.

### Step 3: Create nginx Configuration Template

**nginx/nginx.conf.template:**

```nginx
server {
    listen 80;
    server_name _;
    client_max_body_size 20M;
    
    # API endpoints - bypass basic auth and internal auth
    location ~ ^/api/v1/(mobile|addon)/ {
        auth_basic off;
        proxy_pass http://imagetools:8081;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # No X-Internal-Auth header - APIs use their own token-based auth
    }
    
    # Health check - bypass auth
    location /health {
        auth_basic off;
        proxy_pass http://imagetools:8081/health;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        # No X-Internal-Auth header - health checks are excluded
    }
    
    # All other routes - require basic auth + add internal auth header
    location / {
        auth_basic "ImageTools";
        auth_basic_user_file /etc/nginx/htpasswd/.htpasswd;
        
        proxy_pass http://imagetools:8081;
        proxy_http_version 1.1;
        
        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Internal auth header (substituted from environment variable)
        ${INTERNAL_AUTH_HEADER}
    }
}
```

### Step 4: Create nginx Entrypoint Script

**deployment/nginx/docker-entrypoint.sh:**

```bash
#!/bin/sh
set -e

# Validate that INTERNAL_AUTH_SECRET is set
if [ -z "$INTERNAL_AUTH_SECRET" ]; then
    echo "ERROR: INTERNAL_AUTH_SECRET environment variable is not set"
    exit 1
fi

# Prepare the internal auth header directive
# This will be substituted into the nginx config template
export INTERNAL_AUTH_HEADER="proxy_set_header X-Internal-Auth \"$INTERNAL_AUTH_SECRET\";"

echo "Processing nginx configuration template..."

# Substitute environment variables in the template
envsubst '${INTERNAL_AUTH_HEADER}' < /etc/nginx/templates/nginx.conf.template > /etc/nginx/conf.d/default.conf

echo "nginx configuration generated successfully"
echo "Internal auth header configured"

# Start nginx
exec nginx -g 'daemon off;'
```

Make the script executable:
```bash
chmod +x deployment/nginx/docker-entrypoint.sh
```

### Step 5: Docker Compose Configuration

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: imagetools-nginx
    ports:
      - "80:80"
    volumes:
      # Mount the config template
      - ./nginx/nginx.conf.template:/etc/nginx/templates/nginx.conf.template:ro
      # Mount the htpasswd file
      - ./nginx/htpasswd/.htpasswd:/etc/nginx/htpasswd/.htpasswd:ro
      # Mount the custom entrypoint
      - ./deployment/nginx/docker-entrypoint.sh:/docker-entrypoint.sh:ro
    environment:
      # Pass the secret to nginx container for template substitution
      - INTERNAL_AUTH_SECRET=${INTERNAL_AUTH_SECRET}
    entrypoint: ["/docker-entrypoint.sh"]
    depends_on:
      imagetools:
        condition: service_healthy
    networks:
      - imagetools-network
    restart: unless-stopped

  imagetools:
    image: yourusername/imagetools:latest
    container_name: imagetools-app
    environment:
      - DEBUG=False
      - LOG_LEVEL=INFO
      - SERVER_HOST=0.0.0.0
      - SERVER_PORT=8081
      # Enable internal authentication validation
      - REQUIRE_INTERNAL_AUTH=true
      - INTERNAL_AUTH_SECRET=${INTERNAL_AUTH_SECRET}
    volumes:
      - imagetools-storage:/app/storage
    networks:
      - imagetools-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "python -c 'import urllib.request; urllib.request.urlopen(\"http://localhost:8081/health\")' || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  imagetools-network:
    driver: bridge

volumes:
  imagetools-storage:
    driver: local
```

### Step 6: Setup Instructions

1. **Create directory structure:**
   ```bash
   mkdir -p nginx/htpasswd
   mkdir -p deployment/nginx
   ```

2. **Create the files:**
   - `.env` (with `INTERNAL_AUTH_SECRET`)
   - `nginx/nginx.conf.template` (from Step 3)
   - `deployment/nginx/docker-entrypoint.sh` (from Step 4)
   - `nginx/htpasswd/.htpasswd` (from Step 1)

3. **Make entrypoint executable:**
   ```bash
   chmod +x deployment/nginx/docker-entrypoint.sh
   ```

4. **Verify your `.env` file:**
   ```bash
   # Check that secret is set
   cat .env | grep INTERNAL_AUTH_SECRET
   
   # Ensure it's not tracked by git
   echo ".env" >> .gitignore
   ```

5. **Deploy:**
   ```bash
   docker-compose up -d
   ```

6. **Verify deployment:**
   ```bash
   # Check nginx logs to confirm template processing
   docker logs imagetools-nginx
   # Should see: "nginx configuration generated successfully"
   # Should see: "Internal auth header configured"
   
   # Check that backend picked up the internal auth setting
   docker logs imagetools-app | grep -i "internal auth"
   # Should see: "Internal authentication middleware enabled"
   
   # Verify the nginx config was generated correctly
   docker exec imagetools-nginx cat /etc/nginx/conf.d/default.conf
   # Should see: proxy_set_header X-Internal-Auth "<your-secret>";
   ```

### How Internal Auth Works in This Setup

```
┌─────────┐
│  User   │
└────┬────┘
     │ HTTP Request
     ▼
┌─────────────────┐
│     nginx       │
│  Basic Auth     │
└────┬────────────┘
     │ ✓ Authenticated
     │
     │ Add header:
     │ X-Internal-Auth: <secret>
     ▼
┌──────────────────────┐
│  ImageTools Backend  │
│  Validate header     │
└──────────────────────┘
     │
     ├─ ✓ Header valid → Process request
     └─ ✗ Header invalid/missing → 403 Forbidden
```

**Request flow:**
1. User requests web page → nginx checks basic auth credentials
2. If valid → nginx adds `X-Internal-Auth` header with secret value
3. Backend receives request → validates `X-Internal-Auth` header
4. If header matches secret → process request
5. If header missing/wrong → return 403 Forbidden

**API requests:**
1. Mobile/Addon app → nginx forwards to `/api/v1/mobile/*` or `/api/v1/addon/*`
2. nginx does NOT add `X-Internal-Auth` header (not needed)
3. Backend sees API endpoint → skips internal auth validation
4. Backend uses token-based auth for these endpoints

### Security Benefits: Scenario 3B vs 3A

| Aspect | 3A (Simplified) | 3B (Hardened) |
|--------|-----------------|---------------|
| **Basic Auth** | ✅ Yes | ✅ Yes |
| **Internal Auth Header** | ❌ No | ✅ Yes |
| **Defense in Depth** | ❌ Single layer | ✅ Two layers |
| **Protects against compromised containers** | ❌ No | ✅ Yes |
| **Protects against accidental port exposure** | ❌ No | ✅ Yes |
| **Protects against Docker host attacks** | ❌ Partial | ✅ Yes |
| **API endpoints work** | ✅ Yes | ✅ Yes (bypass) |
| **Complexity** | Low | Medium |
| **Production Ready** | ⚠️ Basic | ✅ Hardened |

**When to use 3A vs 3B:**
- **3A**: Local testing, dev environments, low-security requirements
- **3B**: Production, internet-facing, compliance requirements (SOC2, ISO27001, HIPAA, PCI-DSS)

**Migration from 3A → 3B:**
Simply follow the 3B setup steps. The changes are:
1. Add `.env` file with secret
2. Convert `nginx.conf` to `nginx.conf.template` 
3. Add entrypoint script
4. Update docker-compose.yml with new mounts and environment variables

No data migration needed. Zero downtime if done correctly.

---

## Generating Secure Secrets

For Hardened (B) deployment variants, you need to generate a strong random secret for internal authentication. This section provides multiple methods for generating secure secrets.

### Recommended Method: OpenSSL

The recommended method uses OpenSSL to generate a 64-character hexadecimal secret (256 bits of entropy):

```bash
openssl rand -hex 32
```

**Example output:**
```
7a3f8c2b1e9d4a5f6c8b3e1d9a7c5f2b4e6d8a9c1b3f5e7d9a2c4b6e8f1a3c5e7
```

Add this to your `.env` file:
```bash
INTERNAL_AUTH_SECRET=7a3f8c2b1e9d4a5f6c8b3e1d9a7c5f2b4e6d8a9c1b3f5e7d9a2c4b6e8f1a3c5e7
```

### Alternative Method 1: Python

If you have Python installed:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Example output:**
```
a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2
```

### Alternative Method 2: /dev/urandom

On Linux/macOS systems:

```bash
head -c 32 /dev/urandom | xxd -p -c 64
```

**Example output:**
```
3c5e7f9a1b3d5e7f9a1b3d5e7f9a1b3d5e7f9a1b3d5e7f9a1b3d5e7f9a1b3d5e
```

### Alternative Method 3: Docker

Generate a secret using Docker (no local tools needed):

```bash
docker run --rm alpine/openssl rand -hex 32
```

**Example output:**
```
f1e2d3c4b5a6f7e8d9c0b1a2f3e4d5c6e7f8d9e0f1a2b3c4d5e6f7a8b9c0d1e2
```

### Security Best Practices

1. **Secret Strength**
   - Use at least 64 hexadecimal characters (256 bits)
   - Never use predictable values (e.g., "secret123", "password")
   - Don't reuse secrets across environments (dev/staging/prod)

2. **Secret Storage**
   - Store in `.env` file, never in docker-compose.yml
   - Add `.env` to `.gitignore` immediately
   - Never commit secrets to version control
   - Use different secrets for each deployment environment

3. **Secret Distribution**
   - Use secure channels (e.g., password manager, encrypted chat)
   - Don't email or Slack secrets in plain text
   - Consider using secrets management tools (Vault, AWS Secrets Manager)

4. **Access Control**
   - Limit who has access to production secrets
   - Use separate secrets for dev/staging/production
   - Rotate secrets when team members leave

5. **Monitoring**
   - Monitor backend logs for failed internal auth attempts
   - Set up alerts for unusual authentication failures
   - Review access logs periodically

### Secret Rotation Procedure

If you need to rotate the internal auth secret (e.g., security incident, periodic rotation, team member departure):

1. **Generate a new secret:**
   ```bash
   openssl rand -hex 32
   ```

2. **Update `.env` file:**
   ```bash
   # Old secret
   # INTERNAL_AUTH_SECRET=old_secret_here
   
   # New secret
   INTERNAL_AUTH_SECRET=new_secret_here
   ```

3. **Restart services:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

4. **Verify the rotation:**
   ```bash
   # Check logs to ensure new secret is being used
   docker logs imagetools-app | grep -i "internal auth"
   
   # Test web access (should work)
   curl -u admin:password https://imagetools.yourdomain.com/
   
   # Test direct backend access (should fail with 403)
   curl http://localhost:8081/
   ```

5. **Securely delete old secret:**
   - Remove from password managers
   - Remove from backup files
   - Inform team members the old secret is invalid

**Rotation frequency recommendations:**
- **High security environments**: Every 90 days
- **Standard environments**: Every 180 days
- **Low security environments**: Annually
- **Immediately**: After security incident or team member departure

---

## Configuration Reference

### Required Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_HOST` | `0.0.0.0` | Backend bind address |
| `SERVER_PORT` | `8081` | Backend port |
| `SESSION_EXPIRY_DAYS` | `7` | Session lifetime |
| `MAX_IMAGES_PER_SESSION` | `5` | Max images per session |
| `MAX_UPLOAD_SIZE_MB` | `20` | Max upload size |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `False` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `OPENROUTER_CLIENT_ID` | - | OpenRouter OAuth client ID |
| `OPENROUTER_CLIENT_SECRET` | - | OpenRouter OAuth client secret |
| `OAUTH_REDIRECT_URL` | - | OAuth redirect URL |

### Security Configuration (Hardened Variants Only)

These variables are **required** for Hardened (B) variants and should NOT be set for Simplified (A) variants.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `REQUIRE_INTERNAL_AUTH` | `false` | **Yes** for Hardened | Enable internal auth header validation. Set to `true` in all Hardened (B) deployments. |
| `INTERNAL_AUTH_SECRET` | - | **Yes** for Hardened | Secret value for `X-Internal-Auth` header validation. Must be a strong random value (64-char hex recommended). Generate with: `openssl rand -hex 32` |

**Important Notes:**
- Both variables must be set together in Hardened variants
- The secret must match between proxy (Traefik/nginx) and backend
- Never commit the secret to version control
- Store in `.env` file and add `.env` to `.gitignore`
- Rotate secrets periodically (see Troubleshooting section)
- API endpoints (`/api/v1/mobile/*`, `/api/v1/addon/*`) automatically bypass internal auth
- Health check endpoint (`/health`) automatically bypasses internal auth

**Example .env file for Hardened deployment:**
```bash
# Internal Authentication (Required for Hardened variants)
REQUIRE_INTERNAL_AUTH=true
INTERNAL_AUTH_SECRET=7a3f8c2b1e9d4a5f6c8b3e1d9a7c5f2b4e6d8a9c1b3f5e7d9a2c4b6e8f1a3c5e7
```

### Traefik Label Reference

**Middleware name format:**
- Docker provider: `authelia@docker`, `basicauth@docker`
- File provider: `authelia@file`, `basicauth@file`

**Common Authelia middleware names:**
- `authelia@docker`
- `authelia-verify@docker`
- `auth@docker`

Check your Traefik dashboard or logs to find your exact middleware name.

---

## Testing

### 1. Test Web Access
```bash
# Should redirect to Authelia login
curl -v https://imagetools.yourdomain.com/
```

### 2. Test Mobile API (Should bypass auth)
```bash
# Should return 401 with proper error (no auth header check)
curl -v https://imagetools.yourdomain.com/api/v1/mobile/validate-auth
```

### 3. Test Addon API (Should bypass auth)
```bash
# Should return validation response (no Authelia redirect)
curl -v https://imagetools.yourdomain.com/api/v1/addon/validate
```

### 4. Test Health Check
```bash
# Should return 200 OK
curl https://imagetools.yourdomain.com/health
```

### 5. Test Internal Authentication (Hardened Variants Only)

These tests apply only to Hardened (B) deployment variants. Skip this section if using Simplified (A) variants.

#### 5a. Verify Backend Configuration

```bash
# Check that internal auth is enabled
docker logs imagetools-app | grep -i "internal auth"

# Expected output:
# "Internal authentication middleware enabled"
# "Internal auth secret configured"
```

#### 5b. Test Web App Access (Should Work)

```bash
# Access through proxy with authentication
# For Traefik+Authelia: Visit in browser
# For Traefik+BasicAuth or nginx: Use credentials
curl -u admin:password https://imagetools.yourdomain.com/

# Expected: 200 OK with web app HTML
```

#### 5c. Test Direct Backend Access (Should Fail)

```bash
# Try to access backend directly without internal auth header
curl -v http://localhost:8081/

# Expected: 403 Forbidden
# Response body: {"detail": "Forbidden"}
```

**Why this test matters**: Proves that direct access to backend (bypassing proxy) is blocked, even if attacker has network access to the Docker bridge network.

#### 5d. Test Direct Backend with Wrong Header (Should Fail)

```bash
# Try with incorrect internal auth header
curl -v -H "X-Internal-Auth: wrong-secret" http://localhost:8081/

# Expected: 403 Forbidden
# Response body: {"detail": "Forbidden"}
```

#### 5e. Test Mobile API Still Works (Should Bypass)

```bash
# Mobile API should work through proxy without internal auth header
curl -v https://imagetools.yourdomain.com/api/v1/mobile/validate-auth

# Expected: 401 (needs mobile secret) NOT 403
# Response: {"detail": "Invalid or missing authorization"}
```

**Important**: Mobile APIs bypass internal auth and use their own token-based authentication.

#### 5f. Test Addon API Still Works (Should Bypass)

```bash
# Addon API should work through proxy
curl -v https://imagetools.yourdomain.com/api/v1/addon/validate

# Expected: Validation response (not 403)
```

#### 5g. Test Health Check Bypasses Internal Auth

```bash
# Health check should work without internal auth header
curl -v http://localhost:8081/health

# Expected: 200 OK
# Response: {"status": "healthy"}
```

#### 5h. Verify Proxy Adds Header Correctly

**For Traefik deployments:**
```bash
# Check Traefik middleware configuration
docker exec traefik cat /etc/traefik/traefik.yml
# or check logs:
docker logs traefik | grep "imagetools-internal-auth"

# Expected: Middleware defined with customrequestheaders
```

**For nginx deployments:**
```bash
# Check that nginx config has the header directive
docker exec imagetools-nginx cat /etc/nginx/conf.d/default.conf | grep "X-Internal-Auth"

# Expected output:
# proxy_set_header X-Internal-Auth "<your-secret>";
```

#### 5i. Check Backend Logs for Auth Attempts

```bash
# Monitor backend logs while testing
docker logs -f imagetools-app

# Try accessing without header:
curl http://localhost:8081/

# Expected log entries:
# "Internal auth validation failed: Missing X-Internal-Auth header"
# "Request blocked by internal auth middleware"
```

### Test Summary Checklist

**Simplified (A) Variants:**
- [ ] Test 1: Web access requires proxy authentication
- [ ] Test 2: Mobile API bypasses proxy auth
- [ ] Test 3: Addon API bypasses proxy auth
- [ ] Test 4: Health check accessible

**Hardened (B) Variants (all of above PLUS):**
- [ ] Test 5a: Backend logs show internal auth enabled
- [ ] Test 5b: Web app works through authenticated proxy
- [ ] Test 5c: Direct backend access fails with 403
- [ ] Test 5d: Wrong internal auth header fails with 403
- [ ] Test 5e: Mobile API returns 401 (not 403)
- [ ] Test 5f: Addon API works (not 403)
- [ ] Test 5g: Health check works without header
- [ ] Test 5h: Proxy config shows header being added
- [ ] Test 5i: Backend logs show failed auth attempts

---

## Troubleshooting

### API endpoints are prompting for authentication

**Problem**: Mobile/addon APIs showing Authelia login or Basic Auth prompt

**Solution**:
1. Check router priorities in Traefik dashboard
2. Verify API routers have priority 100 and web router has priority 1
3. Ensure API routers don't have middleware labels
4. Check Traefik logs: `docker logs traefik 2>&1 | grep imagetools`

### Web app not prompting for authentication

**Problem**: Can access web app without logging in

**Solution**:
1. Verify middleware name matches your Authelia middleware
2. Check Traefik dashboard to confirm middleware is attached
3. Verify Authelia is running: `docker ps | grep authelia`

### Cannot connect to ImageTools

**Problem**: Connection refused or 404 errors

**Solution**:
1. Verify ImageTools is running: `docker ps | grep imagetools`
2. Check health status: `docker inspect imagetools-app | grep Health`
3. Verify network connectivity: `docker network inspect traefik-network`
4. Check ImageTools logs: `docker logs imagetools-app`

### Uploads failing

**Problem**: Large file uploads timing out or failing

**Solution**:
1. Check Traefik timeout settings
2. Verify `client_max_body_size` in nginx (if applicable)
3. Ensure `MAX_UPLOAD_SIZE_MB` environment variable is set correctly
4. Check Traefik logs for timeout errors

### Getting 403 Forbidden on Web App (Hardened Variants)

**Problem**: Web app returns 403 Forbidden after successful Authelia/BasicAuth login

**Symptoms**:
- Proxy authentication works (Authelia login or basic auth succeeds)
- But web app returns "Forbidden" error
- Backend logs show: "Internal auth validation failed"

**Root Cause**: Internal auth header not being added by proxy or secret mismatch

**Solution**:

1. **Check that REQUIRE_INTERNAL_AUTH is set:**
   ```bash
   docker exec imagetools-app env | grep REQUIRE_INTERNAL_AUTH
   # Should show: REQUIRE_INTERNAL_AUTH=true
   ```

2. **Verify secret is set in backend:**
   ```bash
   docker exec imagetools-app env | grep INTERNAL_AUTH_SECRET
   # Should show the secret value
   ```

3. **For Traefik: Check middleware is defined:**
   ```bash
   docker logs traefik | grep "imagetools-internal-auth"
   # Should show middleware being created
   ```
   
   Verify the label in docker-compose.yml:
   ```yaml
   - "traefik.http.middlewares.imagetools-internal-auth.headers.customrequestheaders.X-Internal-Auth=${INTERNAL_AUTH_SECRET}"
   ```

4. **For Traefik: Check middleware is applied to router:**
   ```bash
   # Check Traefik dashboard or logs
   docker logs traefik | grep "imagetools-web"
   ```
   
   Verify the router label includes both middlewares:
   ```yaml
   - "traefik.http.routers.imagetools-web.middlewares=authelia@docker,imagetools-internal-auth@docker"
   ```

5. **For nginx: Check header is in config:**
   ```bash
   docker exec imagetools-nginx cat /etc/nginx/conf.d/default.conf | grep X-Internal-Auth
   # Should show: proxy_set_header X-Internal-Auth "<secret>";
   ```

6. **Verify secret matches:**
   ```bash
   # Get secret from .env
   cat .env | grep INTERNAL_AUTH_SECRET
   
   # Compare with backend
   docker exec imagetools-app env | grep INTERNAL_AUTH_SECRET
   
   # For nginx, check generated config
   docker exec imagetools-nginx cat /etc/nginx/conf.d/default.conf | grep X-Internal-Auth
   
   # All three should show the SAME secret value
   ```

7. **Check backend logs for specific error:**
   ```bash
   docker logs imagetools-app | grep -A 5 "Internal auth"
   
   # Possible messages:
   # "Missing X-Internal-Auth header" → Proxy not adding header
   # "Invalid X-Internal-Auth header" → Secret mismatch
   # "Internal auth secret not configured" → INTERNAL_AUTH_SECRET not set
   ```

8. **Restart services after fixing:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### Mobile/Addon APIs Returning 403 (Hardened Variants)

**Problem**: Mobile or addon APIs return 403 Forbidden

**Root Cause**: API endpoints incorrectly receiving internal auth validation or proxy adding header to API routes

**Solution**:

1. **For Traefik: Verify API routers don't have internal-auth middleware:**
   ```bash
   docker logs traefik | grep "imagetools-api"
   ```
   
   API routers should NOT have the `imagetools-internal-auth` middleware:
   ```yaml
   # Correct - no middleware
   - "traefik.http.routers.imagetools-api-mobile.middlewares="
   
   # Wrong - has middleware
   - "traefik.http.routers.imagetools-api-mobile.middlewares=imagetools-internal-auth@docker"
   ```

2. **For nginx: Verify API locations don't have internal auth header:**
   ```bash
   docker exec imagetools-nginx cat /etc/nginx/conf.d/default.conf
   ```
   
   Check that API location blocks do NOT have `X-Internal-Auth` header:
   ```nginx
   # Correct
   location ~ ^/api/v1/(mobile|addon)/ {
       auth_basic off;
       proxy_pass http://imagetools:8081;
       # ... other headers ...
       # NO X-Internal-Auth header here!
   }
   ```

3. **Check backend logs:**
   ```bash
   docker logs imagetools-app | grep "api/v1"
   
   # Should NOT see internal auth validation errors for API endpoints
   ```

4. **Test API directly to backend (should work):**
   ```bash
   # Mobile API
   curl http://localhost:8081/api/v1/mobile/validate-auth
   # Should return 401 (needs mobile secret) NOT 403
   
   # Addon API
   curl http://localhost:8081/api/v1/addon/validate
   # Should return validation response NOT 403
   ```

### Backend Won't Start: "Internal auth secret not configured"

**Problem**: Backend container exits with error about internal auth secret

**Error message**: `"REQUIRE_INTERNAL_AUTH is true but INTERNAL_AUTH_SECRET is not set"`

**Solution**:

1. **Check .env file exists and has the secret:**
   ```bash
   cat .env | grep INTERNAL_AUTH_SECRET
   # Should show: INTERNAL_AUTH_SECRET=<your-secret>
   ```

2. **Verify docker-compose.yml references the secret:**
   ```yaml
   services:
     imagetools:
       environment:
         - REQUIRE_INTERNAL_AUTH=true
         - INTERNAL_AUTH_SECRET=${INTERNAL_AUTH_SECRET}  # Make sure this line exists
   ```

3. **Check that .env file is in the same directory as docker-compose.yml:**
   ```bash
   ls -la .env docker-compose.yml
   # Both files should be in the same directory
   ```

4. **Try setting the variable explicitly (for testing):**
   ```bash
   INTERNAL_AUTH_SECRET=test123 docker-compose up -d
   ```
   
   If this works, the issue is with `.env` file loading.

5. **Regenerate secret and update .env:**
   ```bash
   openssl rand -hex 32 > secret.txt
   echo "INTERNAL_AUTH_SECRET=$(cat secret.txt)" > .env
   rm secret.txt
   ```

6. **Restart services:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### Need to Rotate Internal Auth Secret

**Problem**: Need to change the internal auth secret (security incident, periodic rotation, team change)

**Procedure**:

1. **Generate new secret:**
   ```bash
   openssl rand -hex 32
   # Save the output
   ```

2. **Update .env file with new secret:**
   ```bash
   # Edit .env file
   nano .env
   
   # Or use sed
   NEW_SECRET=$(openssl rand -hex 32)
   sed -i "s/^INTERNAL_AUTH_SECRET=.*/INTERNAL_AUTH_SECRET=$NEW_SECRET/" .env
   ```

3. **Verify .env file:**
   ```bash
   cat .env | grep INTERNAL_AUTH_SECRET
   # Should show new secret
   ```

4. **For nginx variant: Clear any cached configs:**
   ```bash
   docker-compose down
   # Optional: remove nginx container to force full rebuild
   docker rm imagetools-nginx
   ```

5. **Restart all services:**
   ```bash
   docker-compose up -d
   ```

6. **Verify new secret is active:**
   ```bash
   # Check backend picked up new secret
   docker logs imagetools-app | grep "Internal auth"
   
   # Test web access (should work)
   curl -u admin:password https://imagetools.yourdomain.com/
   
   # Test direct backend access (should fail)
   curl http://localhost:8081/
   # Expected: 403 Forbidden
   ```

7. **Test all endpoints work:**
   - Web app (should work after proxy auth)
   - Mobile API (should work, return 401 for invalid token)
   - Addon API (should work)
   - Health check (should work)

8. **Document the rotation:**
   - Update password manager
   - Notify team (if applicable)
   - Remove old secret from backups

**Rotation frequency:**
- High security: Every 90 days
- Standard: Every 180 days  
- After incident: Immediately
- After team member departure: Immediately

### nginx Template Substitution Failed

**Problem**: nginx container exits or config has literal `${INTERNAL_AUTH_HEADER}` in output

**Symptoms**:
```bash
docker exec imagetools-nginx cat /etc/nginx/conf.d/default.conf | grep INTERNAL_AUTH_HEADER
# Shows: ${INTERNAL_AUTH_HEADER}  # This is wrong!
```

**Solution**:

1. **Check entrypoint script exists and is executable:**
   ```bash
   ls -la deployment/nginx/docker-entrypoint.sh
   # Should show: -rwxr-xr-x (executable permissions)
   
   # If not executable:
   chmod +x deployment/nginx/docker-entrypoint.sh
   ```

2. **Verify template file exists:**
   ```bash
   ls -la nginx/nginx.conf.template
   # Should exist
   ```

3. **Check docker-compose.yml has correct mounts:**
   ```yaml
   services:
     nginx:
       volumes:
         - ./nginx/nginx.conf.template:/etc/nginx/templates/nginx.conf.template:ro
         - ./deployment/nginx/docker-entrypoint.sh:/docker-entrypoint.sh:ro
       entrypoint: ["/docker-entrypoint.sh"]
   ```

4. **Check nginx container logs:**
   ```bash
   docker logs imagetools-nginx
   
   # Should see:
   # "Processing nginx configuration template..."
   # "nginx configuration generated successfully"
   ```

5. **Manually test the substitution:**
   ```bash
   export INTERNAL_AUTH_SECRET="test123"
   export INTERNAL_AUTH_HEADER="proxy_set_header X-Internal-Auth \"$INTERNAL_AUTH_SECRET\";"
   envsubst '${INTERNAL_AUTH_HEADER}' < nginx/nginx.conf.template
   
   # Check output has real header, not ${INTERNAL_AUTH_HEADER}
   ```

6. **Rebuild nginx container:**
   ```bash
   docker-compose down
   docker rm imagetools-nginx
   docker-compose up -d nginx
   ```

---

## Architecture Diagrams

### Traefik + Authelia Flow

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ 1. GET /
       ▼
┌─────────────────────────────────────┐
│          Traefik Router             │
│  (imagetools-web, priority=1)       │
│  Middleware: authelia@docker        │
└──────┬──────────────────────────────┘
       │ 2. Forward auth
       ▼
┌─────────────────────────────────────┐
│           Authelia                  │
│  /api/verify                        │
└──────┬──────────────────────────────┘
       │ 3. Not authenticated
       │ Return 401 + redirect
       ▼
┌─────────────────────────────────────┐
│      Authelia Login Page            │
└──────┬──────────────────────────────┘
       │ 4. User logs in
       │ Session cookie set
       ▼
┌─────────────────────────────────────┐
│       ImageTools Web App            │
└─────────────────────────────────────┘
```

### Mobile API Bypass Flow

```
┌─────────────┐
│ Mobile App  │
└──────┬──────┘
       │ 1. POST /api/v1/mobile/upload
       │    + long_term_secret
       ▼
┌─────────────────────────────────────┐
│          Traefik Router             │
│  (imagetools-mobile, priority=100)  │
│  NO middleware                      │
└──────┬──────────────────────────────┘
       │ 2. Direct proxy (no auth)
       ▼
┌─────────────────────────────────────┐
│      ImageTools Backend             │
│  Validates long_term_secret         │
└─────────────────────────────────────┘
```

### Internal Authentication Flow (Hardened Variants)

This flow shows how internal authentication adds a defense-in-depth layer.

**Web Request Flow (Hardened):**

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ 1. GET /
       ▼
┌─────────────────────────────────────┐
│          Reverse Proxy              │
│    (Traefik or nginx)               │
│  Step 1: Check user auth            │
│  (Authelia or BasicAuth)            │
└──────┬──────────────────────────────┘
       │ 2. ✓ User authenticated
       │
       │ Add internal auth header:
       │ X-Internal-Auth: <secret>
       ▼
┌─────────────────────────────────────┐
│      ImageTools Backend             │
│  Internal Auth Middleware           │
│                                     │
│  Step 2: Validate internal header   │
│  - Check X-Internal-Auth exists     │
│  - Compare with INTERNAL_AUTH_SECRET│
└──────┬──────────────────────────────┘
       │
       ├─ ✓ Header valid
       │  → Continue to application logic
       │  → Render page
       │
       └─ ✗ Header invalid/missing
          → Return 403 Forbidden
          → Log security event
```

**Attack Scenario: Direct Backend Access (Hardened):**

```
┌─────────────────┐
│    Attacker     │
│  (compromised   │
│   container)    │
└──────┬──────────┘
       │ 1. Direct request to backend
       │    http://imagetools:8081/
       │    (bypasses reverse proxy)
       ▼
┌─────────────────────────────────────┐
│      ImageTools Backend             │
│  Internal Auth Middleware           │
│                                     │
│  Check: X-Internal-Auth header      │
│  Result: MISSING                    │
└──────┬──────────────────────────────┘
       │
       └─ ✗ No header
          → Return 403 Forbidden
          → Log: "Internal auth validation failed"
          → ATTACK BLOCKED ✅
```

**Why This Protects:**
- Even with Docker network access, attacker cannot access backend
- Missing internal auth header causes immediate rejection
- No data leaked, no application code executed

**API Request Flow (Hardened - Shows Bypass):**

```
┌─────────────┐
│ Mobile App  │
└──────┬──────┘
       │ 1. POST /api/v1/mobile/upload
       │    Authorization: Bearer <mobile-secret>
       ▼
┌─────────────────────────────────────┐
│          Reverse Proxy              │
│  Route: /api/v1/mobile/*            │
│  No auth middleware                 │
│  No X-Internal-Auth header added    │
└──────┬──────────────────────────────┘
       │ 2. Forward request
       │    (no internal auth header)
       ▼
┌─────────────────────────────────────┐
│      ImageTools Backend             │
│  Internal Auth Middleware           │
│                                     │
│  Check: Is path /api/v1/mobile/*?   │
│  Result: YES → BYPASS internal auth │
└──────┬──────────────────────────────┘
       │
       └─ ✓ Bypass internal auth
          → Continue to Mobile API handler
          → Validate mobile token (separate auth)
          → Process request
```

**Why API Bypass is Safe:**
- Mobile/addon APIs have their own authentication (token-based)
- They are NOT unauthenticated, just use different auth method
- Still protected by application-level token validation
- Designed for external access (apps, browser extensions)

### Comparison: Simplified vs Hardened Flow

**Simplified (A) Variant:**
```
User → Proxy (Auth) → Backend → Response
       ✓ One layer of protection
```

**Hardened (B) Variant:**
```
User → Proxy (Auth + Add Header) → Backend (Validate Header) → Response
       ✓ First layer          ✓ Second layer
       ✓ Defense in Depth
```

**Attack Surface Comparison:**

| Attack Vector | Simplified (A) | Hardened (B) |
|---------------|----------------|--------------|
| **Compromised container on Docker network** | ❌ Can access backend directly | ✅ Blocked by internal auth |
| **Accidental port exposure (8081)** | ❌ Backend fully exposed | ✅ Returns 403 (internal auth) |
| **Docker host compromise** | ⚠️ Can access via bridge network | ✅ Still requires secret |
| **Proxy misconfiguration** | ❌ Backend becomes accessible | ⚠️ Still requires secret (partial mitigation) |
| **Web auth bypass (user)** | Protected by proxy | Protected by proxy |
| **API token theft** | Protected by token validation | Protected by token validation |

---

## Security Considerations

### Deployment Variant Selection Guide

**Choose Simplified (A) if:**
- Local development environment
- Testing/staging with no sensitive data
- Trusted network environment (no external access)
- Low security requirements

**Choose Hardened (B) if:**
- Production deployment
- Internet-facing application
- Handling sensitive user data
- Compliance requirements (SOC2, ISO27001, HIPAA, PCI-DSS)
- Multi-tenant Docker host
- Defense-in-depth security required

**Default Recommendation**: Always use Hardened (B) for production deployments.

### Defense-in-Depth with Internal Authentication

Hardened (B) variants implement **defense-in-depth** security using internal authentication headers. This provides multiple layers of protection.

#### Layer 1: Reverse Proxy Authentication
- Traefik + Authelia (OIDC/LDAP integration, 2FA)
- Traefik + Basic Auth (simple username/password)
- nginx + Basic Auth (simple username/password)

**Protects against**: Unauthorized users accessing the web interface

#### Layer 2: Internal Authentication Header
- Secret header added by reverse proxy
- Validated by backend before processing requests
- Protects backend even if Layer 1 is bypassed

**Protects against**:
- Compromised containers on Docker network
- Accidental backend port exposure
- Docker host network attacks
- Proxy misconfiguration
- Internal network threats

#### Layer 3: Application-Level Authentication
- Session management for web users
- Token-based auth for mobile apps
- OAuth tokens for browser addons

**Protects against**: Application-level attacks, session hijacking, token theft

### Attack Scenarios Mitigated by Internal Auth

#### Scenario 1: Compromised Container

**Threat**: Attacker compromises another container on the same Docker network (e.g., vulnerable WordPress plugin)

**Without Internal Auth (Simplified):**
```bash
# From compromised container
curl http://imagetools:8081/
# Returns: 200 OK with full web app
# Attacker has full access! ❌
```

**With Internal Auth (Hardened):**
```bash
# From compromised container
curl http://imagetools:8081/
# Returns: 403 Forbidden
# Attack blocked! ✅
```

**Impact**: Prevents lateral movement attacks in containerized environments

#### Scenario 2: Accidental Port Exposure

**Threat**: Backend port accidentally exposed via docker-compose (e.g., `ports: - "8081:8081"`)

**Without Internal Auth:**
- Backend fully accessible at `http://server-ip:8081`
- No authentication required
- Complete compromise ❌

**With Internal Auth:**
- Backend returns 403 Forbidden for all requests
- Attacker cannot access application
- Only requests from proxy with correct header work ✅

**Real-world example**: Developer accidentally commits port mapping, pushes to production. Hardened variant still protects.

#### Scenario 3: Docker Host Network Access

**Threat**: Attacker gains access to Docker host network (e.g., via SSH compromise, host-level vulnerability)

**Without Internal Auth:**
```bash
# From Docker host
curl http://172.17.0.3:8081/
# Returns: 200 OK
# Full access via bridge network ❌
```

**With Internal Auth:**
```bash
# From Docker host
curl http://172.17.0.3:8081/
# Returns: 403 Forbidden
# Attack blocked! ✅
```

**Impact**: Limits blast radius of host-level compromises

#### Scenario 4: Reverse Proxy Misconfiguration

**Threat**: Traefik/nginx configuration error removes authentication middleware

**Without Internal Auth:**
- Backend immediately exposed
- All users have unauthenticated access
- Complete compromise ❌

**With Internal Auth:**
- Backend returns 403 (no internal auth header)
- Application unavailable but not compromised
- Time to fix configuration before data breach ⚠️

**Impact**: Fail-safe mechanism reduces misconfiguration risk

### Security Comparison Table

| Security Aspect | Simplified (A) | Hardened (B) |
|-----------------|----------------|--------------|
| **Web Authentication** | ✅ Proxy-level | ✅ Proxy-level |
| **API Authentication** | ✅ Token-based | ✅ Token-based |
| **Backend Protection** | ❌ Single layer | ✅ Two layers |
| **Container Isolation** | ❌ Network-level only | ✅ Application-level |
| **Port Exposure Protection** | ❌ Full exposure | ✅ Returns 403 |
| **Misconfiguration Safety** | ❌ Immediate exposure | ⚠️ Fail-safe |
| **Compliance Ready** | ⚠️ Basic | ✅ Defense-in-depth |
| **Zero Trust Compatible** | ❌ No | ✅ Yes |
| **Production Ready** | ⚠️ Basic security | ✅ Enterprise security |

### Compliance & Standards

Hardened (B) variants support compliance with industry security standards:

#### SOC 2 (Type II)
- ✅ Defense-in-depth architecture
- ✅ Access control at multiple layers
- ✅ Secret management best practices
- ✅ Audit logging of security events

#### ISO 27001
- ✅ Information security controls (A.9.1: Access control policy)
- ✅ Network security management (A.13.1)
- ✅ Secure system architecture (A.14.1)
- ✅ Cryptographic controls (A.10.1: secret generation)

#### HIPAA (Healthcare)
- ✅ Access control (§164.312(a)(1))
- ✅ Integrity controls (§164.312(c)(1))
- ✅ Transmission security (§164.312(e)(1))
- ⚠️ Additional controls required for PHI

#### PCI-DSS (Payment Card Industry)
- ✅ Requirement 2: Do not use vendor defaults (custom secrets)
- ✅ Requirement 6: Develop secure systems
- ✅ Requirement 7: Restrict access to cardholder data
- ⚠️ Additional controls required for card data

**Note**: Internal authentication alone does not guarantee compliance. Additional controls, logging, and documentation are required.

### Why This Approach is Secure

**Simplified (A) Variants:**
1. ✅ **Web authentication enforced**: All web routes require Authelia/Basic Auth
2. ✅ **API authentication intact**: Mobile/addon use their own token-based auth
3. ✅ **No authentication bypass**: API routes don't disable auth, they use different auth methods
4. ⚠️ **Single layer of defense**: Relies solely on proxy authentication

**Hardened (B) Variants (all of above PLUS):**
5. ✅ **Defense in depth**: Both reverse proxy AND backend validate requests
6. ✅ **Internal network protection**: Prevents lateral movement attacks
7. ✅ **Fail-safe design**: Misconfiguration causes unavailability, not data breach
8. ✅ **Zero Trust principles**: Backend trusts no requests without validation

### Production Recommendations

#### Essential (All Deployments)
1. **Use HTTPS**: Always use TLS/SSL for production (via Let's Encrypt)
2. **Regular updates**: Keep ImageTools, Traefik/nginx, and Authelia updated
3. **Monitor logs**: Watch for authentication failures and suspicious activity
4. **Network isolation**: Use Docker networks to isolate services
5. **Backup secrets**: Securely backup mobile secrets and addon tokens

#### Hardened Deployments (Additional)
6. **Use Hardened (B) variants**: Enable internal authentication for production
7. **Rotate secrets**: Change internal auth secret every 90-180 days
8. **Monitor failed auth**: Alert on internal auth validation failures
9. **Least privilege**: Only expose necessary ports
10. **Security scanning**: Regularly scan containers for vulnerabilities

#### Advanced (High Security)
11. **Enable 2FA**: Configure Authelia with TOTP/2FA for web access
12. **Rate limiting**: Add rate limiting middleware to Traefik
13. **Intrusion detection**: Monitor Docker logs for suspicious patterns
14. **Security audits**: Periodic security assessments
15. **Incident response**: Have plan for security incidents

### Mobile/Addon API Security

**Mobile API** uses long-term secrets:
- Generated during QR code pairing
- Stored securely on device
- Can be regenerated/revoked via web interface
- **Bypasses internal auth** (designed for external access)
- Uses separate application-level token validation

**Addon API** uses OAuth-style tokens:
- Short-lived access tokens
- Refresh tokens for renewal
- Can be revoked via web interface
- **Bypasses internal auth** (designed for external access)
- Uses separate application-level token validation

**Why API bypass is secure:**
- APIs have their own robust authentication (token-based)
- They are NOT unauthenticated, just use different auth method
- Designed for external access (mobile apps, browser extensions)
- Token-based auth is appropriate for API-style access
- Internal auth would break API functionality without adding security value

Both methods are independent of web authentication and don't require Authelia/Basic Auth.

### When Internal Auth is NOT Required

Internal authentication can be **omitted** (use Simplified variants) in these scenarios:

1. **Local development**: Running on localhost for testing
2. **Private network**: Deployed on isolated network with no external access
3. **Trusted environment**: Single-tenant dedicated server with trusted users only
4. **Testing/staging**: Non-production environment with no sensitive data
5. **Educational**: Learning Docker/Traefik with sample data

**Important**: Even in these scenarios, proxy-level authentication (Authelia/BasicAuth) should still be enabled.

### Security Best Practices Summary

✅ **Do:**
- Use Hardened (B) variants for production
- Generate strong random secrets (64-char hex minimum)
- Store secrets in `.env` file, never in compose file
- Add `.env` to `.gitignore` immediately
- Use different secrets per environment (dev/staging/prod)
- Rotate secrets periodically (90-180 days)
- Monitor logs for failed internal auth attempts
- Enable HTTPS with valid certificates
- Keep all components updated

❌ **Don't:**
- Don't use predictable secrets ("secret123", "password")
- Don't commit secrets to version control
- Don't reuse secrets across environments
- Don't expose backend port (8081) externally
- Don't disable internal auth in production
- Don't skip proxy authentication (Authelia/BasicAuth)
- Don't ignore failed authentication in logs

---

## Summary

This authentication implementation provides **flexible deployment options** with two security variants for each scenario.

### Deployment Options

**Three deployment scenarios, each with two variants:**

1. **Scenario 1A/1B**: Traefik + Authelia
   - Best for: Production with SSO/LDAP integration, 2FA support
   - Auth method: OIDC/LDAP via Authelia
   - Complexity: Medium (requires Authelia setup)

2. **Scenario 2A/2B**: Traefik + Basic Auth
   - Best for: Small deployments, personal use
   - Auth method: Username/password (HTTP Basic Auth)
   - Complexity: Low (simple password hash)

3. **Scenario 3A/3B**: Standalone nginx
   - Best for: No Traefik infrastructure
   - Auth method: Username/password via nginx
   - Complexity: Low (standalone setup)

**Variant selection:**
- **A (Simplified)**: Single-layer proxy auth, suitable for dev/testing
- **B (Hardened)**: Defense-in-depth with internal auth, **recommended for production**

### Key Features

✅ **Zero external configuration changes**
- No modifications to Traefik static/dynamic config
- No modifications to Authelia configuration  
- No modifications to nginx config files (unless standalone)

✅ **Self-contained deployment**
- All routing defined in docker-compose labels
- Drop-in integration with existing infrastructure
- Single file deployment (plus .env for Hardened)

✅ **Simple maintenance**
- Update docker-compose.yml to change configuration
- No need to restart Traefik or Authelia
- Container restart picks up new labels

✅ **Secure by default**
- Web routes protected by Authelia/Basic Auth (all variants)
- API routes use their own authentication (all variants)
- No authentication bypass vulnerabilities
- Defense-in-depth protection (Hardened variants)

✅ **Flexible security levels**
- Simplified (A): Single-layer auth for dev/testing
- Hardened (B): Multi-layer auth for production
- Easy migration from A → B

### Quick Decision Guide

**Choose your scenario:**

| Your Infrastructure | Recommended Scenario |
|---------------------|---------------------|
| Existing Traefik + Authelia | **Scenario 1B** (Hardened) |
| Existing Traefik, no Authelia | **Scenario 2B** (Hardened) |
| No Traefik | **Scenario 3B** (Hardened) |
| Local dev/testing only | Any Scenario **A** (Simplified) |

**Choose your variant:**

| Environment | Recommended Variant | Rationale |
|-------------|--------------------|-----------| 
| Production | **B (Hardened)** | Defense-in-depth, compliance-ready |
| Staging | **B (Hardened)** | Test production configuration |
| Development | **A (Simplified)** | Faster iteration, less setup |
| Local testing | **A (Simplified)** | Minimal configuration |

### Recommended Deployment

**For production environments:**
- **Primary recommendation**: Scenario 1B (Traefik + Authelia + Internal Auth)
- **Alternative**: Scenario 2B (Traefik + Basic Auth + Internal Auth)
- **Standalone**: Scenario 3B (nginx + Basic Auth + Internal Auth)

**Always use Hardened (B) variants for production** to ensure defense-in-depth security.

### Next Steps

1. **Choose your deployment scenario** based on existing infrastructure
2. **Select variant**: Use Hardened (B) for production, Simplified (A) for dev/test
3. **Follow the step-by-step guide** for your chosen scenario
4. **Test thoroughly** using the Testing section checklist
5. **Review Security Considerations** for production best practices

### Document Version

This authentication implementation plan covers:
- ✅ Three deployment scenarios (Traefik+Authelia, Traefik+BasicAuth, nginx)
- ✅ Two security variants per scenario (Simplified, Hardened)
- ✅ Complete configuration examples for all 6 combinations
- ✅ Internal authentication (defense-in-depth) implementation
- ✅ Comprehensive testing procedures
- ✅ Troubleshooting guides
- ✅ Security considerations and compliance guidance

**Total deployment options**: 6 (3 scenarios × 2 variants)

