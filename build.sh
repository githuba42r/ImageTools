#!/bin/bash

###############################################################################
# ImageTools Build Script
#
# Builds all project assets:
# - Docker image (tagged with version and latest)
# - Android APK
# - Browser addons (Firefox & Chrome)
# - Frontend production build
#
# All artifacts are placed in /dist folder
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Parse command line arguments
BUILD_DOCKER=true
BUILD_ANDROID=true
BUILD_BROWSER=true
BUILD_FRONTEND=true
DOCKER_REGISTRY="ghcr.io/githuba42r"
SKIP_TESTS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-docker)
            BUILD_DOCKER=false
            shift
            ;;
        --skip-android)
            BUILD_ANDROID=false
            shift
            ;;
        --skip-browser)
            BUILD_BROWSER=false
            shift
            ;;
        --skip-frontend)
            BUILD_FRONTEND=false
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --registry)
            DOCKER_REGISTRY="$2"
            shift 2
            ;;
        --help)
            echo "Usage: ./build.sh [options]"
            echo ""
            echo "Options:"
            echo "  --skip-docker      Skip Docker image build"
            echo "  --skip-android     Skip Android APK build"
            echo "  --skip-browser     Skip browser addon packaging"
            echo "  --skip-frontend    Skip frontend build"
            echo "  --skip-tests       Skip running tests"
            echo "  --registry <url>   Docker registry (default: ghcr.io/githuba42r)"
            echo "  --help             Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

###############################################################################
# Read version information
###############################################################################

print_header "📋 Reading Version Information"

if [ ! -f "version.json" ]; then
    print_error "version.json not found! Run: node bump-version.js"
    exit 1
fi

VERSION=$(node -p "require('./version.json').version")
VERSION_CODE=$(node -p "require('./version.json').versionCode")
BUILD_DATE=$(node -p "require('./version.json').buildDate")

print_info "Version: $VERSION"
print_info "Version Code: $VERSION_CODE"
print_info "Build Date: $BUILD_DATE"
print_info "Docker Registry: $DOCKER_REGISTRY"

###############################################################################
# Prepare dist directory
###############################################################################

print_header "📁 Preparing Distribution Directory"

DIST_DIR="$SCRIPT_DIR/dist"
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"
mkdir -p "$DIST_DIR/logs"

print_success "Created dist directory: $DIST_DIR"

###############################################################################
# Build Frontend
###############################################################################

if [ "$BUILD_FRONTEND" = true ]; then
    print_header "🎨 Building Frontend"
    
    cd "$SCRIPT_DIR/frontend"
    
    print_info "Installing dependencies..."
    npm install --silent
    
    print_info "Building production bundle..."
    npm run build
    
    # Copy build artifacts to dist
    if [ -d "dist" ]; then
        cp -r dist "$DIST_DIR/frontend-dist"
        print_success "Frontend built successfully"
        print_info "Output: $DIST_DIR/frontend-dist/"
    else
        print_error "Frontend build failed - dist directory not found"
        exit 1
    fi
    
    cd "$SCRIPT_DIR"
fi

###############################################################################
# Build Docker Image
###############################################################################

if [ "$BUILD_DOCKER" = true ]; then
    print_header "🐳 Building Docker Image"
    
    IMAGE_NAME="imagetools"
    IMAGE_TAG_VERSIONED="${DOCKER_REGISTRY}/${IMAGE_NAME}:${VERSION}"
    IMAGE_TAG_LATEST="${DOCKER_REGISTRY}/${IMAGE_NAME}:latest"
    
    print_info "Building: $IMAGE_TAG_VERSIONED"
    print_info "Building: $IMAGE_TAG_LATEST"
    
    # Build the Docker image
    docker build \
        --build-arg VERSION="$VERSION" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        -t "$IMAGE_TAG_VERSIONED" \
        -t "$IMAGE_TAG_LATEST" \
        -f Dockerfile \
        . 2>&1 | tee "$DIST_DIR/logs/docker-build.log"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        print_success "Docker image built successfully"
        
        # Save image information
        echo "Image: $IMAGE_TAG_VERSIONED" > "$DIST_DIR/docker-image-info.txt"
        echo "Image: $IMAGE_TAG_LATEST" >> "$DIST_DIR/docker-image-info.txt"
        echo "Size: $(docker images --format "{{.Size}}" "$IMAGE_TAG_VERSIONED")" >> "$DIST_DIR/docker-image-info.txt"
        
        print_info "Image tags:"
        print_info "  - $IMAGE_TAG_VERSIONED"
        print_info "  - $IMAGE_TAG_LATEST"
        
        # Optional: Save image to tar file
        print_info "Exporting Docker image to tar archive..."
        docker save "$IMAGE_TAG_VERSIONED" | gzip > "$DIST_DIR/imagetools-${VERSION}-docker.tar.gz"
        print_success "Docker image exported to: imagetools-${VERSION}-docker.tar.gz"
    else
        print_error "Docker build failed! Check logs: $DIST_DIR/logs/docker-build.log"
        exit 1
    fi
