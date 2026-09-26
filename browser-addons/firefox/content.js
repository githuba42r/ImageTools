// ImageTools Content Script (simplified for brevity)

// Listen for messages from background script.
// content.js is re-injected on every capture; the guard keeps a single
// listener so a message isn't handled (and answered) once per injection.
// No top-level const/let in this file for the same reason - re-declaring
// them on re-injection throws.
if (!window.__imagetoolsContentListener) {
  window.__imagetoolsContentListener = true;
  browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log('[ImageTools Content] Received message:', message.action);
    
    if (message.action === 'startSelectionCapture') {
      initSelectionCapture();
      sendResponse({ success: true });
      return true;
    } else if (message.action === 'showCapturePreview') {
      showCapturePreview(message.dataUrl, message.filename, message.title);
      sendResponse({ success: true });
      return true;
    } else if (message.action === 'captureFullPage') {
      // Handle async operation. The preview is shown here rather than handing
      // the (potentially huge) image back to the background and round-tripping it.
      captureFullPageCanvas()
        .then(result => {
          showCapturePreview(result.dataUrl, `screenshot-full-${Date.now()}.png`, 'Full page captured');
          console.log('[ImageTools Content] Full page preview shown');
          sendResponse({ previewShown: true });
        })
        .catch(error => {
          console.error('[ImageTools Content] Error in captureFullPageCanvas:', error);
          sendResponse({ error: error.message });
        });
      return true; // Keep channel open for async response
    }
    
    return false;
  });
}

