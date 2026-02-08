# Upgrading ImageTools

This document describes breaking changes and upgrade steps between versions.

## Upgrading to v1.3.1

### Environment Variable Change: `OPENROUTER_APP_URL` → `INSTANCE_URL`

**Breaking Change:** The `OPENROUTER_APP_URL` environment variable has been replaced with `INSTANCE_URL`.

#### Why?

`INSTANCE_URL` is now the single source of truth for all external-facing URLs:
- Android mobile QR code enrollments
- Browser addon connection URLs  
- OpenRouter OAuth callback URLs

This ensures consistency across all enrollment methods and simplifies configuration.

#### Migration Steps

**If using Docker Compose:**

1. Edit your `docker-compose.yml` or `.env` file
2. Replace:
   ```yaml
   - OPENROUTER_APP_URL=http://your-url:port
   ```
   With:
   ```yaml
   - INSTANCE_URL=http://your-url:port
   ```

3. Restart the container:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

**If using Docker run:**

1. Replace the environment variable in your `docker run` command:
   ```bash
   # Old
   docker run -e OPENROUTER_APP_URL=http://your-url:port ...
   
   # New
   docker run -e INSTANCE_URL=http://your-url:port ...
   ```

**If using Kubernetes/other orchestration:**

Update your deployment manifests to use `INSTANCE_URL` instead of `OPENROUTER_APP_URL`.

#### What if I don't update?

The system will fall back to the default value: `http://localhost:8000`

This means:
- ❌ Mobile QR enrollments will use `localhost` (won't work)
- ❌ Browser addon connections will use `localhost` (won't work)
- ❌ OAuth callbacks will use `localhost` (won't work)

**You must set `INSTANCE_URL` to your actual deployment URL for these features to work.**

#### Example Values

```bash
# Local development
INSTANCE_URL=http://localhost:8082

# LAN deployment
INSTANCE_URL=http://192.168.1.100:8082

# Production with domain
INSTANCE_URL=https://imagetools.yourdomain.com

# Production with reverse proxy
INSTANCE_URL=https://yourdomain.com/imagetools
```

### Performance Improvement: Lazy Loading

v1.3.1 implements lazy loading for the `rembg` (background removal) library, reducing startup time from ~31 seconds to <1 second.

**No action required** - this is transparent to users. The first background removal operation will take an additional ~31 seconds (one time), but subsequent operations are instant.

---

## Version History

### v1.3.1 (2026-02-08)
- **Breaking:** Replaced `OPENROUTER_APP_URL` with `INSTANCE_URL`
- Fixed version.json loading in Docker
- Improved startup performance (31s → <1s)
- Added health check log filtering
- Fixed OAuth callback URL to use instance URL

### v1.3.0
- Added DEBUG_ENROLMENT feature
- Dynamic version display
- Authelia session info display
- Configurable max images limit
- Unified icon system

### v1.2.0
- Previous stable release
