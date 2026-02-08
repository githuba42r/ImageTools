# Scenario 2B: Traefik + Basic Auth (Hardened) ⭐ RECOMMENDED FOR PRODUCTION

This is the **Hardened** variant with internal authentication for defense-in-depth security.

This scenario uses Traefik with Basic Auth for user authentication PLUS internal authentication headers for enhanced security against compromised containers and network attacks.

## Architecture

```
Web Request:
User → Traefik
       │
       ├─> Basic Auth Middleware (imagetools-basicauth@docker)
       │   └─> Validates username/password
       │   └─> If valid, continues
       │
       ├─> Internal Auth Middleware (imagetools-internal-auth@docker)  
       │   └─> Adds header: X-Internal-Auth: <secret>
       │
       └─> ImageTools Backend
           └─> Validates X-Internal-Auth header matches INTERNAL_AUTH_SECRET
           └─> If valid, processes request
           └─> If invalid/missing, returns 403 Forbidden

Mobile/Addon API Request:
Mobile/Addon → Traefik → ImageTools Backend (direct, no middleware)
               └─> Bypasses internal auth validation
               └─> Uses app-level token auth instead
```

## Prerequisites

- Existing Traefik setup with Docker provider enabled
- Docker and Docker Compose installed
- apache2-utils (for generating password hash)

## Setup Instructions

### 1. Generate Internal Auth Secret

```bash
# Generate a secure 64-character hex string
openssl rand -hex 32

# Example output:
# 7a3f8c2b1e9d4a5f6c8b3e1d9a7c5f2b4e6d8a9c1b3f5e7d9a2c4b6e8f1a3c5e7
```

### 2. Generate Basic Auth Password Hash

```bash
# Using htpasswd (install apache2-utils if needed)
htpasswd -nb admin yourpassword

# Or using Docker
docker run --rm httpd:alpine htpasswd -nb admin yourpassword

# Output will look like: admin:$apr1$xyz$abc...
# Copy the entire output for the next step
```

### 3. Configure Environment

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` and set your secrets:
```bash
# REQUIRED: Internal authentication secret (from step 1)
INTERNAL_AUTH_SECRET=7a3f8c2b1e9d4a5f6c8b3e1d9a7c5f2b4e6d8a9c1b3f5e7d9a2c4b6e8f1a3c5e7

# REQUIRED: Basic auth password hash (from step 2)
# Important: Escape $ signs by using $$ in docker-compose
BASIC_AUTH_USERS=admin:$$apr1$$hash$$here
```

⚠️ **Security**: Never commit `.env` to version control. Add it to `.gitignore`.

### 4. Find Your Network Name

```bash
# Find your Traefik network name
docker network ls | grep traefik
```

### 5. Update docker-compose.yml

Replace the placeholders:
- `traefik-network` → your actual Traefik network name
- `imagetools.yourdomain.com` → your domain
- `yourusername/imagetools:latest` → your image (or remove to use local build)

### 6. Deploy

```bash
# Verify secrets are set
cat .env | grep -E "INTERNAL_AUTH_SECRET|BASIC_AUTH_USERS"

# Deploy
docker-compose up -d

# Verify internal auth is enabled
docker logs imagetools-app | grep -i "internal auth"
# Should see: "Internal authentication middleware enabled"
```

### 7. Verify

```bash
# Check services are running
docker-compose ps

# Check logs
docker-compose logs -f

# Test web access (should prompt for basic auth)
curl -v https://imagetools.yourdomain.com/

# Test with credentials
curl -u admin:yourpassword https://imagetools.yourdomain.com/

# Test without internal auth header (direct to backend - should fail)
docker exec imagetools-app curl -v http://localhost:8081/
# Expected: 403 Forbidden (missing X-Internal-Auth header)

# Test mobile API (should bypass auth)
curl https://imagetools.yourdomain.com/api/v1/mobile/validate-auth
# Expected: 401 (needs mobile secret) not basic auth prompt

# Test health check
curl https://imagetools.yourdomain.com/health
# Expected: 200 OK
```

## Key Differences from Scenario 2A (Simplified)

| Aspect | Scenario 2A (Simplified) | Scenario 2B (Hardened) |
|--------|--------------------------|------------------------|
| **Middleware Chain** | Only `basicauth@docker` | `basicauth@docker,internal-auth@docker` |
| **Defense Layers** | 1 (Basic Auth) | 2 (Basic Auth + Internal) |
| **Backend Validation** | None | Validates X-Internal-Auth header |
| **Environment Vars** | Basic auth only | + `REQUIRE_INTERNAL_AUTH=true`, `INTERNAL_AUTH_SECRET=...` |
| **Setup Complexity** | Simple | +1 secret to generate |
| **Security Level** | Good | Excellent (defense in depth) |

## Security Benefits

This Hardened variant provides protection against:

1. **Compromised Containers**: Other containers on the Docker network cannot directly access the backend
2. **Network Attacks**: Attackers on the Docker host network are blocked
3. **Misconfiguration**: If Traefik is misconfigured, backend still validates requests
4. **Port Exposure**: If backend port is accidentally exposed, requests without the secret are rejected

## Troubleshooting

### Internal Auth Errors

If you see `403 Forbidden` errors:

```bash
# Check backend logs
docker logs imagetools-app | grep -i "internal auth"

# Verify secret is set correctly
docker exec imagetools-app env | grep INTERNAL_AUTH_SECRET

# Check Traefik is adding the header
docker logs traefik | grep imagetools-internal-auth
```

### Basic Auth Not Working

```bash
# Verify basic auth middleware is defined
docker logs traefik | grep basicauth

# Check password hash format (must escape $ with $$)
cat .env | grep BASIC_AUTH_USERS
```

## Documentation

See full documentation: [docs/AUTHENTICATION_IMPLEMENTATION_PLAN.md](../../../docs/AUTHENTICATION_IMPLEMENTATION_PLAN.md)

## Downgrade to Simplified

If you need to temporarily disable internal auth:

1. Edit `docker-compose.yml`, change: `REQUIRE_INTERNAL_AUTH=false`
2. Remove `imagetools-internal-auth@docker` from web router middleware
3. Restart: `docker-compose up -d`
