#!/bin/bash

################################################################################
# Android App Build and Deploy Script
# Builds the Image Tools Android app and deploys it to connected device via ADB
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ANDROID_STUDIO_DIR="/home/philg/Android"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANDROID_APP_DIR="${SCRIPT_DIR}/android-app"
BUILD_TYPE="${1:-debug}"  # debug or release

# Print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Check if Android Studio exists
check_android_studio() {
    print_header "Checking Android Studio Installation"
    
    if [ ! -d "$ANDROID_STUDIO_DIR" ]; then
        print_error "Android Studio directory not found at: $ANDROID_STUDIO_DIR"
        exit 1
    fi
    
    print_success "Android Studio directory found"
}

# Setup Android SDK environment variables
setup_android_sdk() {
    print_header "Setting up Android SDK Environment"
    
    # Try to find Android SDK
    if [ -d "${ANDROID_STUDIO_DIR}/Sdk" ]; then
        export ANDROID_SDK_ROOT="${ANDROID_STUDIO_DIR}/Sdk"
    elif [ -d "${HOME}/Android/Sdk" ]; then
        export ANDROID_SDK_ROOT="${HOME}/Android/Sdk"
    elif [ -d "${HOME}/.android/sdk" ]; then
        export ANDROID_SDK_ROOT="${HOME}/.android/sdk"
    else
        print_error "Android SDK not found. Please set ANDROID_SDK_ROOT manually."
        exit 1
    fi
    
    export ANDROID_HOME="$ANDROID_SDK_ROOT"
    export PATH="$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/tools:$ANDROID_SDK_ROOT/tools/bin:$PATH"
    
    print_info "ANDROID_SDK_ROOT: $ANDROID_SDK_ROOT"
    print_info "ANDROID_HOME: $ANDROID_HOME"
    print_success "Android SDK environment configured"
}

# Check if ADB is available
check_adb() {
    print_header "Checking ADB"
    
    if ! command -v adb &> /dev/null; then
        print_error "ADB not found in PATH"
        print_info "Expected location: $ANDROID_SDK_ROOT/platform-tools/adb"
        exit 1
    fi
    
    ADB_VERSION=$(adb --version | head -n 1)
    print_success "ADB found: $ADB_VERSION"
}

# Check for connected devices
check_devices() {
    print_header "Checking Connected Devices"
    
    # Start ADB server if not running
    adb start-server > /dev/null 2>&1
    
    # Get list of connected devices
    DEVICES=$(adb devices | grep -v "List" | grep "device$" | wc -l)
    
    if [ "$DEVICES" -eq 0 ]; then
        print_error "No Android devices connected"
        print_info "Please connect a device via USB and enable USB debugging"
        print_info ""
        print_info "To enable USB debugging:"
        print_info "  1. Go to Settings > About Phone"
        print_info "  2. Tap 'Build Number' 7 times to enable Developer Options"
        print_info "  3. Go to Settings > Developer Options"
        print_info "  4. Enable 'USB Debugging'"
        exit 1
    fi
    
    print_success "$DEVICES device(s) connected"
    echo ""
    adb devices -l
    echo ""
}

# Check if Gradle wrapper exists, create if not
setup_gradle() {
    print_header "Setting up Gradle"
    
    cd "$ANDROID_APP_DIR"
    
    if [ ! -f "gradlew" ]; then
        print_warning "Gradle wrapper not found, creating..."
        
        # Create gradle wrapper
        if command -v gradle &> /dev/null; then
            gradle wrapper
            print_success "Gradle wrapper created"
        else
            print_error "Gradle not found. Cannot create wrapper."
            print_info "Please install Gradle or copy gradlew from an existing Android project"
            exit 1
        fi
    else
        print_success "Gradle wrapper found"
    fi
    
    # Make gradlew executable
    chmod +x gradlew
}

# Create necessary project files if they don't exist
create_project_files() {
    print_header "Checking Project Files"
    
    cd "$ANDROID_APP_DIR"
    
    # Create settings.gradle if it doesn't exist
    if [ ! -f "settings.gradle" ]; then
        print_warning "Creating settings.gradle"
        cat > settings.gradle << 'EOF'
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "ImageTools"
include ':app'
EOF
        print_success "settings.gradle created"
    fi
    
    # Create gradle.properties if it doesn't exist
    if [ ! -f "gradle.properties" ]; then
        print_warning "Creating gradle.properties"
        cat > gradle.properties << 'EOF'
# Project-wide Gradle settings
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
org.gradle.parallel=true
org.gradle.caching=true

# Android options
android.useAndroidX=true
android.enableJetifier=true

# Kotlin code style
kotlin.code.style=official
EOF
        print_success "gradle.properties created"
    fi
    
    # Create local.properties with SDK location
    print_info "Creating local.properties with SDK location"
    echo "sdk.dir=$ANDROID_SDK_ROOT" > local.properties
    
    print_success "Project files ready"
}

