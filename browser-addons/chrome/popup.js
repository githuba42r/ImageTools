// ImageTools Popup Script (Chrome)

// Get build date from manifest (injected at build time)
const BUILD_DATE = '2026-02-19T05:54:11.123Z';  // Will be updated by build script

document.addEventListener('DOMContentLoaded', async () => {
  // Display version information
  displayVersionInfo();
  
  // Get DOM elements
  const initialSection = document.getElementById('initialSection');
  const connectSection = document.getElementById('connectSection');
  const captureSection = document.getElementById('captureSection');
  const showConnectBtn = document.getElementById('showConnectBtn');
  const backBtn = document.getElementById('backBtn');
  const connectionStringInput = document.getElementById('connectionString');
  const connectBtn = document.getElementById('connectBtn');
  const logoutBtn = document.getElementById('logoutBtn');
  const captureVisibleBtn = document.getElementById('captureVisibleBtn');
  const captureFullBtn = document.getElementById('captureFullBtn');
  const captureSelectionBtn = document.getElementById('captureSelectionBtn');
  
  // Check auth state on load
  await updateUI();
  
  // Show connect form button
  showConnectBtn.addEventListener('click', () => {
    initialSection.style.display = 'none';
    connectSection.style.display = 'block';
    connectionStringInput.focus();
  });
  
  // Back button
  backBtn.addEventListener('click', () => {
    connectSection.style.display = 'none';
    initialSection.style.display = 'block';
    connectionStringInput.value = '';
  });
  
  // Connect button click
  connectBtn.addEventListener('click', async () => {
    const connectionString = connectionStringInput.value.trim();
    if (!connectionString) {
      alert('Please enter a connection string');
      return;
    }
    
    try {
      // Decode base64 connection string
      const jsonString = atob(connectionString);
      const connectionData = JSON.parse(jsonString);
      
      if (!connectionData.code || !connectionData.instance) {
        throw new Error('Invalid connection string format');
      }
      
      connectBtn.disabled = true;
      connectBtn.textContent = 'Connecting...';
      
      // Send authorization request to background script
      const response = await chrome.runtime.sendMessage({
        action: 'authorize',
        authorizationCode: connectionData.code,
        instanceUrl: connectionData.instance
      });
      
      if (response.success) {
        connectionStringInput.value = '';
        await updateUI();
      } else {
        alert(`Failed to connect: ${response.error}`);
      }
    } catch (error) {
      console.error('Connection error:', error);
      alert(`Error: ${error.message || 'Invalid connection string'}`);
    } finally {
      connectBtn.disabled = false;
      connectBtn.textContent = 'Connect';
    }
  });
  
  // Allow Enter key to submit connection
  connectionStringInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      connectBtn.click();
    }
  });
  
  // Logout button
  logoutBtn.addEventListener('click', async () => {
    if (confirm('Disconnect from ImageTools?')) {
      await chrome.runtime.sendMessage({ action: 'logout' });
      await updateUI();
    }
  });
  
  // Capture buttons
  captureVisibleBtn.addEventListener('click', async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    await chrome.runtime.sendMessage({ action: 'captureVisible', tabId: tab.id });
    window.close();
  });
  
  captureFullBtn.addEventListener('click', async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    await chrome.runtime.sendMessage({ action: 'captureFull', tabId: tab.id });
    window.close();
  });
  
  captureSelectionBtn.addEventListener('click', async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    await chrome.runtime.sendMessage({ action: 'captureSelection', tabId: tab.id });
    window.close();
  });
  
  async function updateUI() {
    try {
      const response = await chrome.runtime.sendMessage({ action: 'getAuthState' });
      const { authState } = response;
      
      if (authState && authState.accessToken && authState.instanceUrl) {
        // Validate token with backend to check if still authorized
        // Use a timeout to prevent hanging
        try {
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 3000); // 3 second timeout
          
          const validateResponse = await fetch(`${authState.instanceUrl}/api/v1/addon/validate`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              access_token: authState.accessToken
            }),
            signal: controller.signal
          });
          
          clearTimeout(timeoutId);
          
          if (validateResponse.ok) {
            const validationData = await validateResponse.json();
            
            if (!validationData.valid) {
              // Token is no longer valid - clear auth state and show connect screen
              console.log('[Popup] Token no longer valid, clearing auth state');
              await chrome.runtime.sendMessage({ action: 'logout' });
              initialSection.style.display = 'block';
              connectSection.style.display = 'none';
              captureSection.style.display = 'none';
              return;
            }
          } else if (validateResponse.status === 401) {
            // Unauthorized - token revoked, clear auth state
            console.log('[Popup] Token revoked (401), clearing auth state');
            await chrome.runtime.sendMessage({ action: 'logout' });
            initialSection.style.display = 'block';
            connectSection.style.display = 'none';
            captureSection.style.display = 'none';
            return;
          }
        } catch (error) {
          console.warn('[Popup] Failed to validate token:', error);
          // Continue showing UI even if validation fails (network issue or timeout)
        }
        
        // Connected - show capture buttons
        initialSection.style.display = 'none';
        connectSection.style.display = 'none';
        captureSection.style.display = 'block';
        
        // Check if current tab can be captured
        const tabCheck = await chrome.runtime.sendMessage({ action: 'checkCurrentTab' });
        
        if (!tabCheck.canCapture) {
          // Disable capture buttons and show message
          captureVisibleBtn.disabled = true;
          captureFullBtn.disabled = true;
          captureSelectionBtn.disabled = true;
          
          // Add warning message if not already present
          let warningMsg = document.getElementById('captureWarning');
          if (!warningMsg) {
            warningMsg = document.createElement('div');
            warningMsg.id = 'captureWarning';
            warningMsg.style.cssText = 'background: #fef3c7; border: 1px solid #f59e0b; border-radius: 6px; padding: 12px; margin-bottom: 15px; font-size: 13px; color: #92400e; line-height: 1.5;';
            
            if (tabCheck.isImageTools) {
              warningMsg.innerHTML = '<strong>⚠️ Cannot capture</strong><br>Screenshots are disabled on ImageTools pages for security.';
            } else if (tabCheck.isRestricted) {
              warningMsg.innerHTML = '<strong>⚠️ Cannot capture</strong><br>Screenshots are disabled on browser internal pages.';
            } else {
              warningMsg.innerHTML = '<strong>⚠️ Cannot capture</strong><br>This page cannot be captured.';
            }
            
            captureSection.insertBefore(warningMsg, captureSection.firstChild);
          }
        } else {
          // Enable capture buttons
          captureVisibleBtn.disabled = false;
          captureFullBtn.disabled = false;
          captureSelectionBtn.disabled = false;
          
          // Remove warning message if present
          const warningMsg = document.getElementById('captureWarning');
          if (warningMsg) {
            warningMsg.remove();
          }
        }
      } else {
        // Not connected - show initial screen
        initialSection.style.display = 'block';
        connectSection.style.display = 'none';
        captureSection.style.display = 'none';
      }
    } catch (error) {
      console.error('[Popup] Error updating UI:', error);
      // On error, show initial connect screen
      initialSection.style.display = 'block';
      connectSection.style.display = 'none';
      captureSection.style.display = 'none';
    }
  }
  
  function displayVersionInfo() {
    // Get version from manifest
    const manifest = chrome.runtime.getManifest();
    const version = manifest.version;
    
    // Format build date
    let buildDateStr = 'Unknown';
    try {
      const buildDate = new Date(BUILD_DATE);
      buildDateStr = buildDate.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
      });
    } catch (e) {
      console.error('Error formatting build date:', e);
    }
    
    // Update UI
    document.getElementById('versionText').textContent = `v${version}`;
    document.getElementById('buildDateText').textContent = buildDateStr;
  }
});
