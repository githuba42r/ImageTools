// ImageTools Firefox Background Script

// Configuration
const API_ENDPOINTS = {
  token: '/api/v1/addon/token',
  refresh: '/api/v1/addon/refresh',
  upload: '/api/v1/addon/upload'
};

// Auth state
let authState = {
  instanceUrl: null,
  accessToken: null,
  refreshToken: null,
  accessExpiresAt: null,
  refreshExpiresAt: null
};

// Initialize addon
browser.runtime.onInstalled.addListener(async () => {
  console.log('[ImageTools] Addon installed');
  
  // Load saved auth state
  await loadAuthState();
  
  // Create context menu items
  createContextMenus();
});

// Load auth state from storage
async function loadAuthState() {
  try {
    const result = await browser.storage.local.get(['authState']);
    if (result.authState) {
      authState = result.authState;
      console.log('[ImageTools] Loaded auth state from storage');
    }
  } catch (error) {
    console.error('[ImageTools] Failed to load auth state:', error);
  }
}

// Save auth state to storage
async function saveAuthState() {
  try {
    await browser.storage.local.set({ authState });
    console.log('[ImageTools] Saved auth state to storage');
  } catch (error) {
    console.error('[ImageTools] Failed to save auth state:', error);
  }
}

// Create context menus
function createContextMenus() {
  browser.contextMenus.removeAll();
  
  browser.contextMenus.create({
    id: 'imagetools-capture-visible',
    title: 'Capture Visible Area',
    contexts: ['page']
  });
  
  browser.contextMenus.create({
    id: 'imagetools-capture-full',
    title: 'Capture Full Page',
    contexts: ['page']
  });
  
  browser.contextMenus.create({
    id: 'imagetools-capture-selection',
    title: 'Capture Selection',
    contexts: ['page']
  });
}

// Context menu click handler
browser.contextMenus.onClicked.addListener(async (info, tab) => {
  console.log('[ImageTools] Context menu clicked:', info.menuItemId);
  
  if (!isAuthenticated()) {
    // Show popup to authenticate
    await browser.browserAction.openPopup();
    return;
  }
  
  switch (info.menuItemId) {
    case 'imagetools-capture-visible':
      await captureVisibleArea(tab);
      break;
    case 'imagetools-capture-full':
      await captureFullPage(tab);
      break;
    case 'imagetools-capture-selection':
      await captureSelection(tab);
      break;
  }
});

// Check if authenticated
function isAuthenticated() {
  if (!authState.accessToken || !authState.instanceUrl) {
    return false;
  }
  
  // Check if token expired
  if (authState.accessExpiresAt) {
    const expiresAt = new Date(authState.accessExpiresAt);
    if (expiresAt < new Date()) {
      return false;
    }
  }
  
  return true;
}

// Exchange authorization code for tokens
async function exchangeAuthCode(authorizationCode, instanceUrl) {
  try {
    const response = await fetch(`${instanceUrl}${API_ENDPOINTS.token}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        authorization_code: authorizationCode
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }
    
    const data = await response.json();
    
    // Save auth state
    authState = {
      instanceUrl: data.instance_url,
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      accessExpiresAt: data.access_expires_at,
      refreshExpiresAt: data.refresh_expires_at
    };
    
    await saveAuthState();
    console.log('[ImageTools] Successfully authenticated');
    return true;
  } catch (error) {
    console.error('[ImageTools] Failed to exchange auth code:', error);
    throw error;
  }
}

// Refresh access token
async function refreshAccessToken() {
  if (!authState.refreshToken || !authState.instanceUrl) {
    throw new Error('No refresh token available');
  }
  
  try {
    const response = await fetch(`${authState.instanceUrl}${API_ENDPOINTS.refresh}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        refresh_token: authState.refreshToken
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }
    
    const data = await response.json();
    
    // Update auth state
    authState.accessToken = data.access_token;
    authState.accessExpiresAt = data.access_expires_at;
    
    await saveAuthState();
    console.log('[ImageTools] Refreshed access token');
    return true;
  } catch (error) {
    console.error('[ImageTools] Failed to refresh token:', error);
    throw error;
  }
}

