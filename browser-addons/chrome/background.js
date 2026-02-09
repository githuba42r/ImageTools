// ImageTools Chrome Background Service Worker
// (Manifest V3)

// Configuration
const API_ENDPOINTS = {
  token: '/api/v1/addon/token',
  refresh: '/api/v1/addon/refresh',
  upload: '/api/v1/addon/upload',
  unpair: '/api/v1/addon/unpair'
};

// Auth state is stored in chrome.storage.local
// We don't maintain it in memory due to service worker lifecycle

// Initialize addon
chrome.runtime.onInstalled.addListener(async () => {
  console.log('[ImageTools] Addon installed');
  
  // Create context menu items
  createContextMenus();
});

// Service worker startup
chrome.runtime.onStartup.addListener(async () => {
  createContextMenus();
});

// Create context menus
function createContextMenus() {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: 'imagetools-capture-visible',
      title: 'Capture Visible Area',
      contexts: ['page']
    });
    
    chrome.contextMenus.create({
      id: 'imagetools-capture-full',
      title: 'Capture Full Page',
      contexts: ['page']
    });
    
    chrome.contextMenus.create({
      id: 'imagetools-capture-selection',
      title: 'Capture Selection',
      contexts: ['page']
    });
  });
}

// Context menu click handler
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  console.log('[ImageTools] Context menu clicked:', info.menuItemId);
  
  const isAuth = await isAuthenticated();
  if (!isAuth) {
    // Open popup to authenticate
    chrome.action.openPopup();
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
async function isAuthenticated() {
  const result = await chrome.storage.local.get(['authState']);
  const authState = result.authState;
  
  if (!authState || !authState.accessToken || !authState.instanceUrl) {
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

// Get auth state
async function getAuthState() {
  const result = await chrome.storage.local.get(['authState']);
  return result.authState || {
    instanceUrl: null,
    accessToken: null,
    refreshToken: null,
    accessExpiresAt: null,
    refreshExpiresAt: null
  };
}

// Save auth state
async function saveAuthState(authState) {
  await chrome.storage.local.set({ authState });
  console.log('[ImageTools] Saved auth state to storage');
}

// Get browser information
function getBrowserInfo() {
  const userAgent = navigator.userAgent;
  let browserName = 'Chrome';
  let browserVersion = '';
  let osName = '';
  
  // Detect browser
  if (userAgent.indexOf('Edg/') > -1) {
    browserName = 'Edge';
    browserVersion = userAgent.match(/Edg\/([\d.]+)/)?.[1] || '';
  } else if (userAgent.indexOf('Chrome/') > -1) {
    browserName = 'Chrome';
    browserVersion = userAgent.match(/Chrome\/([\d.]+)/)?.[1] || '';
  } else if (userAgent.indexOf('Firefox/') > -1) {
    browserName = 'Firefox';
    browserVersion = userAgent.match(/Firefox\/([\d.]+)/)?.[1] || '';
  }
  
  // Detect OS
  if (userAgent.indexOf('Win') > -1) {
    osName = 'Windows';
  } else if (userAgent.indexOf('Mac') > -1) {
    osName = 'macOS';
  } else if (userAgent.indexOf('Linux') > -1) {
    osName = 'Linux';
  } else if (userAgent.indexOf('Android') > -1) {
    osName = 'Android';
  } else if (userAgent.indexOf('iOS') > -1 || userAgent.indexOf('iPhone') > -1 || userAgent.indexOf('iPad') > -1) {
    osName = 'iOS';
  }
  
  return {
    browserName,
    browserVersion,
    osName,
    userAgent
  };
}

// Exchange authorization code for tokens
async function exchangeAuthCode(authorizationCode, instanceUrl) {
  try {
    const browserInfo = getBrowserInfo();
    
    const response = await fetch(`${instanceUrl}${API_ENDPOINTS.token}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        authorization_code: authorizationCode,
        browser_name: browserInfo.browserName,
        browser_version: browserInfo.browserVersion,
        os_name: browserInfo.osName,
        user_agent: browserInfo.userAgent
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }
    
    const data = await response.json();
    
    // Save auth state
    const authState = {
      instanceUrl: data.instance_url,
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      accessExpiresAt: data.access_expires_at,
      refreshExpiresAt: data.refresh_expires_at
    };
    
    await saveAuthState(authState);
    console.log('[ImageTools] Successfully authenticated');
    return true;
  } catch (error) {
    console.error('[ImageTools] Failed to exchange auth code:', error);
    throw error;
  }
}

// Refresh access token
async function refreshAccessToken() {
  const authState = await getAuthState();
  
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
    
    await saveAuthState(authState);
    console.log('[ImageTools] Refreshed access token');
    return true;
  } catch (error) {
    console.error('[ImageTools] Failed to refresh token:', error);
    throw error;
  }
}

// Check if URL is ImageTools webapp (should not be captured)
async function isImageToolsPage(url) {
  if (!url) return false;
  
  try {
    const urlObj = new URL(url);
    const authState = await getAuthState();
    
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
async function validateTabForCapture(tab) {
  // Check if it's an ImageTools page
  if (await isImageToolsPage(tab.url)) {
    throw new Error('Cannot capture screenshots of ImageTools webapp');
  }
  
  // Check for restricted URLs
  if (tab.url.startsWith('chrome://') || 
      tab.url.startsWith('chrome-extension://') ||
      tab.url.startsWith('about:')) {
    throw new Error('Cannot capture browser internal pages');
  }
  
  return true;
}

// Capture visible area
async function captureVisibleArea(tab) {
  try {
    console.log('[ImageTools] Capturing visible area');
    
    // Validate tab before capture
    await validateTabForCapture(tab);
    
    const dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, { format: 'png' });
    
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
    await validateTabForCapture(tab);
    
    console.log('[ImageTools] Injecting content script');
    
    // Inject content script
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ['content.js']
    });
    
    console.log('[ImageTools] Content script injected, sending captureFullPage message');
    
    // Request full page capture from content script
    const response = await chrome.tabs.sendMessage(tab.id, { action: 'captureFullPage' });
    
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
    await validateTabForCapture(tab);
    
    // Inject content script
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ['content.js']
    });
    
    // Request selection capture from content script
    await chrome.tabs.sendMessage(tab.id, { action: 'startSelectionCapture' });
  } catch (error) {
    console.error('[ImageTools] Failed to start selection capture:', error);
    showNotification('Failed to start selection', error.message);
  }
}

// Upload screenshot to ImageTools
async function uploadScreenshot(blob, filename) {
  try {
    console.log('[ImageTools] Uploading screenshot:', filename);
    
    // Get auth state
    let authState = await getAuthState();
    
    // Check auth and refresh if needed
    if (!await isAuthenticated()) {
      await refreshAccessToken();
      authState = await getAuthState();
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
  chrome.notifications.create({
    type: 'basic',
    iconUrl: 'icons/icon-48.png',
    title: title,
    message: message
  });
}

// Listen for messages from popup and content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[ImageTools] Received message:', message);
  
  if (message.action === 'authorize') {
    exchangeAuthCode(message.authorizationCode, message.instanceUrl)
      .then(() => sendResponse({ success: true }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Keep channel open for async response
  } else if (message.action === 'getAuthState') {
    getAuthState()
      .then(authState => sendResponse({ authState }))
      .catch(error => sendResponse({ authState: null, error: error.message }));
    return true;
  } else if (message.action === 'checkCurrentTab') {
    chrome.tabs.query({ active: true, currentWindow: true })
      .then(async tabs => {
        if (tabs.length > 0) {
          const isImageTools = await isImageToolsPage(tabs[0].url);
          const isRestricted = tabs[0].url.startsWith('chrome://') || 
                              tabs[0].url.startsWith('chrome-extension://') ||
                              tabs[0].url.startsWith('about:');
          sendResponse({ 
            canCapture: !isImageTools && !isRestricted,
            isImageTools: isImageTools,
            isRestricted: isRestricted,
            url: tabs[0].url
          });
        } else {
          sendResponse({ canCapture: false });
        }
      })
      .catch(error => sendResponse({ canCapture: false, error: error.message }));
    return true;
  } else if (message.action === 'logout') {
    // Handle logout asynchronously
    (async () => {
      try {
        // Notify web app before clearing local state
        const authState = await getAuthState();
        
        if (authState.accessToken && authState.instanceUrl) {
          try {
            // Call unpair endpoint to notify web app
            await fetch(`${authState.instanceUrl}${API_ENDPOINTS.unpair}`, {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${authState.accessToken}`
              }
            });
            console.log('[ImageTools] Successfully notified web app of unpair');
          } catch (error) {
            console.error('[ImageTools] Failed to notify web app of unpair:', error);
            // Continue with logout even if notification fails
          }
        }
        
        // Clear local auth state
        const emptyAuthState = {
          instanceUrl: null,
          accessToken: null,
          refreshToken: null,
          accessExpiresAt: null,
          refreshExpiresAt: null
        };
        await saveAuthState(emptyAuthState);
        sendResponse({ success: true });
      } catch (error) {
        console.error('[ImageTools] Logout error:', error);
        sendResponse({ success: false, error: error.message });
      }
    })();
    return true; // Keep message channel open for async response
  } else if (message.action === 'uploadSelection') {
    dataUrlToBlob(message.dataUrl)
      .then(blob => uploadScreenshot(blob, `screenshot-selection-${Date.now()}.png`))
      .then(() => sendResponse({ success: true }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  } else if (message.action === 'captureVisibleTab') {
    // Content script is requesting a capture of its own tab
    // Use sender.tab if available, otherwise query for active tab
    console.log('[ImageTools] captureVisibleTab requested, sender.tab:', sender.tab ? sender.tab.id : 'none');
    
    if (sender.tab && sender.tab.windowId) {
      console.log('[ImageTools] Using sender windowId:', sender.tab.windowId);
      chrome.tabs.captureVisibleTab(sender.tab.windowId, { format: 'png' })
        .then(dataUrl => {
          console.log('[ImageTools] Captured visible tab, dataUrl length:', dataUrl ? dataUrl.length : 0);
          sendResponse(dataUrl);
        })
        .catch(error => {
          console.error('[ImageTools] Failed to capture visible tab (sender path):', error);
          sendResponse(null);
        });
    } else {
      console.log('[ImageTools] No sender.tab, using active tab query');
      chrome.tabs.query({ active: true, currentWindow: true })
        .then(tabs => {
          console.log('[ImageTools] Found tabs:', tabs.length);
          if (tabs.length > 0) {
            console.log('[ImageTools] Using tab windowId:', tabs[0].windowId);
            return chrome.tabs.captureVisibleTab(tabs[0].windowId, { format: 'png' });
          }
          return null;
        })
        .then(dataUrl => {
          console.log('[ImageTools] Captured visible tab (fallback), dataUrl length:', dataUrl ? dataUrl.length : 0);
          sendResponse(dataUrl);
        })
        .catch(error => {
          console.error('[ImageTools] Failed to capture visible tab (query path):', error);
          sendResponse(null);
        });
    }
    return true;
  } else if (message.action === 'captureVisible') {
    chrome.tabs.query({ active: true, currentWindow: true })
      .then(tabs => {
        if (tabs.length > 0) {
          return captureVisibleArea(tabs[0]);
        }
      })
      .then(() => sendResponse({ success: true }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  } else if (message.action === 'captureFull') {
    chrome.tabs.query({ active: true, currentWindow: true })
      .then(tabs => {
        if (tabs.length > 0) {
          return captureFullPage(tabs[0]);
        }
      })
      .then(() => sendResponse({ success: true }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  } else if (message.action === 'captureSelection') {
    chrome.tabs.query({ active: true, currentWindow: true })
      .then(tabs => {
        if (tabs.length > 0) {
          return captureSelection(tabs[0]);
        }
      })
      .then(() => sendResponse({ success: true }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }
  
  return false;
});
