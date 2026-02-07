# Mobile App Integration for Image Tools

This document describes the mobile app integration feature that allows users to easily share images from their Android devices to their Image Tools session via QR code-based authentication.

## Overview

The mobile app integration consists of three main components:

1. **Backend API** - Endpoints for mobile app pairing and authenticated image uploads
2. **Frontend QR Code** - QR code generation in the About modal for easy device linking
3. **Android App** - Native Android app with QR scanning and share integration

## Architecture

### Authentication Flow

```
1. User opens About modal in web interface
2. Backend generates a new mobile app pairing with unique shared secret
3. Frontend displays QR code containing:
   - Instance URL
   - Shared secret (256-bit random hex)
   - Pairing ID
   - Session ID
4. User scans QR code with Android app
5. App stores pairing data securely
6. User shares images from any app to Image Tools
7. App uploads images using shared secret authentication
8. Backend validates secret and links images to user's session
```

### Security Features

- **Shared Secret Authentication**: 256-bit (64-character hex) cryptographically secure random secret
- **Session Isolation**: Each pairing is linked to a specific session
- **Expiry**: Pairings expire after 365 days by default
- **Secure Storage**: Shared secrets stored securely on device using DataStore
- **No Password Required**: OAuth2-style flow without traditional user accounts

## Backend Implementation

### Database Model

New table: `mobile_app_pairings`

```python
class MobileAppPairing(Base):
    id = Column(String, primary_key=True)  # UUID
    session_id = Column(String, ForeignKey("sessions.id"))
    device_name = Column(String, nullable=True)
    shared_secret = Column(String, unique=True)  # 64-char hex
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
```

### API Endpoints

#### Mobile App Pairing

- **POST** `/api/v1/mobile/pairings`
  - Create new pairing for a session
  - Request: `{ session_id, device_name? }`
  - Response: Pairing object with generated shared_secret

- **GET** `/api/v1/mobile/pairings/qr-data/{pairing_id}`
  - Get QR code data for display
  - Response: `{ instance_url, shared_secret, pairing_id, session_id }`

- **GET** `/api/v1/mobile/pairings/session/{session_id}`
  - List all pairings for a session
  - Query: `active_only=true`

- **DELETE** `/api/v1/mobile/pairings/{pairing_id}`
  - Deactivate a pairing

- **POST** `/api/v1/mobile/pairings/session/{session_id}/revoke-all`
  - Revoke all pairings for a session

#### Image Upload

- **POST** `/api/v1/mobile/upload`
  - Upload image with shared secret auth
  - Content-Type: `multipart/form-data`
  - Fields:
    - `shared_secret`: Authentication credential
    - `file`: Image file
  - Response: Image metadata with URLs

- **POST** `/api/v1/mobile/validate-secret`
  - Test authentication without uploading
  - Body: `{ shared_secret }`
  - Response: `{ valid, pairing_id, session_id, device_name }`

### Service Layer

`MobileService` (backend/app/services/mobile_service.py):

- `generate_shared_secret()` - Create 256-bit random secret
- `create_pairing()` - Create new pairing with expiry
- `validate_shared_secret()` - Authenticate and update last_used_at
- `get_pairing_by_id()` - Retrieve pairing details
- `get_session_pairings()` - List pairings for session
- `deactivate_pairing()` - Disable a pairing
- `revoke_all_session_pairings()` - Disable all session pairings

## Frontend Implementation

### New Dependencies

Added to `frontend/package.json`:
```json
{
  "qrcode": "^1.5.3"
}
```

### QR Code Display

Location: `About Modal` in `App.vue`

Features:
- Automatic QR code generation when modal opens
- Displays QR code image (300x300px)
- Loading state during generation
- Error handling with retry button
- Regenerate QR code option
- Informational text about security

### Mobile Service

`frontend/src/services/mobileService.js`:

- `createPairing(sessionId, deviceName)` - Create new pairing
- `getQRCodeData(pairingId)` - Get data for QR code
- `getSessionPairings(sessionId, activeOnly)` - List pairings
- `deletePairing(pairingId)` - Remove pairing
- `revokeAllPairings(sessionId)` - Remove all pairings

## Android App

### Technology Stack

- **Language**: Kotlin
- **UI**: Jetpack Compose
- **Networking**: Retrofit + OkHttp
- **QR Scanner**: ML Kit Barcode Scanning
- **Camera**: CameraX
- **Image Loading**: Coil
- **Storage**: DataStore

### Key Features

1. **QR Code Scanning**
   - Uses ML Kit for fast, accurate scanning
   - Camera permission handling
   - Real-time preview

2. **Share Integration**
   - Appears in system share menu for images
   - Supports single and multiple image sharing
   - Automatic upload on share

3. **Pairing Management**
   - Secure storage of pairing data
   - Connection status indicator
   - Re-pair functionality

4. **Upload Progress**
   - Progress notifications
   - Success/error feedback
   - Retry failed uploads

### Project Structure

