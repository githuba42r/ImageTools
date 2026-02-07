# ImageTools

A powerful web-based image compression and editing tool designed to quickly prepare high-resolution images for email and web use. Built with Vue.js and Python FastAPI, ImageTools provides an intuitive interface for bulk image processing with AI-powered features.

**Multi-Platform Ecosystem**: Upload images from anywhere with the Android mobile app (share from gallery/camera) or browser extensions (capture screenshots), then edit and optimize them in the web interface with advanced AI features.

## Support This Project

If you find ImageTools useful, consider supporting its continued development:

[![Donate with PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg)](https://www.paypal.com/donate/?hosted_button_id=YOUR_BUTTON_ID)

Your donations help maintain and improve ImageTools. Thank you for your support!

## Features

- **Image Compression**: Smart compression with presets for email, web, and custom sizes
- **Bulk Operations**: Process multiple images simultaneously
- **Image Editing**: Integrated TUI Image Editor for cropping, filters, and adjustments
- **AI Features** (OAuth-connected):
  - Background removal
  - AI chat interface for natural language image manipulation
  - Advanced filters and effects
- **Multi-Platform Integration**:
  - Web interface
  - Android mobile app for seamless uploads
  - Browser extensions for screenshot capture
- **Undo/Redo**: Full history tracking for all modifications
- **Export Options**: Download individual images, copy to clipboard, or bulk download as ZIP

## Quick Start

See [QUICKSTART.md](QUICKSTART.md) for detailed local development setup instructions.

### Local Development (Fastest)

```bash
# Run everything with one command
./run-all.sh
```

Then open http://localhost:5173

### Docker Deployment (Production)

#### Option 1: Simple Docker Setup

```bash
# Build and start
docker-compose up --build -d

# Access at http://localhost:8082
```

#### Option 2: With Nginx Reverse Proxy and Authentication

For production deployments with HTTP Basic Authentication:

```bash
cd deployment
cp .env.example .env
# Edit .env with your credentials
docker-compose up -d

# Access at http://localhost
```

See [deployment/README.md](deployment/README.md) for full deployment documentation including:
- Nginx reverse proxy configuration
- HTTP Basic Authentication setup
- Authelia integration (coming soon)
- SSL/HTTPS configuration
- Multiple user management

## Architecture Overview

- **Frontend**: Vue 3 + Vite + TUI Image Editor
- **Backend**: Python FastAPI with async operations
- **Database**: SQLite (file-based, no external dependencies)
- **Image Processing**: PIL (Pillow), rembg for background removal
- **AI Integration**: OpenRouter API with OAuth2 PKCE flow
- **Real-time Features**: WebSocket support for live updates

## Deployment Scenarios

### 1. Docker with Nginx Reverse Proxy and Basic Auth

Perfect for self-hosted deployments with password protection.

```bash
cd deployment
cp .env.example .env
# Configure authentication in .env
docker-compose up -d
```

**Features**:
- HTTP Basic Authentication
- WebSocket support
- Persistent storage
- Health monitoring

**Documentation**: [deployment/README.md](deployment/README.md)

### 2. Docker with Authelia (Advanced Authentication)

For enterprise deployments requiring:
- Multi-factor authentication (MFA/2FA)
- Single Sign-On (SSO)
- LDAP/Active Directory integration
- Advanced access control

**Setup Steps**:

1. **Deploy Authelia** (separate container):
   ```bash
   # Authelia configuration (example)
   docker run -d \
     --name authelia \
     -v ./authelia-config:/config \
     -p 9091:9091 \
     authelia/authelia:latest
   ```

2. **Configure Nginx to use Authelia**:
   ```nginx
   # In nginx.conf, add auth_request directive
   location / {
       auth_request /authelia;
       auth_request_set $user $upstream_http_remote_user;
       proxy_pass http://imagetools:8081;
       # ... other proxy settings
   }
   
   location /authelia {
       internal;
       proxy_pass http://authelia:9091/api/verify;
       # ... authelia-specific headers
   }
   ```

3. **Update docker-compose.yml**:
   ```yaml
   services:
     authelia:
       image: authelia/authelia:latest
       volumes:
         - ./authelia-config:/config
       ports:
         - "9091:9091"
       networks:
         - imagetools-network
     
     nginx:
       # ... existing nginx config
       depends_on:
         - authelia
         - imagetools
   ```

4. **Configure Authelia** (`authelia-config/configuration.yml`):
   ```yaml
   server:
     host: 0.0.0.0
     port: 9091
   
   authentication_backend:
     file:
       path: /config/users_database.yml
   
   access_control:
     default_policy: deny
     rules:
       - domain: imagetools.yourdomain.com
         policy: two_factor
   
   session:
     domain: yourdomain.com
     expiration: 1h
     inactivity: 5m
   ```

**Benefits**:
- Two-factor authentication (TOTP, WebAuthn, Duo)
- Session management with Redis
- Granular access control policies
- Integration with existing identity providers

**Documentation**: 
- [Authelia Documentation](https://www.authelia.com/docs/)
- [Nginx Authelia Integration](https://www.authelia.com/integration/proxies/nginx/)
- See [docs/NGINX_AUTHELIA_DEPLOYMENT.md](docs/NGINX_AUTHELIA_DEPLOYMENT.md) for ImageTools-specific configuration

### 3. Standalone Docker (No Authentication)

For trusted networks or development:

```bash
docker-compose up --build -d
# Access at http://localhost:8082
```

See [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md) for complete Docker documentation.

## Mobile and Browser Integration

### Android App

Share images directly from your Android device to ImageTools.

**Quick Setup**:
1. Build and install the Android app (see [android-app/README.md](android-app/README.md))
2. Open ImageTools web interface and generate a QR code
3. Scan the QR code in the Android app to pair
4. Share images from any app to ImageTools

**Download**: Coming soon to Google Play Store

**Documentation**: [android-app/README.md](android-app/README.md)

### Browser Extensions

Capture screenshots and send them directly to ImageTools for editing.

**Features**:
- Capture visible area
- Capture full scrolling page
- Capture selected region
- OAuth2-style secure authorization

**Supported Browsers**:
- Chrome/Chromium (Manifest V3)
- Firefox (WebExtensions)

**Installation**:
- **Chrome Web Store**: Coming soon
- **Firefox Add-ons**: Coming soon
- **Manual Installation**: See [browser-addons/README.md](browser-addons/README.md)

**Documentation**: [browser-addons/README.md](browser-addons/README.md)

## Configuration

ImageTools uses environment variables for configuration. Copy the example file and customize:

```bash
# For local development
cp .env.example .env

# For production Docker deployment
cp .env.production.example .env
```

### Key Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `False` | Enable debug mode |
| `SERVER_PORT` | `8081` | Backend server port |
| `SESSION_EXPIRY_DAYS` | `7` | How long to keep uploaded images |
| `MAX_IMAGES_PER_SESSION` | `5` | Maximum images per upload |
| `MAX_UPLOAD_SIZE_MB` | `20` | Maximum file size |
| `OPENROUTER_APP_URL` | (required) | Public URL for OAuth callbacks |
| `SESSION_SECRET_KEY` | (auto) | Encryption key (min 32 chars) |

See [docs/ENV_CONFIG.md](docs/ENV_CONFIG.md) for full configuration reference.

## User Guide

For end-user instructions on how to use ImageTools, see [USER_GUIDE.md](USER_GUIDE.md).

Topics covered:
- Uploading images
- Using compression presets
- Image editing
- Background removal
- AI chat features
- Downloading and exporting
- Mobile app integration
- Browser extension usage

## Documentation

### User Documentation
- [USER_GUIDE.md](USER_GUIDE.md) - End-user guide for using ImageTools
- [QUICKSTART.md](QUICKSTART.md) - Quick setup for local development

### Deployment Documentation
- [deployment/README.md](deployment/README.md) - Nginx reverse proxy with Basic Auth
- [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md) - Standalone Docker deployment
- [docs/NGINX_AUTHELIA_DEPLOYMENT.md](docs/NGINX_AUTHELIA_DEPLOYMENT.md) - Authelia integration guide
- [docs/ENV_CONFIG.md](docs/ENV_CONFIG.md) - Environment configuration reference

### Platform Integration
- [android-app/README.md](android-app/README.md) - Android app setup and integration
- [browser-addons/README.md](browser-addons/README.md) - Browser extension installation

### Technical Documentation (Implementation Details)
- [docs/IMPLEMENTATION_STRATEGY.md](docs/IMPLEMENTATION_STRATEGY.md) - Overall architecture
- [docs/WEBSOCKET_ARCHITECTURE.md](docs/WEBSOCKET_ARCHITECTURE.md) - Real-time features
- [docs/AI_CHAT_IMPLEMENTATION.md](docs/AI_CHAT_IMPLEMENTATION.md) - AI integration details
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) - Developer guide
- [docs/MOBILE_APP_INTEGRATION.md](docs/MOBILE_APP_INTEGRATION.md) - Mobile integration details
- [docs/ANDROID_BUILD_GUIDE.md](docs/ANDROID_BUILD_GUIDE.md) - Android build process
- [docs/TESTING_MULTI_USER.md](docs/TESTING_MULTI_USER.md) - Multi-user testing guide

## Development

### Prerequisites

- Python 3.11+
- Node.js 20+
- npm 9+

### Setup Development Environment

```bash
# Clone repository
git clone <repository-url>
cd ImageTools

# Run automated setup
./run-all.sh
```

This script will:
1. Create Python virtual environment
2. Install backend dependencies
3. Install frontend dependencies
4. Start backend on http://localhost:8001
5. Start frontend on http://localhost:5173

### Manual Setup

#### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Project Structure

```
ImageTools/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic
│   │   └── main.py         # Application entry point
│   └── requirements.txt
├── frontend/                # Vue.js frontend
│   ├── src/
│   │   ├── components/     # Vue components
│   │   ├── stores/         # Pinia state management
│   │   └── services/       # API client
│   └── package.json
├── android-app/            # Android mobile app
├── browser-addons/         # Browser extensions
│   ├── chrome/
│   └── firefox/
├── deployment/             # Deployment configs
│   ├── docker-compose.yml
│   └── nginx/
├── docs/                   # Technical documentation
├── docker-compose.yml      # Simple Docker setup
├── Dockerfile             # Multi-stage build
└── README.md              # This file
```

## API Documentation

When running locally, API documentation is available at:
- OpenAPI/Swagger UI: http://localhost:8001/api/v1/docs
- ReDoc: http://localhost:8001/api/v1/redoc

## Security Considerations

### Production Deployment Checklist

- [ ] Set strong `SESSION_SECRET_KEY` (min 32 characters)
- [ ] Configure proper `OPENROUTER_APP_URL` for your domain
- [ ] Use HTTPS (TLS/SSL certificates)
- [ ] Enable authentication (Basic Auth or Authelia)
- [ ] Configure firewall rules
- [ ] Set up regular backups
- [ ] Configure `CORS_ORIGINS` appropriately
- [ ] Use strong passwords for authentication
- [ ] Keep Docker images updated
- [ ] Monitor logs for suspicious activity

### OAuth Security

ImageTools uses OpenRouter OAuth2 PKCE flow for AI features:
- Users connect their own OpenRouter accounts
- API keys are encrypted at rest
- Keys are never exposed to frontend
- Session-based key management
- Automatic token refresh

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Supporting the Project

ImageTools is free and open-source software. If you find it useful, please consider supporting its continued development:

### Financial Support

[![Donate with PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg)](https://www.paypal.com/donate/?hosted_button_id=YOUR_BUTTON_ID)

Your donations help:
- Cover server and infrastructure costs
- Fund ongoing development and new features
- Support maintenance and bug fixes
- Improve documentation and user experience

**To set up your PayPal donation link:**
1. Log in to your PayPal account
2. Go to: https://www.paypal.com/donate/buttons
3. Create a donation button and get your hosted button ID
4. Replace `YOUR_BUTTON_ID` in the link above with your actual button ID

Alternatively, you can use a direct PayPal.me link:
- Format: `https://www.paypal.me/YourPayPalUsername`
- Replace the badge URL with: `https://www.paypal.me/YourPayPalUsername`

### Other Ways to Contribute

- **Report bugs**: Open an issue on GitHub
- **Suggest features**: Share your ideas in the issue tracker
- **Improve documentation**: Help make the docs clearer
- **Share the project**: Tell others about ImageTools
- **Write tutorials**: Create guides and blog posts
- **Translate**: Help localize ImageTools for other languages

## License

ImageTools is free and open-source software licensed under the GNU General Public License v3.0 (GPL-3.0).

This means you are free to:
- Use the software for any purpose
- Study and modify the source code
- Share the software with others
- Share your modifications

Under the following conditions:
- Source code must be made available when distributing the software
- Modifications must be released under the same license
- Changes made to the code must be documented
- Copyright and license notices must be preserved

For the full license text, see the [LICENSE](LICENSE) file in this repository or visit [https://www.gnu.org/licenses/gpl-3.0.en.html](https://www.gnu.org/licenses/gpl-3.0.en.html)

## Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Check existing documentation in the `docs/` folder
- Review the User Guide for usage questions

## Roadmap

- [ ] Publish Android app to Google Play Store
- [ ] Publish browser extensions to Chrome Web Store and Firefox Add-ons
- [ ] Add full Authelia integration example
- [ ] PostgreSQL support for multi-container deployments
- [ ] Kubernetes deployment manifests
- [ ] Video compression support
- [ ] PDF optimization
- [ ] Batch processing API
- [ ] User accounts and persistent storage
