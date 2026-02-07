# Android App Build & Deploy - Quick Start Guide

This guide helps you build and deploy the Image Tools Android app to your device.

## Prerequisites

✅ **Already Installed:**
- Android Studio at `/home/philg/Android/`

✅ **Required:**
- Android device with USB debugging enabled
- USB cable to connect device to computer

## Step 1: Enable USB Debugging on Your Android Device

If you haven't enabled USB debugging yet:

1. Open **Settings** on your Android device
2. Scroll to **About Phone** (or **About Device**)
3. Tap **Build Number** 7 times (you'll see "You are now a developer!")
4. Go back to **Settings** > **Developer Options**
5. Enable **USB Debugging**
6. Connect your device via USB
7. Accept the "Allow USB Debugging" prompt on your device

## Step 2: Connect Your Device

```bash
# Connect your Android device via USB
# Check if it's detected
/home/philg/Android/Sdk/platform-tools/adb devices
```

You should see your device listed. If not, check the USB connection and USB debugging setting.

## Step 3: Build and Deploy

The easiest way is to use the build script:

```bash
# Navigate to the project root
cd /home/philg/working/ImageTools

# Run the build script (debug build)
./build-android.sh

# Or for release build
./build-android.sh release
```

### What the Script Does:

1. ✓ Checks Android Studio installation
2. ✓ Sets up Android SDK environment
3. ✓ Verifies ADB is available
4. ✓ Checks for connected devices
5. ✓ Sets up Gradle wrapper
6. ✓ Creates necessary project files
7. ✓ Builds the APK
8. ✓ Installs on device
9. ✓ Launches the app
10. ✓ Optionally shows logs

## Step 4: Manual Build (Alternative)

If you prefer to build manually with Android Studio:

### Option A: Using Android Studio GUI

1. **Open Project**
   ```bash
   /home/philg/Android/android-studio/bin/studio.sh
   ```
   - Click "Open"
   - Navigate to `/home/philg/working/ImageTools/android-app`
   - Click "OK"

2. **Wait for Gradle Sync**
   - Android Studio will automatically sync Gradle
   - This may take a few minutes on first run

3. **Connect Device**
   - Connect your Android device via USB
   - Device should appear in the device dropdown at the top

4. **Build and Run**
   - Click the green "Run" button (▶️) or press `Shift + F10`
   - Select your device
   - App will build and install automatically

### Option B: Using Command Line

```bash
cd /home/philg/working/ImageTools/android-app

# Set up environment
export ANDROID_SDK_ROOT=/home/philg/Android/Sdk
export PATH=$ANDROID_SDK_ROOT/platform-tools:$PATH

# Build debug APK
./gradlew assembleDebug

# Install to device
adb install app/build/outputs/apk/debug/app-debug.apk

# Launch app
adb shell am start -n com.imagetools.mobile/.MainActivity
```

## Step 5: First-Time Setup in the App

Once the app is installed and launched:

1. **Grant Camera Permission**
   - App will request camera permission
   - Tap "Allow" to enable QR code scanning

2. **Scan QR Code**
   - Open Image Tools in your web browser
   - Click the info icon (ℹ️) in the header
   - Scroll to "Mobile App Link" section
   - In the Android app, tap "Scan QR Code"
   - Point camera at the QR code on screen
   - Wait for "Successfully Paired" message

3. **Test Sharing**
   - Open Gallery or Photos app
   - Select an image
   - Tap the Share button
   - Choose "Image Tools"
   - Image uploads automatically!

## Troubleshooting

### Device Not Detected

**Problem:** `adb devices` shows no devices or "unauthorized"

**Solutions:**
```bash
# Restart ADB server
adb kill-server
adb start-server

# Check devices again
adb devices
```

- Unplug and replug USB cable
- Try a different USB port
- Check if USB debugging is still enabled
- Accept the authorization prompt on device
- Try a different USB cable (data cable, not charge-only)

### Build Fails

**Problem:** Gradle sync or build fails

**Solutions:**

1. **Clear Gradle cache**
   ```bash
   cd android-app
   ./gradlew clean
   ```

2. **Update Gradle wrapper** (if needed)
   ```bash
   ./gradlew wrapper --gradle-version=8.2
   ```

3. **Check Java version**
   ```bash
   java -version
   # Should be Java 11 or higher
   ```

4. **Invalidate Android Studio caches**
   - File > Invalidate Caches > Invalidate and Restart

### Installation Fails

**Problem:** APK won't install on device

**Solutions:**

1. **Uninstall old version**
   ```bash
   adb uninstall com.imagetools.mobile
   ```

2. **Check device storage**
   - Ensure device has enough free space

3. **Try installing manually**
   ```bash
   adb install -r app/build/outputs/apk/debug/app-debug.apk
   # -r flag reinstalls/replaces existing app
   ```

### QR Code Won't Scan

**Problem:** Camera opens but QR code doesn't scan

**Solutions:**
- Improve lighting
- Move device closer/farther from screen
- Make sure QR code is fully visible
- Try regenerating QR code in web interface
- Check camera permission is granted
- Restart the app

### Upload Fails

**Problem:** Images shared to app don't upload

**Solutions:**

1. **Check connection**
   ```bash
   # Test if device can reach server
   adb shell ping -c 3 your-imagetools-server.com
   ```

2. **Check pairing**
   - Re-pair device by scanning QR code again

3. **View app logs**
   ```bash
   adb logcat | grep -i "imagetools"
   ```

4. **Check permissions**
   - Settings > Apps > Image Tools > Permissions
   - Ensure "Files and media" or "Storage" is allowed

## Viewing Logs

To see what's happening in the app:

```bash
# Clear log buffer
adb logcat -c

# View filtered logs
adb logcat | grep -i "imagetools\|MainActivity\|ShareActivity"

# Or use the build script
./build-android.sh debug
# Then answer 'y' when asked to view logs
```

## Development Tips

### Fast Iteration

For quick testing during development:

```bash
# Build and install in one command
cd android-app
./gradlew installDebug

# Or build only (without installing)
./gradlew assembleDebug
```

### Debug Mode Features

Debug builds include:
- More detailed logging
- Stacktrace on errors
- Debug symbols for troubleshooting
- No code obfuscation

### Release Mode

For production release:

```bash
./build-android.sh release
```

Note: Release APKs are unsigned. For production, you'll need to:
1. Generate a signing key
2. Configure signing in `build.gradle`
3. Sign the APK

## Environment Variables

The build script automatically sets these:

```bash
ANDROID_SDK_ROOT=/home/philg/Android/Sdk
ANDROID_HOME=/home/philg/Android/Sdk
PATH=$ANDROID_SDK_ROOT/platform-tools:$PATH
```

You can add these to your `~/.bashrc` or `~/.zshrc` for permanent setup:

```bash
echo 'export ANDROID_SDK_ROOT=/home/philg/Android/Sdk' >> ~/.bashrc
echo 'export ANDROID_HOME=$ANDROID_SDK_ROOT' >> ~/.bashrc
echo 'export PATH=$ANDROID_SDK_ROOT/platform-tools:$PATH' >> ~/.bashrc
source ~/.bashrc
```

## Next Steps

After successful deployment:

1. ✅ Test QR code scanning
2. ✅ Test image sharing from Gallery
3. ✅ Verify images appear in web interface
4. ✅ Test with multiple images
5. ✅ Test with different image formats

## Additional Resources

- **Android App README**: `android-app/README.md`
- **Integration Guide**: `MOBILE_APP_INTEGRATION.md`
- **Main Documentation**: `README.md`

## Getting Help

If you encounter issues:

1. Check the logs: `adb logcat`
2. Review this troubleshooting guide
3. Check the main documentation
4. Open an issue on GitHub

## Quick Reference Commands

```bash
# Check connected devices
adb devices

# Build debug APK
./build-android.sh

# Build release APK
./build-android.sh release

# Install APK manually
adb install path/to/app.apk

# Uninstall app
adb uninstall com.imagetools.mobile

# View logs
adb logcat | grep imagetools

# Launch app
adb shell am start -n com.imagetools.mobile/.MainActivity

# Restart ADB
adb kill-server && adb start-server

# Take screenshot from device
adb shell screencap -p /sdcard/screenshot.png
adb pull /sdcard/screenshot.png
```

---

**Ready to build?** Just run:

```bash
cd /home/philg/working/ImageTools
./build-android.sh
```

Good luck! 🚀
