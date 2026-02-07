# Browser Addon URL Generation Fix

## Issue

When clicking "Generate Registration URL" in the Browser Addon modal, the frontend was showing an error:
**"Failed to generate URL please try again"**

## Root Cause

The `addonService.js` was using the wrong API base URL:
- **Before**: `http://localhost:8001/api/v1` (hardcoded fallback)
- **Problem**: Backend was actually running on port 8000, not 8001
- **Port 8001**: Apache web server (not our backend)

## Solution

Changed `addonService.js` to use relative URLs like the other services:
- **After**: `/api/v1` (relative URL)
- **Benefit**: Uses Vite's proxy configuration, which forwards to correct backend port

### File Changed
- `/home/philg/working/ImageTools/frontend/src/services/addonService.js` (line 6)

### Change Made
```javascript
// Before:
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';

// After:
const API_BASE_URL = '/api/v1';
```

## How It Works Now

1. Frontend makes request to `/api/v1/addon/authorize`
2. Vite dev server's proxy catches `/api/*` requests
3. Proxy forwards to backend at `http://10.0.1.97:8000` (from `.env` VITE_API_URL)
4. Backend processes request and returns authorization with registration URL
5. Frontend displays the `imagetools://authorize?code=...&instance=...` URL

## Testing

### 1. Verify Frontend Dev Server is Running
The frontend dev server should have automatically hot-reloaded the change.

If not, restart it:
```bash
cd /home/philg/working/ImageTools/frontend
npm run dev
```

### 2. Test the Browser Addon Flow

1. **Open ImageTools in Browser**: http://localhost:5173 (or your Vite dev server URL)

2. **Open Browser Addon Modal**:
   - Click settings icon (gear) in top right
   - Click "About"
   - Click "Browser Addon" button

3. **Generate Registration URL**:
   - Click "Generate Registration URL" button
   - Should now see a URL like: `imagetools://authorize?code=ABC123...&instance=http://10.0.1.97:8000`
   - No more error message!

4. **Copy and Use in Extension**:
   - Click "Copy URL" button
   - Load browser extension (see TESTING.md)
   - Paste URL in extension popup
   - Click "Connect"
   - Should successfully authenticate

### 3. Verify Backend Logs

You can check the backend logs to see the authorization request:
```bash
tail -f /tmp/backend.log
```

Look for:
```
INFO: POST /api/v1/addon/authorize
[Addon] Creating authorization for session: ...
```

## Backend Running Status

Currently running backends:
- **Port 8000**: Main backend (with INSTANCE_URL=http://10.0.1.97:8000)
- **Port 8081**: Another instance
- **Port 8001**: Apache web server (NOT our backend)

Frontend `.env` configuration:
```
VITE_API_URL=http://10.0.1.97:8000
```

This tells Vite's proxy where to forward API requests.

## Future Considerations

### For Production Deployment

In production, you'll want to set the `INSTANCE_URL` environment variable on the backend to the public URL where ImageTools is accessible:

```bash
# Example for production
export INSTANCE_URL=https://imagetools.example.com
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

This ensures the registration URL in the addon authorization response uses the correct public URL that browser extensions can reach.

### For Development with Different Ports

If you need to run the backend on a different port:

1. Update `.env` in frontend:
   ```
   VITE_API_URL=http://localhost:YOUR_PORT
   ```

2. Restart Vite dev server:
   ```bash
   npm run dev
   ```

3. Set INSTANCE_URL when starting backend:
   ```bash
   INSTANCE_URL=http://localhost:YOUR_PORT uvicorn app.main:app --host 0.0.0.0 --port YOUR_PORT
   ```

## Verification Checklist

- [x] Fixed `addonService.js` to use relative URLs
- [x] Verified Vite proxy is configured correctly
- [x] Backend is running and responding to addon endpoints
- [x] Frontend dev server is running with hot reload
- [ ] **Next**: Test in browser to confirm URL generation works
- [ ] **Next**: Test full addon connection flow
- [ ] **Next**: Test screenshot capture and upload

## Additional Notes

The fix is minimal and follows the existing pattern used by other services in the frontend. All other services (`api.js`, etc.) use relative URLs, so the addon service should too.

This ensures consistency and makes the application work correctly regardless of which port the backend is running on, as long as the Vite proxy is configured correctly.
