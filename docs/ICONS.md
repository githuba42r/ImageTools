# Icon and Logo Management

## Overview

ImageTools uses a unified icon across all platforms:
- **Web App**: SVG logo in the title bar
- **Android App**: Adaptive launcher icons
- **Browser Addons**: Multiple sizes (16, 32, 48, 128px)

## Source Icon

The master icon is located at:
```
frontend/public/icons/imagetools-icon.svg
```

This SVG features:
- Purple/indigo gradient background
- Picture frame with landscape image
- Red tool/wrench icon in the corner
- Clean, modern design suitable for all platforms

## Generating Android App Icons

### Prerequisites

Install one of the following SVG converters:

```bash
# Option 1: Inkscape (recommended for best quality)
sudo apt install inkscape

# Option 2: ImageMagick
sudo apt install imagemagick

# Option 3: librsvg2-bin
sudo apt install librsvg2-bin
```

### Generation Script

Run the icon generation script:

```bash
cd scripts
./generate-android-icons.sh
```

This will generate icons for all Android densities:
- `mipmap-mdpi`: 48x48 (baseline)
- `mipmap-hdpi`: 72x72 (1.5x)
- `mipmap-xhdpi`: 96x96 (2x)
- `mipmap-xxhdpi`: 144x144 (3x)
- `mipmap-xxxhdpi`: 192x192 (4x)

### Manual Generation

If the script doesn't work, you can manually generate icons:

```bash
# Using Inkscape
inkscape frontend/public/icons/imagetools-icon.svg -w 192 -h 192 \
  -o android-app/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png

# Using ImageMagick
convert -background none -resize 192x192 \
  frontend/public/icons/imagetools-icon.svg \
  android-app/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png

# Using rsvg-convert
rsvg-convert -w 192 -h 192 \
  frontend/public/icons/imagetools-icon.svg \
  -o android-app/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png
```

## Browser Addon Icons

Browser addon icons are already generated and located at:

**Chrome/Chromium:**
```
browser-addons/chrome/icons/
├── icon-16.png   (toolbar icon)
├── icon-32.png   (retina toolbar)
├── icon-48.png   (extension management)
└── icon-128.png  (Chrome Web Store)
```

**Firefox:**
```
browser-addons/firefox/icons/
├── icon-16.png   (toolbar icon)
├── icon-48.png   (extension management)
├── icon-96.png   (high-DPI extension management)
└── icon-128.png  (AMO listing)
```

To regenerate browser addon icons from the SVG:

```bash
# 16x16
inkscape frontend/public/icons/imagetools-icon.svg -w 16 -h 16 \
  -o browser-addons/chrome/icons/icon-16.png

# 32x32
inkscape frontend/public/icons/imagetools-icon.svg -w 32 -h 32 \
  -o browser-addons/chrome/icons/icon-32.png

# 48x48
inkscape frontend/public/icons/imagetools-icon.svg -w 48 -h 48 \
  -o browser-addons/chrome/icons/icon-48.png

# 128x128
inkscape frontend/public/icons/imagetools-icon.svg -w 128 -h 128 \
  -o browser-addons/chrome/icons/icon-128.png
```

Copy the same icons to Firefox addon directory.

## Adaptive Icons (Android)

Android adaptive icons use:
- **Foreground**: The main icon content (defined in `ic_launcher_foreground.xml`)
- **Background**: Solid color or gradient (defined in `ic_launcher_background.xml`)

The current setup uses bitmap icons. For a true adaptive icon experience, consider:
1. Converting the SVG to a vector drawable for the foreground layer
2. Using the gradient from the SVG as the background layer

## Testing Icons

### Android
1. Build and install the app: `./gradlew installDebug`
2. Check the launcher icon on your device
3. Long-press to view the adaptive icon behavior

### Browser Addons
1. Load the extension in your browser
2. Check the toolbar icon (16x16/32x32)
3. Check the extension management page (48x48)

## Icon Design Guidelines

When modifying the source icon:

1. **Keep it simple**: Icons should be recognizable at small sizes (16x16)
2. **High contrast**: Ensure good visibility on light and dark backgrounds
3. **Square safe area**: Keep important elements within the center 80% (for adaptive icons)
4. **No text**: Avoid text as it becomes unreadable at small sizes
5. **Distinct silhouette**: The icon should be recognizable from its outline alone

## Troubleshooting

### Icons not updating on Android
- Clean and rebuild: `./gradlew clean assembleDebug`
- Uninstall and reinstall the app
- Clear launcher cache (device-specific)

### Blurry icons
- Ensure you're generating at the correct DPI for each density
- Use Inkscape for better SVG rendering quality
- Check that the source SVG is at least 512x512 viewBox

### Browser addon icons not showing
- Check manifest.json has correct icon paths
- Ensure PNG files are not corrupted (run `file icon-*.png`)
- Reload the extension after icon changes
