#!/bin/bash
# Generate Android app icons from the WebApp SVG logo
# Requires: imagemagick (for 'convert' command) or inkscape

set -e

SVG_SOURCE="../frontend/public/icons/imagetools-icon.svg"
ANDROID_RES="../android-app/app/src/main/res"

# Check if source SVG exists
if [ ! -f "$SVG_SOURCE" ]; then
    echo "Error: Source SVG not found at $SVG_SOURCE"
    exit 1
fi

# Function to generate PNG from SVG
generate_png() {
    local size=$1
    local output=$2
    
    echo "Generating $output at ${size}x${size}..."
    
    # Try inkscape first (better quality)
    if command -v inkscape &> /dev/null; then
        inkscape "$SVG_SOURCE" -w "$size" -h "$size" -o "$output"
    # Fallback to ImageMagick
    elif command -v convert &> /dev/null; then
        convert -background none -resize "${size}x${size}" "$SVG_SOURCE" "$output"
    # Fallback to rsvg-convert
    elif command -v rsvg-convert &> /dev/null; then
        rsvg-convert -w "$size" -h "$size" "$SVG_SOURCE" -o "$output"
    else
        echo "Error: No SVG converter found. Please install inkscape, imagemagick, or librsvg2-bin"
        exit 1
    fi
}

# Generate mipmap icons for different densities
# mdpi (baseline): 48x48
generate_png 48 "$ANDROID_RES/mipmap-mdpi/ic_launcher.png"
generate_png 48 "$ANDROID_RES/mipmap-mdpi/ic_launcher_round.png"

# hdpi (1.5x): 72x72
generate_png 72 "$ANDROID_RES/mipmap-hdpi/ic_launcher.png"
generate_png 72 "$ANDROID_RES/mipmap-hdpi/ic_launcher_round.png"

# xhdpi (2x): 96x96
generate_png 96 "$ANDROID_RES/mipmap-xhdpi/ic_launcher.png"
generate_png 96 "$ANDROID_RES/mipmap-xhdpi/ic_launcher_round.png"

# xxhdpi (3x): 144x144
generate_png 144 "$ANDROID_RES/mipmap-xxhdpi/ic_launcher.png"
generate_png 144 "$ANDROID_RES/mipmap-xxhdpi/ic_launcher_round.png"

# xxxhdpi (4x): 192x192
generate_png 192 "$ANDROID_RES/mipmap-xxxhdpi/ic_launcher.png"
generate_png 192 "$ANDROID_RES/mipmap-xxxhdpi/ic_launcher_round.png"

echo ""
echo "✓ Android app icons generated successfully!"
echo ""
echo "Next steps:"
echo "1. Review the generated icons in $ANDROID_RES/mipmap-*/"
echo "2. Rebuild the Android app"
echo "3. The adaptive icon foreground/background in ic_launcher_foreground.xml may need updating"
