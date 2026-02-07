# Image Tools Android App

This Android app provides seamless image sharing integration with your Image Tools instance through secure QR code-based authentication.

## Features

- **QR Code Pairing**: Scan a QR code from the Image Tools web interface to securely link your device
- **Share Integration**: Share images from any app directly to Image Tools
- **Secure Authentication**: Uses shared secret authentication for secure image uploads
- **Upload Status**: View upload progress and success/failure notifications

## Setup Instructions

### Prerequisites

- Android Studio (latest version recommended)
- Android SDK 24+ (Android 7.0 and above)
- An instance of Image Tools running and accessible from your mobile device

### Installation

1. **Clone or Copy the Android App**
   ```bash
   cd /path/to/ImageTools/android-app
   ```

2. **Open in Android Studio**
   - Open Android Studio
   - Select "Open an Existing Project"
   - Navigate to the `android-app` directory
   - Wait for Gradle sync to complete

3. **Build and Install**
   - Connect your Android device via USB with USB debugging enabled, or use an Android emulator
   - Click "Run" in Android Studio or press `Shift + F10`
   - Select your target device

### First-Time Setup

1. **Open Image Tools Web Interface**
   - Navigate to your Image Tools instance in a web browser
   - Click the information icon (ℹ️) in the header
   - Scroll to the "Mobile App Link" section

2. **Generate QR Code**
   - The QR code will be automatically generated
   - Keep this screen open for scanning

3. **Link Your Android Device**
   - Open the Image Tools Android app
   - Tap "Scan QR Code" on the home screen
   - Grant camera permission when prompted
   - Point your camera at the QR code displayed in the web interface
   - Wait for successful pairing confirmation

4. **Start Sharing Images**
   - Open any app with images (Gallery, Photos, File Manager, etc.)
   - Select one or more images
   - Tap the Share button
   - Select "Image Tools" from the share menu
   - Images will be uploaded automatically to your linked session

## Architecture

### Technology Stack

- **Language**: Kotlin
- **UI Framework**: Jetpack Compose (Modern declarative UI)
- **Networking**: Retrofit + OkHttp
- **QR Code Scanning**: ML Kit Barcode Scanning
- **Camera**: CameraX
- **Image Loading**: Coil
- **Local Storage**: DataStore (for persisting pairing data)

### Project Structure

```
android-app/
├── build.gradle                    # App-level build configuration
├── src/
│   └── main/
│       ├── AndroidManifest.xml    # App manifest with permissions
│       ├── java/com/imagetools/mobile/
│       │   ├── MainActivity.kt     # Main app entry point
│       │   ├── ShareActivity.kt    # Handles shared images
│       │   ├── QRScannerActivity.kt # QR code scanning
│       │   ├── data/
│       │   │   ├── models/         # Data models
│       │   │   ├── repository/     # Data layer
│       │   │   └── network/        # API client
│       │   ├── ui/
│       │   │   ├── screens/        # Compose screens
│       │   │   └── components/     # Reusable UI components
│       │   └── utils/              # Utilities
│       └── res/                    # Resources (layouts, strings, etc.)
└── README.md                       # This file
```

## API Integration

### QR Code Format

The QR code contains JSON data with the following structure:

```json
{
  "instance_url": "https://your-imagetools-instance.com",
  "shared_secret": "64-character-hex-string",
  "pairing_id": "uuid-v4",
  "session_id": "uuid-v4"
}
```

### Upload Process

1. User shares image(s) from another app
2. App reads the image file(s)
3. App creates multipart/form-data request with:
   - `shared_secret`: Stored from QR code pairing
   - `file`: Image file data
4. POST request to `/api/v1/mobile/upload`
5. Backend validates shared secret and session
6. Image is uploaded to the user's session
7. App displays upload confirmation

### Endpoints Used

- `POST /api/v1/mobile/upload` - Upload image with shared secret authentication
- `POST /api/v1/mobile/validate-secret` - Validate connection (optional, for testing)

## Permissions

- **CAMERA**: Required for QR code scanning
- **INTERNET**: Required for API communication
- **READ_MEDIA_IMAGES**: Required to read shared images (Android 13+)
- **READ_EXTERNAL_STORAGE**: Required to read shared images (Android 12 and below)

## Security

- **Shared Secret**: 256-bit random secret generated server-side
- **HTTPS**: All communication should use HTTPS in production
- **Session Isolation**: Each pairing is linked to a specific session
- **Expiry**: Pairings can expire (default: 1 year)
- **No Password Storage**: App only stores the shared secret securely using DataStore

## Troubleshooting

### QR Code Won't Scan
- Ensure camera permissions are granted
- Improve lighting conditions
- Move closer/farther from the screen
- Try regenerating the QR code

### Upload Fails
- Check internet connection
- Verify the Image Tools instance is accessible from your device
- Try re-pairing by scanning a new QR code
- Check that your session hasn't expired (7 days by default)

### Can't Find "Image Tools" in Share Menu
- Ensure the app is installed and opened at least once
- Try restarting the device
- Check that the app has necessary permissions

## Development

### Building from Source

```bash
# Navigate to android-app directory
cd android-app

# Build debug APK
./gradlew assembleDebug

# Install on connected device
./gradlew installDebug

# Run tests
./gradlew test
```

### Configuration

To change the default configuration, edit the relevant files:

- **App Name**: `src/main/res/values/strings.xml`
- **Colors/Theme**: `src/main/res/values/themes.xml`
- **Minimum Android Version**: `build.gradle` (`minSdk`)

## Future Enhancements

- [ ] View uploaded images in the app
- [ ] Support for batch uploads with progress tracking
- [ ] Multiple instance support (multiple pairings)
- [ ] Image preview before upload
- [ ] Upload history
- [ ] Wi-Fi only upload option
- [ ] Custom upload quality settings

## License

This app is part of the Image Tools project. See the main project LICENSE file for details.

## Support

For issues or questions:
- Check the main Image Tools documentation
- Open an issue on the GitHub repository
- Contact the Image Tools development team
