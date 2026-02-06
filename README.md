# ImageTools

Docker container with web frontend for simple image manipulation and editing.

Designed to quickly allow the modification of images from a camera to be cropped, resized, and optimized for adding to a webpage or email.

## Features

- 📸 **Camera Capture** - Capture images directly from your device camera
- 📁 **File Upload** - Upload images from your device
- ✂️ **Crop** - Select and crop specific areas of your images
- 📏 **Resize** - Resize images with presets for:
  - Email (thumbnails, headers, content)
  - Web (various sizes from thumbnail to hero images)
  - Social Media (Facebook, Twitter, Instagram)
- ⚡ **Optimize** - Compress images with adjustable quality
- 🔄 **Format Conversion** - Convert between JPEG, PNG, and WebP formats
- 💾 **Download** - Save processed images instantly

## Quick Start

### Using Docker Compose (Recommended)

```bash
docker-compose up
```

Then open your browser to `http://localhost:5000`

### Using Docker

```bash
docker build -t imagetools .
docker run -p 5000:5000 imagetools
```

### Local Development

```bash
pip install -r requirements.txt
python app.py
```

Then open your browser to `http://localhost:5000`

## Usage

1. **Load an Image**
   - Click "Upload Image" to select a file from your device
   - Or click "Use Camera" to capture a photo directly

2. **Crop (Optional)**
   - Click "Enable Crop"
   - Click and drag on the image to select the area you want to keep
   - Click "Apply Crop" to crop the image

3. **Resize**
   - Choose a preset from Email, Web, or Social tabs
   - Or enter custom dimensions in the Width/Height fields
   - Leave one dimension empty to maintain aspect ratio

4. **Optimize**
   - Select output format (JPEG, PNG, or WebP)
   - Adjust quality slider (1-100)
   - Higher quality = larger file size

5. **Process & Download**
   - Click "Process & Download" to apply all changes
   - The optimized image will be automatically downloaded

## Technology Stack

- **Backend**: Python Flask
- **Image Processing**: Pillow (PIL)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Containerization**: Docker

## Requirements

- Docker (for containerized deployment)
- Or Python 3.11+ with pip (for local development)

## License

MIT
