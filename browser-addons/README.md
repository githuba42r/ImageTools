# ImageTools Browser Addons

Browser extensions for capturing screenshots and sending them to ImageTools for editing and compression.

## Features

- Capture visible area of webpage
- Capture full scrolling page
- Capture selected region
- OAuth2-style authorization flow
- Secure token-based authentication
- Direct upload to ImageTools

## Installation

### Firefox

1. Navigate to `browser-addons/firefox/`
2. Open Firefox and go to `about:debugging`
3. Click "This Firefox" → "Load Temporary Add-on"
4. Select the `manifest.json` file
5. The addon is now installed temporarily for testing

### Chrome

1. Navigate to `browser-addons/chrome/`
2. Open Chrome and go to `chrome://extensions/`
3. Enable "Developer mode"
4. Click "Load unpacked"
5. Select the `chrome` folder
6. The extension is now installed for testing

## Usage

1. Open ImageTools in your browser
2. Go to Settings (About modal) → Click "Browser Addon"
3. Click "Generate Registration URL"
4. Copy the registration URL
5. Click the ImageTools browser extension icon
6. Paste the registration URL and click "Connect"
7. Once connected, you can:
   - Click the extension icon and choose a capture mode
   - Right-click on any page and use the context menu

## OAuth2 Authorization Flow

1. User clicks "Connect Addon" in ImageTools web UI
2. Backend generates an authorization code (5-minute expiry)
3. User pastes the registration URL into the addon
4. Addon extracts the authorization code
5. Addon exchanges code for:
   - Access token (30 days)
   - Refresh token (90 days)
6. Addon uses access token for all screenshot uploads
7. When access token expires, addon uses refresh token to get a new one

## Security

- Authorization codes are single-use and expire after 5 minutes
- Access tokens expire after 30 days
- Refresh tokens expire after 90 days
- All tokens are stored securely in browser storage
- Tokens can be revoked from the ImageTools settings

## Development

### Project Structure

```
browser-addons/
├── firefox/
│   ├── manifest.json       # Firefox WebExtension manifest (v2)
│   ├── background.js       # Background script for auth and capture
│   ├── popup.html         # Extension popup UI
│   ├── popup.js           # Popup logic
│   ├── content.js         # Content script for selection capture
│   └── icons/             # Extension icons
└── chrome/
    ├── manifest.json       # Chrome Extension manifest (v3)
    ├── background.js       # Service worker for auth and capture
    ├── popup.html         # Extension popup UI
    ├── popup.js           # Popup logic
    ├── content.js         # Content script for selection capture
    └── icons/             # Extension icons
```

### API Endpoints Used

- `POST /api/v1/addon/authorize` - Create authorization
- `POST /api/v1/addon/token` - Exchange code for tokens
- `POST /api/v1/addon/refresh` - Refresh access token
- `POST /api/v1/addon/upload` - Upload screenshot
- `GET /api/v1/addon/authorizations/session/{session_id}/list` - List connected addons
- `DELETE /api/v1/addon/authorizations/{auth_id}` - Revoke authorization

## Building for Production

### Firefox

1. Create addon icons (16x16, 48x48, 128x128)
2. Test thoroughly with temporary installation
3. Package as XPI:
   ```bash
   cd browser-addons/firefox
   zip -r imagetools-firefox.xpi *
   ```
4. Submit to Mozilla Add-ons store

### Chrome

1. Create extension icons (16x16, 48x48, 128x128)
2. Test thoroughly with unpacked installation
3. Package as ZIP:
   ```bash
   cd browser-addons/chrome
   zip -r imagetools-chrome.zip *
   ```
4. Submit to Chrome Web Store

## TODO

- Add full page capture implementation
- Add selection capture with better UI
- Add screenshot annotation before upload
- Add support for other browsers (Edge, Safari)
- Add screenshot history in extension
- Add settings panel in extension
- Add keyboard shortcuts
- Publish to browser addon stores

## License

Same as Image Tools main project
