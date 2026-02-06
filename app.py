from flask import Flask, render_template, request, send_file, jsonify
from PIL import Image
import io
import os
from werkzeug.utils import secure_filename
import base64

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    """Handle image upload from file or camera"""
    try:
        if 'file' not in request.files and 'image' not in request.form:
            return jsonify({'error': 'No file provided'}), 400
        
        # Handle file upload
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if file and allowed_file(file.filename):
                image = Image.open(file.stream)
        # Handle camera capture (base64 data)
        elif 'image' in request.form:
            image_data = request.form['image']
            # Remove data URL prefix
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        
        # Return image info
        img_io = io.BytesIO()
        image.save(img_io, 'JPEG', quality=95)
        img_io.seek(0)
        img_base64 = base64.b64encode(img_io.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'image': f'data:image/jpeg;base64,{img_base64}',
            'width': image.width,
            'height': image.height
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/process', methods=['POST'])
def process_image():
    """Process image with crop, resize, and optimization"""
    try:
        data = request.get_json()
        
        if 'image' not in data:
            return jsonify({'error': 'No image data provided'}), 400
        
        # Decode base64 image
        image_data = data['image']
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Apply crop if specified
        if 'crop' in data:
            crop = data['crop']
            image = image.crop((
                int(crop['x']),
                int(crop['y']),
                int(crop['x'] + crop['width']),
                int(crop['y'] + crop['height'])
            ))
        
        # Apply resize if specified
        if 'resize' in data:
            resize = data['resize']
            width = int(resize.get('width', image.width))
            height = int(resize.get('height', image.height))
            
            # Maintain aspect ratio if only one dimension specified
            if 'width' in resize and 'height' not in resize:
                aspect_ratio = image.height / image.width
                height = int(width * aspect_ratio)
            elif 'height' in resize and 'width' not in resize:
                aspect_ratio = image.width / image.height
                width = int(height * aspect_ratio)
            
            image = image.resize((width, height), Image.Resampling.LANCZOS)
        
        # Apply optimization
        quality = int(data.get('quality', 85))
        optimize = data.get('optimize', True)
        output_format = data.get('format', 'JPEG').upper()
        
        # Prepare output
        img_io = io.BytesIO()
        
        if output_format == 'PNG':
            image.save(img_io, 'PNG', optimize=optimize)
            mime_type = 'image/png'
        elif output_format == 'WEBP':
            image.save(img_io, 'WEBP', quality=quality, method=6)
            mime_type = 'image/webp'
        else:  # JPEG
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                image = background
            image.save(img_io, 'JPEG', quality=quality, optimize=optimize)
            mime_type = 'image/jpeg'
        
        img_io.seek(0)
        img_base64 = base64.b64encode(img_io.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'image': f'data:{mime_type};base64,{img_base64}',
            'width': image.width,
            'height': image.height,
            'size': len(img_io.getvalue())
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/presets/<preset_type>')
def get_preset(preset_type):
    """Get preset dimensions for common use cases"""
    presets = {
        'email': [
            {'name': 'Email Thumbnail', 'width': 150, 'height': 150},
            {'name': 'Email Header', 'width': 600, 'height': 200},
            {'name': 'Email Content', 'width': 600, 'height': 400},
        ],
        'web': [
            {'name': 'Thumbnail', 'width': 200, 'height': 200},
            {'name': 'Small', 'width': 400, 'height': 300},
            {'name': 'Medium', 'width': 800, 'height': 600},
            {'name': 'Large', 'width': 1200, 'height': 900},
            {'name': 'Hero Image', 'width': 1920, 'height': 600},
        ],
        'social': [
            {'name': 'Facebook Post', 'width': 1200, 'height': 630},
            {'name': 'Twitter Post', 'width': 1200, 'height': 675},
            {'name': 'Instagram Square', 'width': 1080, 'height': 1080},
            {'name': 'Instagram Portrait', 'width': 1080, 'height': 1350},
        ]
    }
    
    return jsonify(presets.get(preset_type, []))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