// Check if URL is ImageTools webapp (should not be captured)
function isImageToolsPage(url) {
  if (!url) return false;
  
  try {
    const urlObj = new URL(url);
    
    // If we have an instance URL, check if current page matches it
    if (!authState.instanceUrl) return false;
    
    const instanceUrl = new URL(authState.instanceUrl);
    
    // Check if hostname matches (ImageTools frontend and backend are on same host)
    // This catches both backend (port 8000) and frontend (port 5173) URLs
    return urlObj.hostname === instanceUrl.hostname;
  } catch (error) {
    return false;
  }
}

// Validate tab before capture
function validateTabForCapture(tab) {
  // Check if it's an ImageTools page
  if (isImageToolsPage(tab.url)) {
    throw new Error('Cannot capture screenshots of ImageTools webapp');
  }
  
  // Check for restricted URLs
  if (tab.url.startsWith('about:') || 
      tab.url.startsWith('moz-extension://')) {
    throw new Error('Cannot capture browser internal pages');
  }
  
  return true;
}

// Capture visible area
async function captureVisibleArea(tab) {
  try {
    console.log('[ImageTools] Capturing visible area');
    
    // Validate tab before capture
    validateTabForCapture(tab);
    
    const dataUrl = await browser.tabs.captureVisibleTab(tab.windowId, { format: 'png' });
    
    // Convert data URL to blob
    const blob = await dataUrlToBlob(dataUrl);
    
    // Upload to ImageTools
    await uploadScreenshot(blob, `screenshot-${Date.now()}.png`);
  } catch (error) {
    console.error('[ImageTools] Failed to capture visible area:', error);
    showNotification('Failed to capture screenshot', error.message);
  }
}

// Capture full page
async function captureFullPage(tab) {
  try {
    console.log('[ImageTools] Capturing full page for tab:', tab.id);
    
    // Validate tab before capture
    validateTabForCapture(tab);
    
    console.log('[ImageTools] Injecting content script');
    
    // Inject content script to get full page dimensions
    await browser.tabs.executeScript(tab.id, { file: 'content.js' });
    
    console.log('[ImageTools] Content script injected, sending captureFullPage message');
    
    // Request full page capture from content script
    const response = await browser.tabs.sendMessage(tab.id, { action: 'captureFullPage' });
    
    console.log('[ImageTools] Received response from content script:', response ? 'has data' : 'no data');
    
    if (response && response.dataUrl) {
      console.log('[ImageTools] Converting dataUrl to blob');
      const blob = await dataUrlToBlob(response.dataUrl);
      console.log('[ImageTools] Blob size:', blob.size, 'bytes');
      await uploadScreenshot(blob, `screenshot-full-${Date.now()}.png`);
    } else {
      console.error('[ImageTools] No dataUrl in response:', response);
      showNotification('Full page capture failed', 'No image data received from content script');
    }
  } catch (error) {
    console.error('[ImageTools] Failed to capture full page:', error);
    showNotification('Failed to capture full page', error.message);
  }
}

// Capture selection
async function captureSelection(tab) {
  try {
    console.log('[ImageTools] Initiating selection capture');
    
    // Validate tab before capture
    validateTabForCapture(tab);
    
    // Inject content script
    await browser.tabs.executeScript(tab.id, { file: 'content.js' });
    
    // Request selection capture from content script
    await browser.tabs.sendMessage(tab.id, { action: 'startSelectionCapture' });
  } catch (error) {
    console.error('[ImageTools] Failed to start selection capture:', error);
    showNotification('Failed to start selection', error.message);
  }
}

// Upload screenshot to ImageTools
async function uploadScreenshot(blob, filename) {
  try {
    console.log('[ImageTools] Uploading screenshot:', filename);
    
    // Check auth and refresh if needed
    if (!isAuthenticated()) {
      await refreshAccessToken();
    }
    
    const formData = new FormData();
    formData.append('file', blob, filename);
    
    const response = await fetch(`${authState.instanceUrl}${API_ENDPOINTS.upload}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authState.accessToken}`
      },
      body: formData
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }
    
    const data = await response.json();
    console.log('[ImageTools] Upload successful:', data);
    
    // Show success notification
    showNotification('Screenshot uploaded!', 'Image successfully uploaded to ImageTools');
  } catch (error) {
    console.error('[ImageTools] Upload failed:', error);
    showNotification('Upload failed', error.message);
    throw error;
  }
}

