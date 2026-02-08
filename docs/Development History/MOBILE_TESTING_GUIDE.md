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
- Network Frontend: http://10.0.1.97:5173 (accessible from mobile)
- Network Backend: http://10.0.1.97:8081

**Note:** The IP address 10.200.200.254 is a machine-local address for other services. The actual network IP is 10.0.1.97

### 2. Test on Web Browser

1. Open http://localhost:5173 (or http://10.0.1.97:5173 from another device)
2. Upload an image to create a session
3. Click the ℹ️ (info) icon in the top right
4. Click "Mobile App Link"
5. Click "📋 Copy Pairing Data" button

The pairing JSON will be copied to your clipboard. It looks like:
```json
{
  "instance_url": "http://10.0.1.97:8081",
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
- Check the `instance_url` in the pairing data uses your computer's IP (10.0.1.97), not localhost
- Make sure no firewall is blocking ports 8081 or 5173
- Test by opening http://10.0.1.97:8081/docs in your phone's browser

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

### "🔗 Pair This Device" button opens app but doesn't pass parameters

**Problem:** When you tap the "🔗 Pair This Device" button in your mobile browser, the Android app launches but the pairing doesn't complete because parameters aren't being passed.

**Root Cause:** Some mobile browsers may not correctly handle deep links with multiple query parameters when clicking an `<a href="">` link. The parameters after the first `&` may get truncated.

**Current Status:**
- ✅ App code is fixed - MainActivity and HomeScreen correctly handle deep link pairing
- ✅ Deep link format is correct and tested via ADB
- ❌ Mobile browser may truncate URL parameters when clicking the link

**How to Debug:**
1. Open the web app on your Android device: http://10.0.1.97:5173
2. Upload an image to create a session
3. Tap ℹ️ → "Mobile App Link"  
4. Open browser DevTools/Console (Chrome: Menu → More Tools → Developer Tools)
5. Look for the console log that says "Generated pairing deep link: imagetools://pair/..."
6. Copy that full URL
7. Tap "🔗 Pair This Device" button
8. Check Android logs to see what was actually received:
   ```bash
   adb logcat MainActivity:D HomeScreen:D *:S
   ```

**Expected Deep Link Format:**
```
imagetools://pair/link?url=http%3A%2F%2F10.0.1.97%3A8081&secret=<64-char-hex>&pairing_id=<uuid>&session_id=<uuid>
```

**If Parameters Are Missing:**
The browser is truncating the URL. Use one of these workarounds:

**Workaround 1: Manual JSON Pairing (Most Reliable)**
1. Tap "📋 Copy Pairing Data" instead
2. Open Image Tools app
3. Tap "Scan QR Code"
4. Paste the JSON into the text field
5. Tap "Pair"

**Workaround 2: Test with ADB (For Development)**
```bash
# Get the pairing data from web UI
# Then run:
adb shell am start -a android.intent.action.VIEW -d "'imagetools://pair/link?url=http%3A%2F%2F10.0.1.97%3A8081&secret=YOUR_SECRET&pairing_id=YOUR_ID&session_id=YOUR_SESSION'"
```

**Possible Browser-Specific Solutions:**
- Try a different browser (Firefox, Samsung Internet, etc.)
- Try copying the link and pasting it in the address bar
- Use the QR code method once the scanner is implemented

### Manual pairing from web app opened on Android device

**Important:** The pairing system is designed to work across **two separate devices**:
- **Device 1 (Desktop/Laptop)**: Runs the web app, creates session, displays images
- **Device 2 (Android Phone)**: Runs the mobile app, uploads images to the session

**Same-Device Pairing (Opening web app on Android device):**

With the fix applied above, you CAN now use the "🔗 Pair This Device" button to pair when accessing the web app from your Android device's browser. However, this creates a scenario where:
- The web session runs in your Android browser
- The mobile app uploads images to that same Android device
- This works functionally but may not be the intended use case

**Why Two Devices is Recommended:**
The typical workflow is:
1. **Desktop**: Open web app, create session, view images on large screen
2. **Mobile**: Share images from Gallery → automatically appear on desktop

Having the session on your desktop while using your phone to upload is the more practical workflow.

**Testing with Same Device:**
If you need to test with only one device:
1. Open http://10.0.1.97:5173 in Android Chrome
2. Upload an image to create a session  
3. Tap ℹ️ → "Mobile App Link" → "🔗 Pair This Device"
4. The Image Tools app should open and pair automatically
5. Go to Gallery → Share an image → Image Tools
6. Return to Chrome - the image should appear in the session

**Alternative Testing Methods:**
- Use Android emulator on your desktop
- Use the backend test page: http://10.0.1.97:8081/test-pairing.html
- Test with manual API calls using curl (see MOBILE_APP_INTEGRATION.md)

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
