# Scenario 2A: Traefik + Basic Auth (Simplified)

This is the **Simplified** variant without internal authentication. 

⚠️ **For production deployments, use [Scenario 2B (Hardened)](../scenario-2b-traefik-basicauth-hardened/) instead.**

## Prerequisites

- Existing Traefik setup with Docker provider enabled
- Docker and Docker Compose installed
- apache2-utils (for generating password hash)

## Setup Instructions

### 1. Generate Basic Auth Password Hash

```bash
# Using htpasswd (install apache2-utils if needed)
htpasswd -nb admin yourpassword

# Or using Docker
docker run --rm httpd:alpine htpasswd -nb admin yourpassword

# Output will look like: admin:$apr1$xyz$abc...
# Copy the entire output for the next step
```

### 2. Configure Environment

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` and set your password hash:
```bash
# Important: Escape $ signs in docker-compose by using $$
BASIC_AUTH_USERS=admin:$$apr1$$hash$$here
```

### 3. Find Your Network Name

```bash
# Find your Traefik network name
docker network ls | grep traefik
```

### 4. Update docker-compose.yml

Replace the placeholders:
- `traefik-network` → your actual Traefik network name
- `imagetools.yourdomain.com` → your domain
- `yourusername/imagetools:latest` → your image (or remove to use local build)
- Update `BASIC_AUTH_USERS` in the BasicAuth middleware label

### 5. Deploy

```bash
docker-compose up -d
```

### 6. Verify

```bash
# Check services are running
docker-compose ps

# Check logs
docker-compose logs -f

# Test web access (should prompt for basic auth)
curl -v https://imagetools.yourdomain.com/

# Test with credentials
curl -u admin:yourpassword https://imagetools.yourdomain.com/

# Test mobile API (should bypass auth)
curl https://imagetools.yourdomain.com/api/v1/mobile/validate-auth
# Expected: 401 (needs mobile secret) not basic auth prompt

# Test health check
curl https://imagetools.yourdomain.com/health
# Expected: 200 OK
```

## Security Note

This Simplified variant provides **single-layer authentication** at the reverse proxy level. For production deployments with defense-in-depth security, use [Scenario 2B (Hardened)](../scenario-2b-traefik-basicauth-hardened/).

## Upgrade to Hardened

To upgrade to the Hardened variant with internal authentication:

1. Generate a secret: `openssl rand -hex 32`
2. Add to `.env`: `INTERNAL_AUTH_SECRET=<your-secret>`
3. Follow [Scenario 2B setup instructions](../scenario-2b-traefik-basicauth-hardened/README.md)

## Documentation

See full documentation: [docs/AUTHENTICATION_IMPLEMENTATION_PLAN.md](../../../docs/AUTHENTICATION_IMPLEMENTATION_PLAN.md)