// Initialize selection capture overlay
function initSelectionCapture() {
  // Remove any existing overlays first
  cleanupSelectionUI();
  
  // Create overlay for selection
  const overlay = document.createElement('div');
  overlay.id = 'imagetools-selection-overlay';
  overlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.3);
    z-index: 999999;
    cursor: crosshair;
    user-select: none;
    -webkit-user-select: none;
    touch-action: none;
  `;
  
  const selectionBox = document.createElement('div');
  selectionBox.id = 'imagetools-selection-box';
  selectionBox.style.cssText = `
    position: fixed;
    border: 3px solid #6366f1;
    background: rgba(99,102,241,0.1);
    display: none;
    z-index: 1000000;
    pointer-events: none;
  `;
  
  // Create action buttons container
  const actionsContainer = document.createElement('div');
  actionsContainer.id = 'imagetools-selection-actions';
  actionsContainer.style.cssText = `
    position: fixed;
    display: none;
    flex-direction: column;
    z-index: 1000001;
    gap: 10px;
    padding: 10px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  `;

  const tagPicker = createTagPicker();
  const buttonsRow = document.createElement('div');
  buttonsRow.style.cssText = 'display: flex; gap: 10px;';
  
  // Create OK button
  const okButton = document.createElement('button');
  okButton.id = 'imagetools-selection-ok';
  okButton.textContent = '✓ Capture';
  okButton.style.cssText = `
    padding: 10px 20px;
    background: #10b981;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  `;
  okButton.onmouseover = () => okButton.style.background = '#059669';
  okButton.onmouseout = () => okButton.style.background = '#10b981';
  
  // Create Cancel button
  const cancelButton = document.createElement('button');
  cancelButton.id = 'imagetools-selection-cancel';
  cancelButton.textContent = '✕ Cancel';
  cancelButton.style.cssText = `
    padding: 10px 20px;
    background: #ef4444;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  `;
  cancelButton.onmouseover = () => cancelButton.style.background = '#dc2626';
  cancelButton.onmouseout = () => cancelButton.style.background = '#ef4444';
  
  // Create Reselect button
  const reselectButton = document.createElement('button');
  reselectButton.id = 'imagetools-selection-reselect';
  reselectButton.textContent = '↻ Reselect';
  reselectButton.style.cssText = `
    padding: 10px 20px;
    background: #6366f1;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  `;
  reselectButton.onmouseover = () => reselectButton.style.background = '#4f46e5';
  reselectButton.onmouseout = () => reselectButton.style.background = '#6366f1';
  
  buttonsRow.appendChild(okButton);
  buttonsRow.appendChild(reselectButton);
  buttonsRow.appendChild(cancelButton);
  actionsContainer.appendChild(tagPicker.element);
  actionsContainer.appendChild(buttonsRow);
  
  document.body.appendChild(overlay);
  document.body.appendChild(selectionBox);
  document.body.appendChild(actionsContainer);

  // Prevent mouse events from bubbling to page-level listeners (e.g. click-outside
  // handlers that dismiss modals). Applied to both the overlay and the actions
  // container so button clicks also stay contained.
  const blockPropagation = (e) => e.stopPropagation();
  for (const evt of ['mousedown', 'mouseup', 'click', 'pointerdown', 'pointerup']) {
    overlay.addEventListener(evt, blockPropagation);
    actionsContainer.addEventListener(evt, blockPropagation);
  }

  let startX = null;
  let startY = null;
  let isDrawing = false;
  let currentRect = null;

  // Clamp selection coordinates to the viewport so dragging the pointer
  // past the window edge still produces a valid selection rectangle.
  const clampX = (v) => Math.max(0, Math.min(v, window.innerWidth - 1));
  const clampY = (v) => Math.max(0, Math.min(v, window.innerHeight - 1));

  // Pointer down - start selection.
  //
  // Pointer Events + setPointerCapture guarantee that pointermove/pointerup
  // are still delivered to the overlay even when the pointer leaves the
  // browser viewport (released off the edge of the screen). preventDefault()
  // plus user-select:none on the overlay suppress the browser's native
  // text/content selection that otherwise highlights the whole page.
  overlay.addEventListener('pointerdown', (e) => {
    if (actionsContainer.style.display === 'flex') {
      // Already have a selection, ignore
      return;
    }

    e.preventDefault();
    try { overlay.setPointerCapture(e.pointerId); } catch (_) { /* not supported */ }

    isDrawing = true;
    startX = clampX(e.clientX);
    startY = clampY(e.clientY);
    selectionBox.style.left = startX + 'px';
    selectionBox.style.top = startY + 'px';
    selectionBox.style.width = '0px';
    selectionBox.style.height = '0px';
    selectionBox.style.display = 'block';
  });

  // Pointer move - draw selection
  overlay.addEventListener('pointermove', (e) => {
    if (!isDrawing || startX === null) return;

    const currentX = clampX(e.clientX);
    const currentY = clampY(e.clientY);
    const width = Math.abs(currentX - startX);
    const height = Math.abs(currentY - startY);
    const left = Math.min(startX, currentX);
    const top = Math.min(startY, currentY);

    selectionBox.style.left = left + 'px';
    selectionBox.style.top = top + 'px';
    selectionBox.style.width = width + 'px';
    selectionBox.style.height = height + 'px';
  });

  // Pointer up - finish selection and show actions
  overlay.addEventListener('pointerup', (e) => {
    if (!isDrawing) return;

    isDrawing = false;
    try { overlay.releasePointerCapture(e.pointerId); } catch (_) { /* ignore */ }

    const width = parseInt(selectionBox.style.width);
    const height = parseInt(selectionBox.style.height);
    
    // Only show actions if selection is large enough
    if (width > 10 && height > 10) {
      currentRect = {
        x: parseInt(selectionBox.style.left),
        y: parseInt(selectionBox.style.top),
        width: width,
        height: height
      };
      
      positionActionsContainer(actionsContainer, currentRect);
      
      // Change cursor to default
      overlay.style.cursor = 'default';
    } else {
      // Selection too small, reset
      selectionBox.style.display = 'none';
      startX = null;
      startY = null;
    }
  });
  
  // OK button - capture and cleanup
  const confirmCapture = async () => {
    if (!currentRect) return;
    const tag = tagPicker.getTag();
    actionsContainer.style.display = 'none';
    overlay.style.display = 'none';
    selectionBox.style.display = 'none';
    await new Promise(resolve => setTimeout(resolve, 100));
    await captureSelection(currentRect, tag);
    cleanupSelectionUI();
  };
  okButton.addEventListener('click', confirmCapture);
  
  // Cancel button - cleanup
  cancelButton.addEventListener('click', () => {
    cleanupSelectionUI();
  });
  
  // Reselect button - reset selection
  reselectButton.addEventListener('click', () => {
    selectionBox.style.display = 'none';
    actionsContainer.style.display = 'none';
    overlay.style.cursor = 'crosshair';
    startX = null;
    startY = null;
    currentRect = null;
  });
  
  // Enter to capture, Escape to cancel
  const keyHandler = (e) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      document.removeEventListener('keydown', keyHandler);
      cleanupSelectionUI();
    } else if (e.key === 'Enter' && currentRect) {
      e.preventDefault();
      document.removeEventListener('keydown', keyHandler);
      confirmCapture();
    }
  };
  document.addEventListener('keydown', keyHandler);
}

