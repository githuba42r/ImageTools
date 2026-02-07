// ImageTools Content Script (simplified for brevity)

// Listen for messages from background script
browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[ImageTools Content] Received message:', message.action);
  
  if (message.action === 'startSelectionCapture') {
    initSelectionCapture();
    sendResponse({ success: true });
    return true;
  } else if (message.action === 'captureFullPage') {
    // Handle async operation
    captureFullPageCanvas()
      .then(result => {
        console.log('[ImageTools Content] Sending response back to background');
        sendResponse(result);
      })
      .catch(error => {
        console.error('[ImageTools Content] Error in captureFullPageCanvas:', error);
        sendResponse({ error: error.message });
      });
    return true; // Keep channel open for async response
  }
  
  return false;
});

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
    z-index: 1000001;
    gap: 10px;
  `;
  
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
  
  actionsContainer.appendChild(okButton);
  actionsContainer.appendChild(reselectButton);
  actionsContainer.appendChild(cancelButton);
  
  document.body.appendChild(overlay);
  document.body.appendChild(selectionBox);
  document.body.appendChild(actionsContainer);
  
  let startX = null;
  let startY = null;
  let isDrawing = false;
  let currentRect = null;
  
  // Mouse down - start selection
  overlay.addEventListener('mousedown', (e) => {
    if (actionsContainer.style.display === 'flex') {
      // Already have a selection, ignore
      return;
    }
    
    isDrawing = true;
    startX = e.clientX;
    startY = e.clientY;
    selectionBox.style.left = startX + 'px';
    selectionBox.style.top = startY + 'px';
    selectionBox.style.width = '0px';
    selectionBox.style.height = '0px';
    selectionBox.style.display = 'block';
  });
  
  // Mouse move - draw selection
  overlay.addEventListener('mousemove', (e) => {
    if (!isDrawing || startX === null) return;
    
    const currentX = e.clientX;
    const currentY = e.clientY;
    const width = Math.abs(currentX - startX);
    const height = Math.abs(currentY - startY);
    const left = Math.min(startX, currentX);
    const top = Math.min(startY, currentY);
    
    selectionBox.style.left = left + 'px';
    selectionBox.style.top = top + 'px';
    selectionBox.style.width = width + 'px';
    selectionBox.style.height = height + 'px';
  });
  
  // Mouse up - finish selection and show actions
  overlay.addEventListener('mouseup', (e) => {
    if (!isDrawing) return;
    
    isDrawing = false;
    
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
      
      // Position action buttons below the selection box
      const boxBottom = currentRect.y + currentRect.height;
      const boxLeft = currentRect.x;
      
      actionsContainer.style.left = boxLeft + 'px';
      actionsContainer.style.top = (boxBottom + 10) + 'px';
      actionsContainer.style.display = 'flex';
      
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
  okButton.addEventListener('click', async () => {
    if (currentRect) {
      // Hide UI immediately
      actionsContainer.style.display = 'none';
      overlay.style.display = 'none';
      selectionBox.style.display = 'none';
      
      // Wait a moment for UI to disappear
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Capture the selection
      await captureSelection(currentRect);
      
      // Clean up
      cleanupSelectionUI();
    }
  });
  
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
  
  // ESC to cancel
  const escapeHandler = (e) => {
    if (e.key === 'Escape') {
      cleanupSelectionUI();
      document.removeEventListener('keydown', escapeHandler);
    }
  };
  document.addEventListener('keydown', escapeHandler);
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
async function captureSelection(rect) {
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
    
    // Account for device pixel ratio
    const dpr = window.devicePixelRatio || 1;
    
    // Draw the selected portion
    ctx.drawImage(
      img,
      rect.x * dpr, 
      rect.y * dpr, 
      rect.width * dpr, 
      rect.height * dpr,
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
      dataUrl: croppedDataUrl 
    });
    
  } catch (error) {
    console.error('[ImageTools] Failed to capture selection:', error);
  }
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
    
    // Create canvas for full page
    const canvas = document.createElement('canvas');
    canvas.width = fullWidth;
    canvas.height = fullHeight;
    const ctx = canvas.getContext('2d');
    
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
        ctx.drawImage(img, x, y);
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