# Build the Android app
build_app() {
    print_header "Building Android App ($BUILD_TYPE)"
    
    cd "$ANDROID_APP_DIR"
    
    print_info "Starting Gradle build..."
    print_info "This may take a few minutes on first run..."
    echo ""
    
    if [ "$BUILD_TYPE" = "release" ]; then
        ./gradlew assembleRelease
        APK_PATH="app/build/outputs/apk/release/app-release-unsigned.apk"
    else
        ./gradlew assembleDebug
        APK_PATH="app/build/outputs/apk/debug/app-debug.apk"
    fi
    
    if [ ! -f "$APK_PATH" ]; then
        print_error "Build failed - APK not found at $APK_PATH"
        exit 1
    fi
    
    APK_SIZE=$(du -h "$APK_PATH" | cut -f1)
    print_success "Build complete!"
    print_info "APK: $APK_PATH"
    print_info "Size: $APK_SIZE"
}

# Install the app on connected device
install_app() {
    print_header "Installing App on Device"
    
    cd "$ANDROID_APP_DIR"
    
    # Get target device (if multiple, use first one)
    DEVICE_SERIAL=$(adb devices | grep -v "List" | grep "device$" | head -n 1 | awk '{print $1}')
    
    if [ -z "$DEVICE_SERIAL" ]; then
        print_error "No device found"
        exit 1
    fi
    
    print_info "Installing on device: $DEVICE_SERIAL"
    
    # Uninstall old version if exists
    print_info "Checking for existing installation..."
    if adb -s "$DEVICE_SERIAL" shell pm list packages | grep -q "com.imagetools.mobile"; then
        print_warning "Uninstalling old version..."
        adb -s "$DEVICE_SERIAL" uninstall com.imagetools.mobile > /dev/null 2>&1 || true
    fi
    
    # Install APK
    print_info "Installing APK..."
    if adb -s "$DEVICE_SERIAL" install "$APK_PATH"; then
        print_success "App installed successfully!"
    else
        print_error "Installation failed"
        exit 1
    fi
}

# Launch the app
launch_app() {
    print_header "Launching App"
    
    DEVICE_SERIAL=$(adb devices | grep -v "List" | grep "device$" | head -n 1 | awk '{print $1}')
    
    print_info "Starting Image Tools app..."
    adb -s "$DEVICE_SERIAL" shell am start -n com.imagetools.mobile/.MainActivity
    
    print_success "App launched!"
}

# Show logcat for the app
show_logcat() {
    print_header "App Logs (Ctrl+C to exit)"
    
    DEVICE_SERIAL=$(adb devices | grep -v "List" | grep "device$" | head -n 1 | awk '{print $1}')
    
    echo ""
    print_info "Filtering logs for: com.imagetools.mobile"
    print_info "Press Ctrl+C to stop"
    echo ""
    
    # Clear logcat buffer
    adb -s "$DEVICE_SERIAL" logcat -c
    
    # Show filtered logcat
    adb -s "$DEVICE_SERIAL" logcat | grep -i "imagetools\|MainActivity\|ShareActivity"
}

# Main execution
main() {
    print_header "Image Tools Android App - Build & Deploy"
    
    print_info "Build type: $BUILD_TYPE"
    print_info "Working directory: $ANDROID_APP_DIR"
    echo ""
    
    # Check prerequisites
    check_android_studio
    setup_android_sdk
    check_adb
    check_devices
    
    # Setup project
    setup_gradle
    create_project_files
    
    # Build and install
    build_app
    install_app
    launch_app
    
    # Final summary
    print_header "Deployment Complete!"
    print_success "App successfully built and installed"
    echo ""
    print_info "Next steps:"
    print_info "  1. Open the app on your device"
    print_info "  2. Grant camera permission when prompted"
    print_info "  3. Scan QR code from Image Tools web interface"
    print_info "  4. Start sharing images!"
    echo ""
    
    # Ask if user wants to see logs
    read -p "$(echo -e ${BLUE}Would you like to view app logs? [y/N]:${NC} )" -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        show_logcat
    fi
}

# Show usage
show_usage() {
    echo "Usage: $0 [debug|release]"
    echo ""
    echo "Options:"
    echo "  debug    - Build debug APK (default)"
    echo "  release  - Build release APK (unsigned)"
    echo ""
    echo "Examples:"
    echo "  $0              # Build and install debug version"
    echo "  $0 debug        # Build and install debug version"
    echo "  $0 release      # Build and install release version"
    echo ""
}

# Handle arguments
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_usage
    exit 0
fi

if [ "$BUILD_TYPE" != "debug" ] && [ "$BUILD_TYPE" != "release" ]; then
    print_error "Invalid build type: $BUILD_TYPE"
    show_usage
    exit 1
fi

# Run main function
main
