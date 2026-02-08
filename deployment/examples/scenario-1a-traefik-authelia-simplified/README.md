# Scenario 1A: Traefik + Authelia (Simplified)

This is the **Simplified** variant without internal authentication. 

⚠️ **For production deployments, use [Scenario 1B (Hardened)](../scenario-1b-traefik-authelia-hardened/) instead.**

## Prerequisites

- Existing Traefik setup
- Existing Authelia middleware
- Docker and Docker Compose installed

## Setup Instructions

### 1. Configure Environment

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` and set your values:
```bash
# No internal auth configuration needed for Simplified variant
```

### 2. Find Your Network and Middleware Names

```bash
# Find your Traefik network name
docker network ls | grep traefik

# Find your Authelia middleware name
docker logs traefik 2>&1 | grep authelia
# Common names: authelia@docker, authelia-verify@docker, auth@docker
```

### 3. Update docker-compose.yml

Replace the placeholders:
- `traefik-network` → your actual Traefik network name
- `authelia@docker` → your actual Authelia middleware name
- `imagetools.yourdomain.com` → your domain
- `yourusername/imagetools:latest` → your image (or remove to use local build)

### 4. Deploy

```bash
docker-compose up -d
```

### 5. Verify

```bash
# Check services are running
docker-compose ps

# Check logs
docker-compose logs -f

# Test web access (should redirect to Authelia)
curl -v https://imagetools.yourdomain.com/

# Test mobile API (should bypass auth)
curl https://imagetools.yourdomain.com/api/v1/mobile/validate-auth
# Expected: 401 (needs mobile secret) not auth redirect

# Test health check
curl https://imagetools.yourdomain.com/health
# Expected: 200 OK
```

## Security Note

This Simplified variant provides **single-layer authentication** at the reverse proxy level. For production deployments with defense-in-depth security, use [Scenario 1B (Hardened)](../scenario-1b-traefik-authelia-hardened/).

## Upgrade to Hardened

To upgrade to the Hardened variant with internal authentication:

1. Generate a secret: `openssl rand -hex 32`
2. Add to `.env`: `INTERNAL_AUTH_SECRET=<your-secret>`
3. Follow [Scenario 1B setup instructions](../scenario-1b-traefik-authelia-hardened/README.md)

## Documentation

See full documentation: [docs/AUTHENTICATION_IMPLEMENTATION_PLAN.md](../../../docs/AUTHENTICATION_IMPLEMENTATION_PLAN.md)
