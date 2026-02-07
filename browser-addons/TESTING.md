# Browser Addon Testing Guide

## Prerequisites

1. **Backend Running**: Ensure ImageTools backend is running
   ```bash
   cd /home/philg/working/ImageTools/backend
   python -m uvicorn app.main:app --reload
   ```

2. **Frontend Running**: Ensure ImageTools frontend is running
   ```bash
   cd /home/philg/working/ImageTools/frontend
   npm run dev
   ```

## Firefox Testing

### 1. Load Firefox Extension

1. Open Firefox
2. Navigate to `about:debugging#/runtime/this-firefox`
3. Click "Load Temporary Add-on"
4. Navigate to `/home/philg/working/ImageTools/browser-addons/firefox/`
5. Select `manifest.json`
6. Extension should now be loaded (look for camera icon in toolbar)

### 2. Connect Extension to ImageTools

1. Open ImageTools in browser (usually `http://localhost:5173`)
2. Click on "About" or settings icon
3. Click "Browser Addon" button
4. Click "Generate Registration URL"
5. Copy the generated URL (format: `imagetools://authorize?code=...&instance=...`)
6. Click the ImageTools extension icon in Firefox toolbar
7. Paste the registration URL into the input field
8. Click "Connect"
9. Extension should show "Connected to localhost" status

### 3. Test Screenshot Capture

#### Test Visible Area Capture:
1. Navigate to any webpage
2. Right-click on the page
3. Select "Capture Visible Area" from context menu
4. Screenshot should upload and ImageTools should open in new tab
5. Verify screenshot appears in ImageTools

#### Test Full Page Capture:
1. Navigate to a long webpage (e.g., Wikipedia article)
2. Right-click on the page
3. Select "Capture Full Page" from context menu
4. Wait for capture to complete (may take several seconds for long pages)
5. Screenshot should upload and ImageTools should open
6. Verify full page screenshot appears (should show content below fold)

#### Test Selection Capture:
1. Navigate to any webpage
2. Right-click on the page
3. Select "Capture Selection" from context menu
4. Page should show dark overlay with crosshair cursor
5. Click and drag to select an area
6. Release mouse to capture
7. Screenshot of selected area should upload
8. Verify cropped screenshot appears in ImageTools

### 4. Test Context Menu Alternative

Instead of right-click menu, you can also use the extension popup:
1. Click extension icon in toolbar
2. Click one of the three capture buttons:
   - "Capture Visible"
   - "Capture Full Page"
   - "Capture Selection"

## Chrome Testing

### 1. Load Chrome Extension

1. Open Chrome
2. Navigate to `chrome://extensions/`
3. Enable "Developer mode" (toggle in top-right)
4. Click "Load unpacked"
5. Navigate to `/home/philg/working/ImageTools/browser-addons/chrome/`
6. Select the chrome folder
7. Extension should now be loaded (look for camera icon in toolbar)

### 2-4. Follow Same Steps as Firefox

The testing steps for connection and screenshot capture are identical to Firefox.

## Troubleshooting

### Connection Issues

**Problem**: "Failed to connect" error when pasting registration URL

**Solutions**:
- Verify backend is running on correct port
- Check registration URL format is correct: `imagetools://authorize?code=...&instance=...`
- Check browser console (F12) for detailed error messages
- Verify authorization code hasn't expired (5-minute expiry)

### Screenshot Upload Issues

**Problem**: Screenshot captures but doesn't upload

**Solutions**:
- Check browser console for upload errors
- Verify access token hasn't expired
- Try disconnecting and reconnecting extension
- Check backend logs for upload errors

### Full Page Capture Issues

**Problem**: Full page capture only captures visible area

**Solutions**:
- Check content script is injecting properly
- Look for errors in browser console
- Try on simpler page first (not YouTube, Netflix, etc. which may block scripts)

### Selection Capture Issues

**Problem**: Selection overlay doesn't appear

**Solutions**:
- Check content script permissions
- Some pages may block overlays (CSP restrictions)
- Try on a different page

### Icon Not Showing

**Problem**: Extension loads but no icon in toolbar

**Solutions**:
- Check icons folder has all three PNG files (16, 48, 128)
- Try removing and re-adding extension
- Check manifest.json paths are correct

## Expected Behavior

### Successful Connection:
- Extension popup shows: "Connected to localhost" (or your instance hostname)
- Green status indicator
- Capture buttons are enabled

### Successful Upload:
- Browser notification: "Screenshot uploaded!"
- ImageTools opens in new tab
- Screenshot appears in ImageTools gallery

### Token Refresh:
- If access token expires (30 days), extension automatically refreshes using refresh token
- No user interaction needed
- If refresh token also expires (90 days), user must reconnect

## Verification Checklist

- [ ] Extension loads without errors
- [ ] Connection to ImageTools succeeds
- [ ] Visible area capture works
- [ ] Full page capture works (test on long page)
- [ ] Selection capture works
- [ ] Screenshots upload successfully
- [ ] ImageTools opens after upload
- [ ] Screenshots appear in gallery
- [ ] Context menu items appear
- [ ] Popup UI works
- [ ] Notifications show
- [ ] Can disconnect/reconnect

## Known Limitations

1. **Protocol Handler**: The `imagetools://` protocol handler may not work in all browsers. If it doesn't work, users can manually parse the URL.

2. **Full Page Capture**: May not work perfectly on:
   - Pages with lazy-loading images
   - Infinite scroll pages
   - Pages with complex animations
   - Pages with CSP restrictions

3. **Selection Capture**: May not work on:
   - Pages with strict CSP headers
   - Iframes with different origins
   - Some embedded content (videos, etc.)

4. **Permissions**: Some websites may block content script injection due to CSP policies.

## Next Steps After Testing

If all tests pass:
1. Consider publishing to browser addon stores
2. Add keyboard shortcuts for quick capture
3. Add screenshot annotation before upload
4. Add settings panel in extension
5. Support for Edge browser (same as Chrome)
6. Support for Safari (requires different approach)
