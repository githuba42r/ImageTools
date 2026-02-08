# Building ImageTools

This document describes how to build all ImageTools components for release.

## Prerequisites

### Required Tools

- **Node.js** (v18+) - For version management
- **Docker** - For building container images (includes frontend build)
- **Java JDK** (v11+) - For Android builds
- **Android SDK** - For Android APK compilation
- **zip** - For packaging browser addons

### Environment Setup

```bash
# Set ANDROID_HOME environment variable
export ANDROID_HOME=/path/to/android-sdk
```

Note: Frontend dependencies are installed automatically during the Docker build process.

## Build Process

### 1. Bump Version (Optional)

If creating a new release, first bump the version:

```bash
# Bump version (automatically commits and tags)
node bump-version.js patch   # or minor, major, prerelease

# This updates all component versions and creates:
# - Git commit: "chore: bump version to X.Y.Z"
# - Git tag: "vX.Y.Z"
```

### 2. Run Build Script

Build all components:

```bash
./build.sh
```

This will create the following artifacts in `/dist`:

- **Docker Image**: Tagged as `ghcr.io/githuba42r/imagetools:1.2.2` and `:latest` (includes built frontend)
- **Android APK**: `imagetools-1.2.2-10202.apk`
- **Firefox Addon**: `imagetools-firefox-1.2.2.zip`
- **Chrome Addon**: `imagetools-chrome-1.2.2.zip`
- **Build Report**: `BUILD-REPORT.txt`
- **Docker Image Info**: `docker-image-info.txt`

### 3. Selective Builds

Build only specific components:

```bash
# Build only browser addons
./build.sh --skip-docker --skip-android

# Build only Docker image (includes frontend)
./build.sh --skip-android --skip-browser

# Build only Android APK
./build.sh --skip-docker --skip-browser
```

### 4. Custom Docker Registry

Specify a different Docker registry:

```bash
./build.sh --registry ghcr.io/myorg
```

This will tag images as:
- `ghcr.io/myorg/imagetools:1.2.2`
- `ghcr.io/myorg/imagetools:latest`

## Build Output

All build artifacts are placed in `/dist`:

```
dist/
├── BUILD-REPORT.txt                    # Summary of build
├── docker-image-info.txt               # Docker image details (tags, size, version)
├── imagetools-1.2.2-10202.apk          # Android APK
├── imagetools-firefox-1.2.2.zip        # Firefox addon
├── imagetools-chrome-1.2.2.zip         # Chrome addon
└── logs/                               # Build logs
    ├── docker-build.log
    ├── android-build.log
    └── android-clean.log
```

Note: The Docker image contains the built frontend - no separate frontend artifacts are generated.

## Publishing Releases

### 1. Push Docker Images

```bash
# Push versioned image
docker push ghcr.io/githuba42r/imagetools:1.2.2

# Push latest tag
docker push ghcr.io/githuba42r/imagetools:latest
```

The Docker image includes the built frontend, so no separate deployment is needed for the web app.

### 2. Publish Android APK

The APK in `/dist` is an unsigned release build. To publish to Google Play:

1. Sign the APK with your release keystore
2. Upload to Google Play Console
3. Follow Google's release process

### 3. Submit Browser Addons

#### Firefox

1. Go to https://addons.mozilla.org/developers/
2. Upload `dist/imagetools-firefox-1.2.2.zip`
3. Fill in release notes and submit for review

#### Chrome

1. Go to https://chrome.google.com/webstore/devconsole/
2. Upload `dist/imagetools-chrome-1.2.2.zip`
3. Fill in release notes and submit for review

### 4. Push Git Tags

```bash
# Push commits and tags
git push && git push --tags

# Or if you didn't use bump-version.js:
git tag v1.2.2
git push origin v1.2.2
```

### 5. Create GitHub Release

```bash
# Using GitHub CLI
gh release create v1.2.2 \
  --title "ImageTools v1.2.2" \
  --notes "Release notes here" \
  dist/imagetools-1.2.2-10202.apk \
  dist/imagetools-firefox-1.2.2.zip \
  dist/imagetools-chrome-1.2.2.zip
```

Note: Docker images are pushed to the container registry (not included in GitHub releases).

## Build Script Options

```
Usage: ./build.sh [options]

Options:
  --skip-docker      Skip Docker image build (includes frontend)
  --skip-android     Skip Android APK build
  --skip-browser     Skip browser addon packaging
  --registry <url>   Docker registry (default: ghcr.io/githuba42r)
  --help             Show this help message
```

## Troubleshooting

### Android Build Fails

**Problem**: `ANDROID_HOME not set`

**Solution**:
```bash
export ANDROID_HOME=/path/to/android-sdk
```

### Docker Build Fails

**Problem**: `permission denied while trying to connect to Docker daemon`

**Solution**:
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

### Frontend Build Fails

**Problem**: `npm install fails with dependency errors`

**Solution**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
cd ..
```

## CI/CD Integration

The build script is designed to work in CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Build all components
  run: |
    node bump-version.js patch --no-commit
    ./build.sh
    
- name: Upload artifacts
  uses: actions/upload-artifact@v3
  with:
    name: build-artifacts
    path: dist/
```

## Version Management

All component versions are synchronized via `version.json`. The build script automatically reads this file to:

- Tag Docker images with the correct version
- Name APK files with version and version code
- Name browser addon zips with version
- Update BUILD_DATE in browser addon source files

See [VERSION_MANAGEMENT.md](docs/VERSION_MANAGEMENT.md) for details on version management.