```
android-app/
├── build.gradle
├── src/main/
│   ├── AndroidManifest.xml
│   ├── java/com/imagetools/mobile/
│   │   ├── MainActivity.kt
│   │   ├── ShareActivity.kt
│   │   ├── data/
│   │   │   ├── models/
│   │   │   │   ├── QRCodeData.kt
│   │   │   │   └── UploadResponse.kt
│   │   │   ├── network/
│   │   │   │   ├── ImageToolsApi.kt
│   │   │   │   └── RetrofitClient.kt
│   │   │   └── repository/
│   │   │       └── PairingRepository.kt
│   │   ├── ui/
│   │   │   ├── screens/
│   │   │   │   ├── HomeScreen.kt
│   │   │   │   └── QRScannerScreen.kt
│   │   │   └── components/
│   │   │       └── UploadProgressDialog.kt
│   │   └── utils/
│   │       └── PairingPreferences.kt
│   └── res/
└── README.md
```

## User Guide

### Setting Up Mobile Integration

1. **Open Image Tools Web Interface**
   - Click the information icon (ℹ️) in the header
   - Or select "About" from the settings menu

2. **Find the QR Code**
   - Scroll to "Mobile App Link" section
   - QR code generates automatically
   - If needed, click "Generate New QR Code"

3. **Install Android App**
   - Build from source in Android Studio, or
   - Install pre-built APK (if available)

4. **Link Your Device**
   - Open Image Tools app on Android
   - Tap "Scan QR Code"
   - Grant camera permission
   - Point camera at QR code
   - Wait for "Successfully Paired" message

5. **Share Images**
   - Open any app with images
   - Select image(s) to share
   - Tap Share button
   - Choose "Image Tools"
   - Images upload automatically

### Managing Pairings

- **View Active Pairings**: GET `/api/v1/mobile/pairings/session/{session_id}`
- **Revoke Single Pairing**: Click "Remove" next to pairing
- **Revoke All Pairings**: POST to revoke-all endpoint

## Configuration

### Environment Variables

Add to `.env`:

```bash
# Mobile App Configuration
INSTANCE_URL=https://your-imagetools-instance.com
# Used in QR code for mobile app to know where to connect
```

### Pairing Expiry

Default: 365 days

Customize in `MobileService.create_pairing()`:
```python
pairing = await MobileService.create_pairing(
    db=db,
    session_id=session_id,
    device_name=device_name,
    expiry_days=365  # Change this value
)
```

## Testing

### Backend Testing

```bash
# Create pairing
curl -X POST http://localhost:8081/api/v1/mobile/pairings \
  -H "Content-Type: application/json" \
  -d '{"session_id": "your-session-id", "device_name": "Test Device"}'

# Validate secret
curl -X POST http://localhost:8081/api/v1/mobile/validate-secret \
  -H "Content-Type: application/json" \
  -d '{"shared_secret": "your-shared-secret"}'

# Upload image
curl -X POST http://localhost:8081/api/v1/mobile/upload \
  -F "shared_secret=your-shared-secret" \
  -F "file=@/path/to/image.jpg"
```

### Frontend Testing

1. Open About modal
2. Verify QR code displays
3. Check console for any errors
4. Try "Generate New QR Code" button

### Android Testing

1. Build and install app
2. Grant camera permission
3. Scan test QR code
4. Verify pairing saved
5. Test image sharing from Gallery

## Troubleshooting

### QR Code Not Generating

- Check browser console for errors
- Verify session ID exists
- Ensure backend is running
- Check network connectivity

### Upload Fails (401 Unauthorized)

- Shared secret may be invalid
- Pairing may have expired
- Session may have expired
- Re-pair device by scanning new QR code

### Upload Fails (Network Error)

- Check INSTANCE_URL is correct
- Ensure device can reach backend
- Verify CORS settings if needed
- Check firewall/network settings

### Images Not Appearing in Session

- Verify correct session is active in web interface
- Check upload was successful (200 response)
- Refresh the web page
- Check session image limit not exceeded

## Security Considerations

### Recommended Practices

1. **Use HTTPS**: Always use HTTPS in production
2. **Rotate Secrets**: Regenerate QR codes periodically
3. **Revoke Unused Pairings**: Remove old/unused pairings
4. **Monitor Usage**: Check last_used_at timestamps
5. **Set Expiry**: Use reasonable expiry times

### Attack Mitigation

- **Replay Attacks**: Each upload updates last_used_at
- **Secret Exposure**: Secrets are single-use per session
- **Session Hijacking**: Pairings tied to specific sessions
- **Brute Force**: 256-bit secrets are computationally infeasible to guess

## Future Enhancements

- [ ] iOS app
- [ ] Progressive Web App (PWA) for mobile web
- [ ] Biometric authentication on mobile
- [ ] Background sync
- [ ] Offline queue with auto-retry
- [ ] Thumbnail preview before upload
- [ ] Batch upload progress tracking
- [ ] Multiple instance support
- [ ] QR code  refresh/expiry notifications
- [ ] Upload analytics and history

## API Reference

Full API documentation available at:
- Local: `http://localhost:8081/api/v1/docs`
- Production: `https://your-instance.com/api/v1/docs`

Look for the "mobile" tag in the API documentation.

## Support

For issues or questions:
- Check logs: `backend.log` and Android logcat
- Review this documentation
- Open issue on GitHub repository
- Contact development team