// Convert data URL to Blob
async function dataUrlToBlob(dataUrl) {
  const response = await fetch(dataUrl);
  return await response.blob();
}

// Show notification
function showNotification(title, message) {
  browser.notifications.create({
    type: 'basic',
    iconUrl: 'icons/icon-48.png',
    title: title,
    message: message
  });
}

// Listen for messages from popup
browser.runtime.onMessage.addListener(async (message, sender, sendResponse) => {
  console.log('[ImageTools] Received message:', message);
  
  if (message.action === 'authorize') {
    try {
      await exchangeAuthCode(message.authorizationCode, message.instanceUrl);
      return Promise.resolve({ success: true });
    } catch (error) {
      return Promise.resolve({ success: false, error: error.message });
    }
  } else if (message.action === 'getAuthState') {
    return Promise.resolve({ authState });
  } else if (message.action === 'checkCurrentTab') {
    try {
      const tabs = await browser.tabs.query({ active: true, currentWindow: true });
      if (tabs.length > 0) {
        const isImageTools = isImageToolsPage(tabs[0].url);
        const isRestricted = tabs[0].url.startsWith('about:') || 
                            tabs[0].url.startsWith('moz-extension://');
        return Promise.resolve({ 
          canCapture: !isImageTools && !isRestricted,
          isImageTools: isImageTools,
          isRestricted: isRestricted,
          url: tabs[0].url
        });
      } else {
        return Promise.resolve({ canCapture: false });
      }
    } catch (error) {
      return Promise.resolve({ canCapture: false, error: error.message });
    }
  } else if (message.action === 'logout') {
    authState = {
      instanceUrl: null,
      accessToken: null,
      refreshToken: null,
      accessExpiresAt: null,
      refreshExpiresAt: null
    };
    await saveAuthState();
    return Promise.resolve({ success: true });
  } else if (message.action === 'uploadSelection') {
    try {
      const blob = await dataUrlToBlob(message.dataUrl);
      await uploadScreenshot(blob, `screenshot-selection-${Date.now()}.png`);
      return Promise.resolve({ success: true });
    } catch (error) {
      return Promise.resolve({ success: false, error: error.message });
    }
  } else if (message.action === 'captureVisibleTab') {
    try {
      // Content script is requesting a capture of its own tab
      // Use sender.tab if available, otherwise query for active tab
      let windowId;
      
      if (sender.tab && sender.tab.windowId) {
        windowId = sender.tab.windowId;
        console.log('[ImageTools] Using sender tab windowId:', windowId);
      } else {
        const tabs = await browser.tabs.query({ active: true, currentWindow: true });
        if (tabs.length > 0) {
          windowId = tabs[0].windowId;
          console.log('[ImageTools] Using active tab windowId:', windowId);
        } else {
          console.error('[ImageTools] No tab found for capture');
          return Promise.resolve(null);
        }
      }
      
      const dataUrl = await browser.tabs.captureVisibleTab(windowId, { format: 'png' });
      console.log('[ImageTools] Captured visible tab, dataUrl length:', dataUrl ? dataUrl.length : 0);
      return Promise.resolve(dataUrl);
    } catch (error) {
      console.error('[ImageTools] Failed to capture visible tab:', error);
      return Promise.resolve(null);
    }
  } else if (message.action === 'captureVisible') {
    const tabs = await browser.tabs.query({ active: true, currentWindow: true });
    if (tabs.length > 0) {
      await captureVisibleArea(tabs[0]);
    }
    return Promise.resolve({ success: true });
  } else if (message.action === 'captureFull') {
    const tabs = await browser.tabs.query({ active: true, currentWindow: true });
    if (tabs.length > 0) {
      await captureFullPage(tabs[0]);
    }
    return Promise.resolve({ success: true });
  } else if (message.action === 'captureSelection') {
    const tabs = await browser.tabs.query({ active: true, currentWindow: true });
    if (tabs.length > 0) {
      await captureSelection(tabs[0]);
    }
    return Promise.resolve({ success: true });
  }
});