// Position the actions container relative to the selection, keeping it in viewport.
function positionActionsContainer(actionsContainer, rect) {
  const margin = 10;
  // Reveal off-screen to measure size, then place.
  actionsContainer.style.visibility = 'hidden';
  actionsContainer.style.left = '0px';
  actionsContainer.style.top = '0px';
  actionsContainer.style.display = 'flex';

  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const { width: aw, height: ah } = actionsContainer.getBoundingClientRect();
  const boxTop = rect.y;
  const boxBottom = rect.y + rect.height;

  let top;
  if (boxBottom + margin + ah <= vh) {
    top = boxBottom + margin;
  } else if (boxTop - margin - ah >= 0) {
    top = boxTop - margin - ah;
  } else {
    top = Math.max(margin, vh - ah - margin);
  }

  let left = rect.x;
  const maxLeft = vw - aw - margin;
  if (left > maxLeft) left = maxLeft;
  if (left < margin) left = margin;

  actionsContainer.style.left = left + 'px';
  actionsContainer.style.top = top + 'px';
  actionsContainer.style.visibility = 'visible';
}

// Clean up selection UI elements
function cleanupSelectionUI() {
  const overlay = document.getElementById('imagetools-selection-overlay');
  const selectionBox = document.getElementById('imagetools-selection-box');
  const actionsContainer = document.getElementById('imagetools-selection-actions');
  
  if (overlay) overlay.remove();
  if (selectionBox) selectionBox.remove();
  if (actionsContainer) actionsContainer.remove();
}

// Capture selected area
async function captureSelection(rect, tag) {
  try {
    // First, temporarily hide the overlay elements
    const overlay = document.getElementById('imagetools-selection-overlay');
    const selectionBox = document.getElementById('imagetools-selection-box');
    if (overlay) overlay.style.display = 'none';
    if (selectionBox) selectionBox.style.display = 'none';
    
    // Wait a moment for DOM to update
    await new Promise(resolve => setTimeout(resolve, 50));
    
    // Capture the visible tab
    const dataUrl = await browser.runtime.sendMessage({ 
      action: 'captureVisibleTab' 
    });
    
    // Create canvas to crop the selection
    const canvas = document.createElement('canvas');
    canvas.width = rect.width;
    canvas.height = rect.height;
    const ctx = canvas.getContext('2d');
    
    // Load captured image
    const img = await loadImage(dataUrl);

    // Derive the real scale between CSS pixels (the selection rect, which is
    // in clientX/Y units) and the captured bitmap. Measuring from the actual
    // image is correct under normal DPR, browser zoom AND DevTools device
    // emulation - in device-toolbar mode window.devicePixelRatio reports the
    // *emulated* device ratio while captureVisibleTab renders at the host
    // scale, so the old `* devicePixelRatio` math cropped the wrong region.
    const scaleX = img.naturalWidth / window.innerWidth;
    const scaleY = img.naturalHeight / window.innerHeight;

    console.log('[ImageTools] selection capture scale diag:', {
      imgW: img.naturalWidth, imgH: img.naturalHeight,
      innerW: window.innerWidth, innerH: window.innerHeight,
      devicePixelRatio: window.devicePixelRatio, scaleX, scaleY, rect
    });

    // Draw the selected portion
    ctx.drawImage(
      img,
      rect.x * scaleX,
      rect.y * scaleY,
      rect.width * scaleX,
      rect.height * scaleY,
      0,
      0,
      rect.width,
      rect.height
    );
    
    // Get cropped image as data URL
    const croppedDataUrl = canvas.toDataURL('image/png');
    
    // Send to background script for upload
    await browser.runtime.sendMessage({ 
      action: 'uploadSelection', 
      dataUrl: croppedDataUrl,
      tag
    });
    
  } catch (error) {
    console.error('[ImageTools] Failed to capture selection:', error);
  }
}

