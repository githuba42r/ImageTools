# Upgrading ImageTools

This document describes breaking changes and upgrade steps between versions.

## Upgrading to v1.3.1

### Environment Variable Change: `OPENROUTER_APP_URL` → `INSTANCE_URL`

**Breaking Change:** The `OPENROUTER_APP_URL` environment variable has been deprecated in favor of automatic URL detection from request headers.

#### What Changed?

The system now automatically detects your deployment URL from HTTP headers (just like Android and browser addon enrollments):

**Priority order:**
1. **X-Forwarded-Host + X-Forwarded-Proto** headers (from reverse proxy like Traefik/nginx) ✅ Recommended
2. **Host** header (from direct requests)
3. **INSTANCE_URL** environment variable (fallback only)

This means you **no longer need to set environment variables** in most deployments!

#### Do I Need to Do Anything?

**If you're using a reverse proxy (Traefik, nginx, Caddy, Apache):**
- ✅ **No action required!** The system will auto-detect the URL from `X-Forwarded-Host` and `X-Forwarded-Proto` headers
- Your reverse proxy likely already sets these headers automatically

**If you're accessing directly (no reverse proxy):**
- ✅ **No action required!** The system will use the `Host` header from the browser request

**If you need to override the detection:**
- Set `INSTANCE_URL` environment variable to your desired URL

#### Migration Steps (Optional)

If you previously had `OPENROUTER_APP_URL` set, you can:

1. **Option A: Remove it** (recommended) - let the system auto-detect
   ```bash
   # Remove from docker-compose.yml or .env:
   # - OPENROUTER_APP_URL=http://your-url:port  # DELETE THIS LINE
   ```

2. **Option B: Rename to INSTANCE_URL** (if you need to override auto-detection)
   ```yaml
   # In docker-compose.yml or .env:
   - INSTANCE_URL=http://your-url:port
   ```

3. Restart the container:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

#### What if I don't update?

The `OPENROUTER_APP_URL` variable is completely ignored now. The system will auto-detect the URL from request headers instead.

**No functionality will break** - the new auto-detection is more reliable than manual configuration.

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
