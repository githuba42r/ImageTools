# Version Management

This document describes the version management system for ImageTools.

## Overview

ImageTools uses a centralized version management system that keeps all components synchronized:
- **Frontend** (Vue.js web app)
- **Backend** (FastAPI service)
- **Browser Extensions** (Firefox & Chrome)
- **Android App**

All components share the same version number from a central `version.json` file at the project root.

## Version File

The central version file is located at `/version.json`:

```json
{
  "version": "1.2.0",
  "buildDate": "2026-02-08T00:00:00.000Z",
  "versionCode": 3
}
```

- **version**: Semantic version (major.minor.patch[-prerelease])
- **buildDate**: ISO 8601 timestamp of when the version was bumped
- **versionCode**: Android version code (calculated as: major * 10000 + minor * 100 + patch)

## Bumping Versions

Use the `bump-version.js` script to increment versions across all components:

```bash
node bump-version.js <bump-type> [preid] [--no-commit]
```

### Bump Types

#### patch
Increment patch version (bug fixes)
```bash
node bump-version.js patch
# 1.2.0 -> 1.2.1
```

#### minor
Increment minor version (new features, backwards compatible)
```bash
node bump-version.js minor
# 1.2.0 -> 1.3.0
```

#### major
Increment major version (breaking changes)
```bash
node bump-version.js major
# 1.2.0 -> 2.0.0
```

#### prerelease
Create or increment prerelease version
```bash
node bump-version.js prerelease
# 1.2.0 -> 1.2.1-alpha.0

node bump-version.js prerelease beta
# 1.2.0 -> 1.2.1-beta.0
```

### What Gets Updated

The bump script automatically updates:

1. **version.json** - Central version file
2. **frontend/package.json** - Frontend version
3. **backend/app/main.py** - Backend API version
4. **browser-addons/firefox/manifest.json** - Firefox extension version
5. **browser-addons/chrome/manifest.json** - Chrome extension version
6. **android-app/app/build.gradle** - Android app versionName and versionCode

### Automatic Git Commit and Tag

By default, the bump script automatically:
1. Stages all version-related files
2. Creates a commit with message: `chore: bump version to X.Y.Z`
3. Creates an annotated git tag: `vX.Y.Z`

**Prerequisites:**
- Your working directory must be clean (no uncommitted changes)
- You must be in a git repository

### After Bumping

After running the bump script:

1. Review the commit: `git show`
2. Push changes: `git push`
3. Push tags: `git push --tags`
4. Or push both at once: `git push && git push --tags`

### Skip Automatic Commit

To update version files without committing:

```bash
node bump-version.js patch --no-commit
```

Then manually commit:
```bash
git diff                                    # Review changes
git add .
git commit -m "chore: bump version to X.Y.Z"
git tag vX.Y.Z
git push && git push --tags
```

## Version Display

### Backend API

The backend exposes an unprotected `/version` endpoint:

```bash
curl https://your-domain.com/version
```

Returns:
```json
{
  "version": "1.2.0",
  "buildDate": "2026-02-08T00:00:00.000Z",
  "versionCode": 3,
  "service": "ImageTools Backend API"
}
```

This endpoint:
- Is **unprotected** (bypasses authentication)
- Shows version, build date, and version code
- Useful for health checks and version verification

### Browser Extensions

Both Firefox and Chrome extensions display version information in the popup footer:

- Version number from manifest
- Build date (from `BUILD_DATE` constant in popup.js)

To verify the correct version is running:
1. Click the extension icon
2. Look at the bottom of the popup
3. You'll see: "Version: v1.2.0" and "Build: Feb 8, 2026"

### Android App

The Android app includes version information in BuildConfig:

```kotlin
BuildConfig.VERSION_NAME  // "1.2.0"
BuildConfig.VERSION_CODE  // 3
BuildConfig.BUILD_TIME    // "2026-02-08 12:34:56"
```

## Version Numbering Scheme

ImageTools follows [Semantic Versioning](https://semver.org/):

**MAJOR.MINOR.PATCH[-PRERELEASE]**

- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)
- **PRERELEASE**: Optional pre-release identifier (alpha, beta, rc)

### Android versionCode

The Android versionCode is automatically calculated:

```
versionCode = major * 10000 + minor * 100 + patch
```

Examples:
- 1.2.0 → versionCode 10200
- 1.2.1 → versionCode 10201
- 2.0.0 → versionCode 20000

This ensures proper ordering in the Play Store.

### Browser Extension Versions

Browser extensions don't support prerelease versions in manifests. The bump script automatically strips prerelease suffixes for browser manifests:

- 1.2.1-alpha.0 becomes 1.2.1 in manifest.json
- Full version (with prerelease) is still shown in the popup

## Continuous Integration

When integrating with CI/CD:

1. Run bump script in CI pipeline
2. Build all components with new version
3. Tag and push if build succeeds

Example GitHub Actions workflow:

```yaml
- name: Bump version
  run: node bump-version.js patch

- name: Build all components
  run: |
    # Build frontend
    cd frontend && npm run build && cd ..
    # Build backend
    cd backend && python -m build && cd ..
    # Build Android (if needed)
    # ...

- name: Commit and tag
  run: |
    git config user.name "CI Bot"
    git config user.email "ci@example.com"
    git add .
    git commit -m "chore: bump version [skip ci]"
    VERSION=$(node -p "require('./version.json').version")
    git tag "v${VERSION}"
    git push && git push --tags
```

## Troubleshooting

### Version mismatch between components

Run the bump script again to synchronize:
```bash
node bump-version.js patch  # Will update all components to same version
```

### Build date not updating in browser extensions

The BUILD_DATE constant in `popup.js` files needs manual update or build script automation. Consider adding a build step:

```bash
# Update BUILD_DATE before building
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
sed -i "s/const BUILD_DATE = '[^']*'/const BUILD_DATE = '${BUILD_DATE}'/" browser-addons/*/popup.js
```

### Backend not showing correct version

Make sure the backend is reading from version.json:
```bash
# Check version.json exists
ls -la version.json

# Restart backend to reload version
docker-compose restart imagetools
```

## Best Practices

1. **Always use the bump script** - Don't manually edit version numbers
2. **Bump before building** - Ensure all builds use the same version
3. **Tag releases** - Use git tags matching version numbers (v1.2.0)
4. **Document breaking changes** - Use major version bumps for API changes
5. **Test prereleases** - Use alpha/beta versions for testing before release
6. **Keep build dates accurate** - Update BUILD_DATE in addon files when building

## Related Files

- `/version.json` - Central version file
- `/bump-version.js` - Version bump script
- `/frontend/package.json` - Frontend version
- `/backend/app/main.py` - Backend version loader
- `/browser-addons/firefox/manifest.json` - Firefox version
- `/browser-addons/chrome/manifest.json` - Chrome version
- `/android-app/app/build.gradle` - Android version