fi

###############################################################################
# Build Android APK
###############################################################################

if [ "$BUILD_ANDROID" = true ]; then
    print_header "📱 Building Android APK"
    
    cd "$SCRIPT_DIR/android-app"
    
    # Check if gradlew exists
    if [ ! -f "gradlew" ]; then
        print_error "gradlew not found in android-app directory"
        exit 1
    fi
    
    # Make gradlew executable
    chmod +x gradlew
    
    # Clean previous builds
    print_info "Cleaning previous builds..."
    ./gradlew clean > "$DIST_DIR/logs/android-clean.log" 2>&1
    
    # Build release APK
    print_info "Building release APK..."
    ./gradlew assembleRelease 2>&1 | tee "$DIST_DIR/logs/android-build.log"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        # Find the generated APK
        APK_PATH=$(find app/build/outputs/apk/release -name "*.apk" | head -1)
        
        if [ -n "$APK_PATH" ] && [ -f "$APK_PATH" ]; then
            # Copy APK to dist with versioned filename
            APK_FILENAME="imagetools-${VERSION}-${VERSION_CODE}.apk"
            cp "$APK_PATH" "$DIST_DIR/$APK_FILENAME"
            
            # Get APK size
            APK_SIZE=$(du -h "$DIST_DIR/$APK_FILENAME" | cut -f1)
            
            print_success "Android APK built successfully"
            print_info "Output: $APK_FILENAME ($APK_SIZE)"
        else
            print_error "APK file not found after build"
            exit 1
        fi
    else
        print_error "Android build failed! Check logs: $DIST_DIR/logs/android-build.log"
        exit 1
    fi
    
    cd "$SCRIPT_DIR"
fi

###############################################################################
# Package Browser Addons
###############################################################################

if [ "$BUILD_BROWSER" = true ]; then
    print_header "🌐 Packaging Browser Addons"
    
    # Update BUILD_DATE in popup.js files
    print_info "Updating BUILD_DATE in browser addons..."
    
    for BROWSER in firefox chrome; do
        POPUP_JS="$SCRIPT_DIR/browser-addons/$BROWSER/popup.js"
        if [ -f "$POPUP_JS" ]; then
            # Update BUILD_DATE constant
            sed -i.bak "s/const BUILD_DATE = '.*';/const BUILD_DATE = '${BUILD_DATE}';/" "$POPUP_JS"
            rm "${POPUP_JS}.bak" 2>/dev/null || true
        fi
    done
    
    # Package Firefox addon
    print_info "Packaging Firefox addon..."
    cd "$SCRIPT_DIR/browser-addons/firefox"
    
    FIREFOX_ZIP="imagetools-firefox-${VERSION}.zip"
    
    # Build file list (include icons only if they exist)
    FIREFOX_FILES="manifest.json popup.html popup.js"
    if [ -f "icon16.png" ]; then
        FIREFOX_FILES="$FIREFOX_FILES icon16.png icon48.png icon128.png"
    else
        print_warning "Icon files not found, packaging without icons"
    fi
    
    zip -r "$DIST_DIR/$FIREFOX_ZIP" $FIREFOX_FILES -q
    
    FIREFOX_SIZE=$(du -h "$DIST_DIR/$FIREFOX_ZIP" | cut -f1)
    print_success "Firefox addon packaged: $FIREFOX_ZIP ($FIREFOX_SIZE)"
    
    # Package Chrome addon
    print_info "Packaging Chrome addon..."
    cd "$SCRIPT_DIR/browser-addons/chrome"
    
    CHROME_ZIP="imagetools-chrome-${VERSION}.zip"
    
    # Build file list (include icons only if they exist)
    CHROME_FILES="manifest.json popup.html popup.js"
    if [ -f "icon16.png" ]; then
        CHROME_FILES="$CHROME_FILES icon16.png icon48.png icon128.png"
    else
        print_warning "Icon files not found, packaging without icons"
    fi
    
    zip -r "$DIST_DIR/$CHROME_ZIP" $CHROME_FILES -q
    
    CHROME_SIZE=$(du -h "$DIST_DIR/$CHROME_ZIP" | cut -f1)
    print_success "Chrome addon packaged: $CHROME_ZIP ($CHROME_SIZE)"
    
    cd "$SCRIPT_DIR"