// Maximum number of recently used tags offered as chips
var IMAGETOOLS_RECENT_TAG_LIMIT = 8;

// Build the tag picker shared by the selection overlay and the capture
// preview: a free-text input plus chips for recently used tags. Recent tags
// come from the background (which holds the access token); the input is
// usable immediately and the chips appear once the lookup returns.
function createTagPicker() {
  const element = document.createElement('div');
  element.style.cssText = `
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 13px;
    color: #374151;
    text-align: left;
  `;

  const inputRow = document.createElement('div');
  inputRow.style.cssText = 'display: flex; gap: 6px; align-items: center;';

  const label = document.createElement('span');
  label.textContent = 'Tag:';
  label.style.cssText = 'font-weight: 500; white-space: nowrap;';

  const input = document.createElement('input');
  input.type = 'text';
  input.placeholder = 'New or recent tag (optional)';
  input.style.cssText = `
    flex: 1;
    min-width: 180px;
    padding: 6px 8px;
    border: 2px solid #e5e7eb;
    border-radius: 6px;
    font-size: 13px;
    color: #111827;
    background: white;
    box-sizing: border-box;
    outline: none;
  `;
  input.addEventListener('focus', () => input.style.borderColor = '#6366f1');
  input.addEventListener('blur', () => input.style.borderColor = '#e5e7eb');

  const clearButton = document.createElement('button');
  clearButton.type = 'button';
  clearButton.textContent = '×';
  clearButton.title = 'Clear tag';
  clearButton.style.cssText = `
    padding: 4px 9px;
    background: #e5e7eb;
    color: #374151;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    cursor: pointer;
  `;

  const chips = document.createElement('div');
  chips.style.cssText = 'display: flex; flex-wrap: wrap; gap: 4px; max-width: 420px;';

  inputRow.appendChild(label);
  inputRow.appendChild(input);
  inputRow.appendChild(clearButton);
  element.appendChild(inputRow);
  element.appendChild(chips);

  // Keep typing out of page-level keyboard shortcuts. Enter/Escape still
  // bubble so the overlay's own key handler can confirm/cancel.
  for (const evt of ['keydown', 'keyup', 'keypress']) {
    input.addEventListener(evt, (e) => {
      if (e.key !== 'Enter' && e.key !== 'Escape') e.stopPropagation();
    });
  }

  const highlightChips = () => {
    const value = input.value.trim();
    for (const chip of chips.children) {
      const active = chip.dataset.tag === value;
      chip.style.background = active ? '#6366f1' : '#eef2ff';
      chip.style.color = active ? 'white' : '#4338ca';
    }
  };

  let touched = false;
  input.addEventListener('input', () => { touched = true; highlightChips(); });
  clearButton.addEventListener('click', () => {
    touched = true;
    input.value = '';
    highlightChips();
  });

  browser.runtime.sendMessage({ action: 'getRecentTags' })
    .then((response) => {
      if (!response) return;
      // Default to the current tag unless the user already started typing
      if (!touched && response.currentTag) input.value = response.currentTag;
      for (const tag of (response.tags || []).slice(0, IMAGETOOLS_RECENT_TAG_LIMIT)) {
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.dataset.tag = tag;
        chip.textContent = tag;
        chip.title = `Tag as "${tag}"`;
        chip.style.cssText = `
          padding: 3px 10px;
          border: none;
          border-radius: 999px;
          font-size: 12px;
          cursor: pointer;
        `;
        chip.addEventListener('click', () => {
          touched = true;
          input.value = tag;
          highlightChips();
        });
        chips.appendChild(chip);
      }
      highlightChips();
    })
    .catch((error) => console.warn('[ImageTools] Recent tags lookup failed:', error));

  return {
    element,
    getTag: () => input.value.trim()
  };
}

