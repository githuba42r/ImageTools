# ImageTools User Guide

Welcome to ImageTools! This guide will help you quickly compress, edit, and optimize your images for email and web use.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Uploading Images](#uploading-images)
3. [Compression Presets](#compression-presets)
4. [Image Editing](#image-editing)
5. [AI Features](#ai-features)
6. [Downloading and Exporting](#downloading-and-exporting)
7. [Mobile App Integration](#mobile-app-integration)
8. [Browser Extension](#browser-extension)
9. [Tips and Tricks](#tips-and-tricks)
10. [Troubleshooting](#troubleshooting)

## Getting Started

### Accessing ImageTools

1. Open your web browser
2. Navigate to your ImageTools instance (e.g., http://localhost:8082 for local installations)
3. You'll see the main interface with an upload area

### Interface Overview

- **Upload Area**: Drag and drop images or click to browse
- **Image Gallery**: View all uploaded images with thumbnails
- **Toolbar**: Quick actions for selected images
- **Image Card Controls**: Edit, compress, remove background, chat with AI

## Uploading Images

### Method 1: Drag and Drop

1. Drag one or more images from your file explorer
2. Drop them onto the upload area
3. Images will automatically appear in the gallery

### Method 2: Click to Browse

1. Click the "Upload Images" button or click anywhere in the upload area
2. Select one or more images from the file picker
3. Click "Open" to upload

### Method 3: Mobile App (Android)

1. Pair your Android device (see [Mobile App Integration](#mobile-app-integration))
2. Share images from any app to ImageTools
3. Images appear automatically in the web interface

### Method 4: Browser Extension

1. Install the browser extension (see [Browser Extension](#browser-extension))
2. Capture screenshots directly from any webpage
3. Screenshots upload automatically to ImageTools

### Supported Formats

- JPEG/JPG
- PNG
- WebP
- GIF
- BMP
- TIFF

### Upload Limits

- Maximum file size: 20 MB per image (configurable by administrator)
- Maximum images per session: 5 images at once (configurable by administrator)
- Images are automatically deleted after 7 days (configurable by administrator)

## Compression Presets

Quickly optimize images for different use cases with one-click presets.

### Available Presets

#### Email Preset
- **Best for**: Attaching images to emails
- **Output**: 800x600 pixels, 85% quality
- **Typical file size**: 100-300 KB
- **Use when**: You need to send photos via email without hitting attachment limits

#### Web Preset
- **Best for**: Website content, blog posts
- **Output**: 1200x900 pixels, 80% quality
- **Typical file size**: 200-500 KB
- **Use when**: Optimizing images for web pages to improve load times

#### Thumbnail Preset
- **Best for**: Profile pictures, small icons
- **Output**: 200x200 pixels, 75% quality
- **Typical file size**: 20-50 KB
- **Use when**: Creating small preview images

#### Custom Preset
- **Best for**: Specific requirements
- **Options**: Choose your own dimensions, quality, and format
- **Use when**: You need precise control over output

### How to Use Presets

#### Single Image

1. Find the image in the gallery
2. Click the preset button (Email, Web, or Thumbnail)
3. Watch the compression progress
4. See before/after comparison and compression ratio
5. Click "Undo" if you want to revert

#### Multiple Images (Bulk)

1. Select multiple images using the checkboxes
2. Click the toolbar preset button at the top
3. All selected images compress simultaneously
4. Individual results shown on each image card

### Understanding Compression Results

After compression, you'll see:
- **Before**: Original file size
- **After**: Compressed file size
- **Saved**: Percentage reduction
- **Ratio**: Compression ratio (e.g., 4:1 means 75% smaller)

Example: "1.2 MB → 300 KB (75% saved, 4:1 ratio)"

## Image Editing

ImageTools includes a powerful built-in image editor powered by TUI Image Editor.

### Opening the Editor

1. Find your image in the gallery
2. Click the "Edit" button (pencil icon)
3. The editor opens in a modal window

### Editor Features

#### Crop
- Select predefined aspect ratios (1:1, 4:3, 16:9, free)
- Drag corners to adjust crop area
- Apply to crop the image

#### Flip & Rotate
- Flip horizontal or vertical
- Rotate 90° left or right
- Free rotation with angle slider

#### Draw
- Freehand drawing
- Adjustable brush size and color
- Straight lines

#### Text
- Add text overlays
- Choose font, size, and color
- Position anywhere on the image
- Bold, italic, underline options

#### Shapes
- Rectangle
- Circle
- Triangle
- Custom shapes
- Fill or outline styles

#### Filters
- Grayscale
- Sepia
- Blur
- Sharpen
- Emboss
- Remove White
- Custom color adjustments

#### Image Adjustments
- Brightness
- Contrast
- Saturation
- Exposure
- Hue rotation

### Saving Edits

1. Make your changes in the editor
2. Click "Apply" or "Save" button
3. The editor closes and updates the image
4. Original is preserved - use "Undo" to revert

### Undoing Edits

- Click the "Undo" button on the image card
- This reverts to the previous version
- Multiple undo levels supported

## AI Features

AI-powered features require connecting your OpenRouter account.

### Connecting to OpenRouter

1. Click the information icon (ℹ️) in the top-right
2. Navigate to "AI Settings"
3. Click "Connect OpenRouter"
4. Log in to your OpenRouter account
5. Authorize ImageTools
6. You're now connected!

**Note**: You'll need an OpenRouter account with API credits. Sign up at [openrouter.ai](https://openrouter.ai)

### Background Removal

Remove backgrounds automatically using AI.

1. Upload an image with a subject (person, product, etc.)
2. Click "Remove Background" button
3. AI processes the image (5-15 seconds)
4. Background is removed, leaving transparent background
5. Click "Undo" to restore original

**Tips**:
- Works best with clear subjects
- High-contrast subjects give best results
- May take longer for complex images

### AI Chat Interface

Have a conversation with AI about your images using natural language.

#### Opening AI Chat

1. Click the "Chat" button (speech bubble icon) on any image
2. Chat panel opens on the right side
3. Your image is shown in the chat context

#### What You Can Ask

**Image Analysis**:
- "What's in this image?"
- "Describe this photo in detail"
- "What colors are dominant?"

**Image Editing Suggestions**:
- "How can I make this image better?"
- "Suggest improvements for composition"
- "What filter would work well here?"

**Technical Questions**:
- "What resolution should I use for Instagram?"
- "How much should I compress for email?"
- "What's the best format for this image?"

**Creative Ideas**:
- "Give me ideas for similar photos"
- "What style is this photo?"
- "How could I edit this for a vintage look?"

#### Chat Tips

- Be specific in your questions
- You can ask follow-up questions
- AI remembers the conversation context
- Click "Clear Chat" to start fresh

### AI Model Selection

1. Open Settings (ℹ️ icon)
2. Go to "AI Models"
3. Choose from available models:
   - **GPT-4**: Best quality, slower, more expensive
   - **GPT-3.5**: Good balance, faster, cheaper
   - **Claude**: Great for detailed analysis
   - And others...
4. Your selection is saved automatically

**Cost Note**: Different models have different costs per request. Check OpenRouter pricing.

## Downloading and Exporting

### Download Single Image

1. Click the "Download" button on any image card
2. Image downloads to your default downloads folder
3. Filename includes modification timestamp

### Copy to Clipboard

1. Click "Copy" button on image card
2. Image is copied to your clipboard
3. Paste directly into emails, documents, or chat applications

**Browser Support**: Works in modern browsers (Chrome, Firefox, Edge, Safari 13.1+)

### Bulk Download as ZIP

1. Select multiple images using checkboxes
2. Click "Download Selected as ZIP" in the toolbar
3. All selected images are packaged into a ZIP file
4. ZIP file downloads automatically

**ZIP Contents**:
- All selected images in their current state
- Preserves filenames
- Maintains image formats

### Download Formats

Images are downloaded in their current format:
- JPEG for compressed/edited photos
- PNG for images with transparency
- Original format preserved when possible

## Mobile App Integration

Share images seamlessly from your Android device to ImageTools.

### First-Time Setup

#### Step 1: Install the Android App

- Download from Google Play Store (coming soon)
- Or install manually (see [android-app/README.md](android-app/README.md))

#### Step 2: Generate QR Code

1. Open ImageTools web interface
2. Click the information icon (ℹ️)
3. Scroll to "Mobile App Link"
4. QR code is automatically displayed

#### Step 3: Pair Your Device

1. Open ImageTools Android app
2. Tap "Scan QR Code"
3. Grant camera permission if prompted
4. Point camera at QR code on screen
5. Wait for "Pairing successful" message

### Using the Mobile App

#### Sharing Images from Gallery

1. Open your Photos/Gallery app
2. Select one or more images
3. Tap the Share button
4. Choose "ImageTools" from the share menu
5. Images upload automatically
6. View them instantly in the web interface

#### Sharing from Camera

1. Take a photo with your camera app
2. Tap the Share button immediately
3. Choose "ImageTools"
4. Photo uploads and appears in web interface

#### Sharing from Other Apps

Works with any app that has a share function:
- File managers
- Social media apps (save then share)
- Cloud storage apps
- Messaging apps

### Mobile App Tips

- Images upload in the background
- You'll see a notification when upload completes
- Works on Wi-Fi and mobile data
- Large images may take longer to upload
- Pairing lasts 1 year before re-pairing needed

### Troubleshooting Mobile App

**Can't find ImageTools in share menu**:
- Ensure app is installed and opened at least once
- Try restarting your device

**Upload fails**:
- Check internet connection
- Verify ImageTools server is accessible
- Try re-pairing with new QR code

**QR code won't scan**:
- Improve lighting
- Move closer/farther from screen
- Clean camera lens
- Try regenerating QR code

## Browser Extension

Capture screenshots and send them directly to ImageTools.

### Installing the Extension

#### Chrome/Edge

1. Visit Chrome Web Store (link coming soon)
2. Click "Add to Chrome"
3. Confirm installation
4. Extension icon appears in toolbar

#### Firefox

1. Visit Firefox Add-ons (link coming soon)
2. Click "Add to Firefox"
3. Confirm installation
4. Extension icon appears in toolbar

#### Manual Installation (Developers)

See [browser-addons/README.md](browser-addons/README.md)

### First-Time Setup

#### Step 1: Generate Registration URL

1. Open ImageTools web interface
2. Click the information icon (ℹ️)
3. Navigate to "Browser Addon"
4. Click "Generate Registration URL"
5. Copy the URL that appears

#### Step 2: Connect Extension

1. Click the ImageTools extension icon
2. Paste the registration URL
3. Click "Connect"
4. Wait for "Connected successfully" message

### Capturing Screenshots

#### Method 1: Extension Icon

1. Click the ImageTools extension icon
2. Choose capture mode:
   - **Visible Area**: Current viewport only
   - **Full Page**: Entire scrolling page
   - **Selected Region**: Draw a selection box
3. Screenshot is captured and uploaded automatically
4. Check ImageTools web interface to see the image

#### Method 2: Context Menu

1. Right-click anywhere on a webpage
2. Hover over "ImageTools"
3. Select capture mode from submenu
4. Screenshot uploads automatically

#### Method 3: Keyboard Shortcuts (if configured)

- `Ctrl+Shift+S`: Capture visible area
- `Ctrl+Shift+F`: Capture full page
- `Ctrl+Shift+A`: Capture selected region

### Screenshot Tips

- Full page capture may take several seconds for long pages
- Selected region: click and drag to select area
- Screenshots are saved as PNG format
- Filename includes timestamp and page title

### Extension Troubleshooting

**Extension not connecting**:
- Check that ImageTools is accessible in a browser tab
- Regenerate registration URL and try again
- Check browser console for errors

**Screenshots not appearing**:
- Wait a few seconds for upload
- Refresh ImageTools web interface
- Check browser permissions for extension

**Full page capture not working**:
- Some pages block full-page capture
- Try "Visible Area" or "Selected Region" instead
- Dynamic content may not capture properly

## Tips and Tricks

### Workflow Optimization

**Quick Email Prep**:
1. Upload all photos
2. Select all with checkbox
3. Click "Email" preset in toolbar
4. Click "Download as ZIP"
5. Done in seconds!

**Before/After Comparisons**:
1. Upload image
2. Compress with preset
3. Open in editor
4. Compare quality before downloading

**Batch Processing**:
- Upload up to 5 images at once
- Select all for bulk operations
- Use consistent presets for uniformity

### Keyboard Shortcuts (Web Interface)

- `Ctrl/Cmd + V`: Paste image from clipboard
- `Esc`: Close editor/modal
- `Ctrl/Cmd + Z`: Undo last operation
- `Delete`: Remove selected images

### Storage Management

- Images auto-delete after 7 days
- Download important images before they expire
- Clear browser cache to free local storage
- Session persists across browser tabs

### Quality vs. File Size

**For emails**:
- Prioritize file size (use Email preset)
- Most email clients limit attachments to 25 MB total
- Lower quality (70-85%) often imperceptible

**For websites**:
- Balance quality and load time (use Web preset)
- Modern formats like WebP provide best compression
- Consider mobile users with slower connections

**For printing**:
- Keep original or use minimal compression
- Maintain high resolution (300 DPI minimum)
- Use PNG or JPEG at 95%+ quality

### Privacy and Security

- Images are NOT permanently stored
- Session-based storage only
- No user accounts required
- All processing happens on your server
- AI features use encrypted API keys

## Troubleshooting

### Upload Issues

**"File too large" error**:
- Maximum file size is 20 MB by default
- Compress image before uploading
- Contact administrator to increase limit

**"Maximum images exceeded"**:
- Session limit is 5 images by default
- Delete existing images before uploading more
- Or download and clear current session

**Upload stalls or fails**:
- Check internet connection
- Try smaller file
- Refresh page and try again
- Check browser console for errors

### Compression Issues

**Image quality too low after compression**:
- Use Custom preset with higher quality setting
- Start with Web preset instead of Email
- Some images don't compress well (already optimized)

**File size not reducing much**:
- Image may already be optimized
- Try different format (e.g., JPEG instead of PNG)
- Use more aggressive compression settings

**Colors look different after compression**:
- JPEG compression can affect colors slightly
- Use PNG for images requiring color accuracy
- Increase quality percentage

### Editor Issues

**Editor won't open**:
- Refresh the page
- Check browser console for errors
- Try a different browser
- Ensure JavaScript is enabled

**Changes not saving**:
- Click "Apply" or "Save" button
- Don't close editor while saving
- Check for error messages

**Editor is slow**:
- Large images take longer to edit
- Compress image first
- Close other browser tabs
- Use a more powerful device

### AI Feature Issues

**Can't connect to OpenRouter**:
- Ensure you have an OpenRouter account
- Check that OAuth redirect URL is configured correctly
- Try disconnecting and reconnecting
- Contact administrator if self-hosted

**Background removal fails**:
- Image may be too complex
- Try an image with clearer subject
- Ensure adequate OpenRouter credits
- Check AI model is selected

**AI chat not responding**:
- Check OpenRouter credits
- Try selecting a different model
- Ensure internet connection is stable
- Refresh page and try again

### Browser Compatibility

**Recommended Browsers**:
- Chrome 90+
- Firefox 88+
- Safari 13.1+
- Edge 90+

**Known Issues**:
- Internet Explorer: Not supported
- Older browsers: Some features may not work
- Mobile browsers: Full feature support on modern versions

### Connection Issues

**"Server unreachable" error**:
- Check that ImageTools is running
- Verify correct URL
- Check firewall settings
- Contact administrator

**Slow performance**:
- Check internet speed
- Server may be under load
- Try during off-peak hours
- Contact administrator if persistent

### Getting Help

1. **Check this guide first**
2. **Review error messages** in browser console (F12)
3. **Try in different browser** to rule out browser issues
4. **Contact administrator** for server-related issues
5. **Report bugs** on GitHub if self-hosted

## Conclusion

You're now ready to use ImageTools like a pro! Remember:

- Drag and drop for quick uploads
- Use presets for common tasks
- Experiment with the editor
- Try AI features for advanced processing
- Download or ZIP before images expire

Happy image editing!

---

**Need more help?**
- Technical documentation: [docs/](docs/)
- Setup guide: [README.md](README.md)
- Android app: [android-app/README.md](android-app/README.md)
- Browser extension: [browser-addons/README.md](browser-addons/README.md)