fi

###############################################################################
# Generate Build Report
###############################################################################

print_header "📊 Generating Build Report"

BUILD_REPORT="$DIST_DIR/BUILD-REPORT.txt"

cat > "$BUILD_REPORT" << EOF
ImageTools Build Report
=======================

Build Information
-----------------
Version:        $VERSION
Version Code:   $VERSION_CODE
Build Date:     $BUILD_DATE
Build Host:     $(hostname)
Build Time:     $(date)

Build Artifacts
---------------
EOF

if [ "$BUILD_DOCKER" = true ]; then
    cat >> "$BUILD_REPORT" << EOF

Docker Images:
  - ${DOCKER_REGISTRY}/imagetools:${VERSION}
  - ${DOCKER_REGISTRY}/imagetools:latest
  - Exported: imagetools-${VERSION}-docker.tar.gz
EOF
fi

if [ "$BUILD_ANDROID" = true ]; then
    APK_FILE=$(ls "$DIST_DIR"/*.apk 2>/dev/null | head -1)
    if [ -n "$APK_FILE" ]; then
        APK_SIZE=$(du -h "$APK_FILE" | cut -f1)
        APK_NAME=$(basename "$APK_FILE")
        cat >> "$BUILD_REPORT" << EOF

Android APK:
  - Filename: $APK_NAME
  - Size: $APK_SIZE
EOF
    fi
fi

if [ "$BUILD_BROWSER" = true ]; then
    cat >> "$BUILD_REPORT" << EOF

Browser Addons:
  - Firefox: imagetools-firefox-${VERSION}.zip
  - Chrome:  imagetools-chrome-${VERSION}.zip
EOF
fi

if [ "$BUILD_FRONTEND" = true ]; then
    cat >> "$BUILD_REPORT" << EOF

Frontend:
  - Build artifacts in: frontend-dist/
EOF
fi

cat >> "$BUILD_REPORT" << EOF

Build Logs
----------
Logs are available in: dist/logs/

Next Steps
----------
EOF

if [ "$BUILD_DOCKER" = true ]; then
    cat >> "$BUILD_REPORT" << EOF

1. Push Docker images:
   docker push ${DOCKER_REGISTRY}/imagetools:${VERSION}
   docker push ${DOCKER_REGISTRY}/imagetools:latest

EOF
fi

if [ "$BUILD_ANDROID" = true ]; then
    cat >> "$BUILD_REPORT" << EOF
2. Sign and publish Android APK to Google Play Store

EOF
fi

if [ "$BUILD_BROWSER" = true ]; then
    cat >> "$BUILD_REPORT" << EOF
3. Submit browser addons:
   - Firefox: https://addons.mozilla.org/developers/
   - Chrome:  https://chrome.google.com/webstore/devconsole/

EOF
fi

cat >> "$BUILD_REPORT" << EOF
4. Tag the release and push:
   git tag v${VERSION}
   git push && git push --tags

EOF

print_success "Build report generated: BUILD-REPORT.txt"

###############################################################################
# Display Summary
###############################################################################

print_header "✅ Build Complete!"

echo ""
echo "Build Artifacts Location: $DIST_DIR"
echo ""
echo "Built Artifacts:"

if [ "$BUILD_DOCKER" = true ]; then
    echo "  🐳 Docker: imagetools-${VERSION}-docker.tar.gz"
fi

if [ "$BUILD_ANDROID" = true ]; then
    APK_FILE=$(ls "$DIST_DIR"/*.apk 2>/dev/null | head -1)
    if [ -n "$APK_FILE" ]; then
        echo "  📱 Android: $(basename "$APK_FILE")"
    fi
fi

if [ "$BUILD_BROWSER" = true ]; then
    echo "  🦊 Firefox: imagetools-firefox-${VERSION}.zip"
    echo "  🌐 Chrome:  imagetools-chrome-${VERSION}.zip"
fi

if [ "$BUILD_FRONTEND" = true ]; then
    echo "  🎨 Frontend: frontend-dist/"
fi

echo ""
echo "📄 Full build report: $DIST_DIR/BUILD-REPORT.txt"
echo "📋 Build logs: $DIST_DIR/logs/"
echo ""

if [ "$BUILD_DOCKER" = true ]; then
    print_info "To push Docker images:"
    echo "  docker push ${DOCKER_REGISTRY}/imagetools:${VERSION}"
    echo "  docker push ${DOCKER_REGISTRY}/imagetools:latest"
    echo ""
fi

print_success "All builds completed successfully! 🎉"
echo ""