// Show a modal with a preview of a captured image, a tag picker, and
// Upload / Discard buttons. Nothing is uploaded until the user confirms.
function showCapturePreview(dataUrl, filename, title) {
  cleanupCapturePreview();

  const backdrop = document.createElement('div');
  backdrop.id = 'imagetools-preview-backdrop';
  backdrop.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.6);
    z-index: 2147483647;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  `;

  const panel = document.createElement('div');
  panel.style.cssText = `
    background: white;
    border-radius: 10px;
    padding: 16px;
    max-width: min(900px, 90vw);
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    gap: 12px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.4);
    box-sizing: border-box;
  `;

  const heading = document.createElement('div');
  heading.style.cssText = 'font-size: 16px; font-weight: 600; color: #111827;';
  heading.textContent = title || 'Screenshot captured';

  // Scrollable so tall full-page captures can be inspected
  const imageWrap = document.createElement('div');
  imageWrap.style.cssText = `
    overflow: auto;
    max-height: 60vh;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    background: #f9fafb;
  `;
  const img = document.createElement('img');
  img.src = dataUrl;
  img.alt = 'Captured screenshot preview';
  img.style.cssText = 'display: block; width: 100%; height: auto;';
  imageWrap.appendChild(img);

  const tagPicker = createTagPicker();

  const status = document.createElement('div');
  status.style.cssText = 'font-size: 13px; color: #dc2626; display: none;';

  const buttonsRow = document.createElement('div');
  buttonsRow.style.cssText = 'display: flex; gap: 10px; justify-content: flex-end;';

  const uploadButton = document.createElement('button');
  uploadButton.textContent = '✓ Upload';
  styleOverlayButton(uploadButton, '#10b981', '#059669');

  const discardButton = document.createElement('button');
  discardButton.textContent = '✕ Discard';
  styleOverlayButton(discardButton, '#ef4444', '#dc2626');

  buttonsRow.appendChild(uploadButton);
  buttonsRow.appendChild(discardButton);

  panel.appendChild(heading);
  panel.appendChild(imageWrap);
  panel.appendChild(tagPicker.element);
  panel.appendChild(status);
  panel.appendChild(buttonsRow);
  backdrop.appendChild(panel);
  document.body.appendChild(backdrop);

  // Keep clicks inside the modal away from page-level handlers
  const blockPropagation = (e) => e.stopPropagation();
  for (const evt of ['mousedown', 'mouseup', 'click', 'pointerdown', 'pointerup']) {
    backdrop.addEventListener(evt, blockPropagation);
  }

  let uploading = false;

  const close = () => {
    document.removeEventListener('keydown', keyHandler);
    cleanupCapturePreview();
  };

  const upload = async () => {
    if (uploading) return;
    uploading = true;
    uploadButton.disabled = true;
    discardButton.disabled = true;
    uploadButton.textContent = 'Uploading…';
    status.style.display = 'none';

    try {
      const response = await browser.runtime.sendMessage({
        action: 'uploadCapture',
        dataUrl,
        filename,
        tag: tagPicker.getTag()
      });
      if (response && response.success) {
        close();
        return;
      }
      throw new Error((response && response.error) || 'Upload failed');
    } catch (error) {
      console.error('[ImageTools] Preview upload failed:', error);
      status.textContent = `Upload failed: ${error.message}`;
      status.style.display = 'block';
      uploadButton.textContent = '✓ Retry upload';
      uploadButton.disabled = false;
      discardButton.disabled = false;
      uploading = false;
    }
  };

  const keyHandler = (e) => {
    // A newer preview replaced this one - stop listening
    if (!backdrop.isConnected) {
      document.removeEventListener('keydown', keyHandler);
      return;
    }
    if (e.key === 'Escape' && !uploading) {
      e.preventDefault();
      close();
    } else if (e.key === 'Enter') {
      e.preventDefault();
      upload();
    }
  };

  uploadButton.addEventListener('click', upload);
  discardButton.addEventListener('click', close);
  document.addEventListener('keydown', keyHandler);
}

// Apply the shared overlay button style with a hover colour
function styleOverlayButton(button, background, hoverBackground) {
  button.type = 'button';
  button.style.cssText = `
    padding: 10px 20px;
    background: ${background};
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  `;
  button.onmouseover = () => button.style.background = hoverBackground;
  button.onmouseout = () => button.style.background = background;
}

// Remove the capture preview modal
function cleanupCapturePreview() {
  const backdrop = document.getElementById('imagetools-preview-backdrop');
  if (backdrop) backdrop.remove();
}

// Capture full page
async function captureFullPageCanvas() {
  // Save original scroll position at the start
  const originalScrollX = window.scrollX;
  const originalScrollY = window.scrollY;
  
  try {
    console.log('[ImageTools Content] Starting full page capture');
    
    // Get full page dimensions
    const fullWidth = Math.max(
      document.documentElement.scrollWidth,
      document.body.scrollWidth
    );
    const fullHeight = Math.max(
      document.documentElement.scrollHeight,
      document.body.scrollHeight
    );
    
    console.log('[ImageTools Content] Full page dimensions:', fullWidth, 'x', fullHeight);
    
    // Get viewport dimensions
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    
    console.log('[ImageTools Content] Viewport dimensions:', viewportWidth, 'x', viewportHeight);
    
    // Create canvas for full page. Its pixel size depends on the real
    // capture scale, which we only learn from the first captured tile
    // (see the device-emulation note in captureSelection). Sized lazily.
    const canvas = document.createElement('canvas');
    let ctx = null;
    let scaleX = 1;
    let scaleY = 1;
    let scaleResolved = false;

    // Calculate number of screenshots needed
    const cols = Math.ceil(fullWidth / viewportWidth);
    const rows = Math.ceil(fullHeight / viewportHeight);
    
    console.log('[ImageTools Content] Grid:', rows, 'rows x', cols, 'cols');
    
    // Capture screenshots in a grid
    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        const x = col * viewportWidth;
        const y = row * viewportHeight;
        
        // Scroll to position
        window.scrollTo(x, y);
        
        // Wait for scroll to complete and any lazy-loaded content
        // Browser APIs may have rate limits on captureVisibleTab
        // so we use a longer delay to avoid hitting limits
        await new Promise(resolve => setTimeout(resolve, 600));
        
        console.log('[ImageTools Content] Capturing tile', row, col, 'at', x, y);
        
        // Capture visible area with retry logic
        let dataUrl = null;
        let retries = 3;
        
        for (let attempt = 1; attempt <= retries; attempt++) {
          dataUrl = await browser.runtime.sendMessage({ 
            action: 'captureVisibleTab' 
          });
          
          if (dataUrl) {
            console.log('[ImageTools Content] Received dataUrl on attempt', attempt, ':', `${dataUrl.substring(0, 50)}... (length: ${dataUrl.length})`);
            break;
          } else {
            console.warn('[ImageTools Content] Attempt', attempt, 'failed, dataUrl is NULL');
            if (attempt < retries) {
              console.log('[ImageTools Content] Waiting 1 second before retry...');
              await new Promise(resolve => setTimeout(resolve, 1000));
            }
          }
        }
        
        if (!dataUrl) {
          throw new Error(`Failed to capture visible tab after ${retries} attempts - received null/undefined`);
        }
        
        // Load image and draw to canvas
        const img = await loadImage(dataUrl);

        // Resolve the capture scale once from the first tile and reuse it
        // for every tile and for the canvas size. Measuring per-tile would
        // break on the last (partial) row/col where dimensions differ.
        if (!scaleResolved) {
          scaleX = img.naturalWidth / viewportWidth;
          scaleY = img.naturalHeight / viewportHeight;
          canvas.width = Math.round(fullWidth * scaleX);
          canvas.height = Math.round(fullHeight * scaleY);
          ctx = canvas.getContext('2d');
          scaleResolved = true;
          console.log('[ImageTools] full-page capture scale diag:', {
            imgW: img.naturalWidth, imgH: img.naturalHeight,
            viewportWidth, viewportHeight,
            devicePixelRatio: window.devicePixelRatio,
            scaleX, scaleY,
            canvasW: canvas.width, canvasH: canvas.height
          });
        }

        ctx.drawImage(img, Math.round(x * scaleX), Math.round(y * scaleY));
      }
    }
    
    // Restore original scroll position
    window.scrollTo(originalScrollX, originalScrollY);
    
    console.log('[ImageTools Content] Full page capture complete');
    
    return { dataUrl: canvas.toDataURL('image/png') };
  } catch (error) {
    console.error('[ImageTools Content] Full page capture failed:', error);
    // Restore scroll position on error
    window.scrollTo(originalScrollX, originalScrollY);
    throw error;
  }
}

// Helper function to load image from data URL
function loadImage(dataUrl) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = dataUrl;
  });
}
