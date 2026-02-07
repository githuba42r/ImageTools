# Mobile App Testing Guide

## Quick Start

### 1. Start Development Servers
```bash
./dev-all.sh
```

This will start both backend and frontend on `0.0.0.0`, making them accessible from your network.

**URLs:**
- Local Frontend: http://localhost:5173
- Local Backend: http://localhost:8081
- Network Frontend: http://10.200.200.254:5173 (accessible from mobile)
- Network Backend: http://10.200.200.254:8081

### 2. Test on Web Browser

1. Open http://localhost:5173 (or http://10.200.200.254:5173 from another device)
2. Upload an image to create a session
3. Click the ℹ️ (info) icon in the top right
4. Click "Mobile App Link"
5. Click "📋 Copy Pairing Data" button

The pairing JSON will be copied to your clipboard. It looks like:
```json
{
  "instance_url": "http://10.200.200.254:8081",
  "shared_secret": "64-character-hex-string",
  "pairing_id": "uuid",
  "session_id": "uuid"
}
```

### 3. Connect Android App

**Transfer pairing data to your Android device:**
- Email it to yourself
- Use messaging app
- Use cloud clipboard (if available)
- Or manually type the network IP into the instance_url

**On your Android device:**

1. Open the "Image Tools" app
2. Tap "Scan QR Code"
3. You'll see a "Manual Pairing" screen
4. Paste the pairing JSON data into the text field
5. Tap "Pair"
6. You should see "Paired successfully!"

### 4. Test Image Sharing

1. Open your Gallery/Photos app on Android
2. Select an image
3. Tap Share → "Image Tools"
4. The image should upload to your web session!
5. Check the web browser - the image should appear

## Troubleshooting

### Android app can't connect to backend

**Problem:** Network connection errors

**Solutions:**
- Make sure your Android device is on the same network as your computer
- Check the `instance_url` in the pairing data uses your computer's IP (10.200.200.254), not localhost
- Make sure no firewall is blocking ports 8081 or 5173
- Test by opening http://10.200.200.254:8081/docs in your phone's browser

### QR code shows "Failed to generate"

**Problem:** Backend mobile endpoints not working

**Solution:**
- Check backend logs: `tail -f backend.log`
- Make sure you've created a session by uploading an image first
- Restart the backend if needed

### Pairing fails with "Invalid pairing data"

**Problem:** JSON format is incorrect

**Solution:**
- Make sure you copied the complete JSON (starts with `{` and ends with `}`)
- Check that there are no extra characters or line breaks
- Try copying again from the web app

## Network Configuration

### CORS Settings
The backend is configured to allow all origins (`*`) for development. In production, you should restrict this to specific origins.

**File:** `backend/app/core/config.py`
```python
CORS_ORIGINS: str = "*"  # Change in production!
```

### Network Binding
Both servers bind to `0.0.0.0` to accept connections from any network interface:

**Backend:** `--host 0.0.0.0 --port 8081`
**Frontend:** Configured in `vite.config.js` with `host: '0.0.0.0'`

## Architecture Overview

```
┌─────────────────┐
│   Web Browser   │
│  (Frontend UI)  │
└────────┬────────┘
         │ HTTP
         ↓
┌─────────────────┐
│  Vite Dev Server│
│   (port 5173)   │
└────────┬────────┘
         │ Proxy /api
         ↓
┌─────────────────┐      ┌──────────────┐
│  FastAPI Backend│←────→│   Database   │
│   (port 8081)   │      │  (SQLite)    │
└────────┬────────┘      └──────────────┘
         ↑
         │ HTTP + Shared Secret
         │
┌────────┴────────┐
│  Android App    │
│  (Mobile Device)│
└─────────────────┘
```

## Security Notes

- **Shared Secret:** Each pairing has a 256-bit (64-char hex) shared secret
- **Expiry:** Pairings expire after 365 days by default
- **Session Link:** Each pairing is linked to a specific session
- **Network:** Current setup is for development only - use HTTPS in production!

## Implementation Status

✅ **Complete:**
- Backend mobile pairing API (async SQLAlchemy)
- Frontend QR code generation with copy button
- Android app manual pairing UI
- Android app image upload via Share intent
- Network accessibility (0.0.0.0 binding)
- CORS configuration for cross-origin requests

⚠️ **Partial:**
- QR Scanner (stub only - shows manual pairing instead)

🔧 **To Implement (Optional):**
- Full CameraX + ML Kit QR scanner (code available in ANDROID_COMPLETE_IMPLEMENTATION.md)
- Push notifications when images are uploaded
- Multiple image selection in Share intent
- Pairing management UI in web app
