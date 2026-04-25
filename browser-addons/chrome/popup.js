// ImageTools Popup Script (Chrome)

// Get build date from manifest (injected at build time)
const BUILD_DATE = '2026-04-25T13:28:18.180Z';  // Will be updated by build script

const TAG_KEY = 'imagetools_current_tag';

async function loadCurrentTag() {
  const got = await chrome.storage.local.get([TAG_KEY]);
  const input = document.getElementById('current-tag');
  if (input) input.value = got[TAG_KEY] || '';
}

async function persistCurrentTag(tag) {
  if (tag) {
    await chrome.storage.local.set({ [TAG_KEY]: tag });
  } else {
    await chrome.storage.local.remove(TAG_KEY);
  }
}

async function ensureUserId(authState) {
  if (!authState || !authState.accessToken || !authState.instanceUrl) return null;
  if (authState.userId) return authState.userId;
  // Backfill for addons paired before user_id was stashed: hit /validate.
  try {
    const r = await fetch(
      `${authState.instanceUrl}/api/v1/addon/validate`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authState.accessToken}`,
        },
        body: JSON.stringify({ access_token: authState.accessToken }),
      }
    );
    if (!r.ok) return null;
    const data = await r.json();
    if (!data.valid || !data.user_id) return null;
    authState.userId = data.user_id;
    await chrome.storage.local.set({ authState });
    return data.user_id;
  } catch (e) {
    return null;
  }
}

async function refreshTagSuggestions(authState) {
  if (!authState || !authState.instanceUrl) return;
  const userId = await ensureUserId(authState);
  if (!userId) return;
  try {
    const r = await fetch(
      `${authState.instanceUrl}/api/v1/users/${userId}/tags`,
      { headers: { 'Authorization': `Bearer ${authState.accessToken}` } }
    );
    if (!r.ok) return;
    const tags = await r.json();
    const dl = document.getElementById('tag-suggestions');
    if (!dl) return;
    dl.innerHTML = '';
    for (const { tag } of tags) {
      const opt = document.createElement('option');
      opt.value = tag;
      dl.appendChild(opt);
    }
  } catch (e) {
    console.warn('[ImageTools] tag suggestions fetch failed', e);
  }
}

function attachTagHandlers() {
  const input = document.getElementById('current-tag');
  const clearBtn = document.getElementById('clear-tag');
  if (input) {
    input.addEventListener('change', e => persistCurrentTag(e.target.value.trim()));
    input.addEventListener('blur', e => persistCurrentTag(e.target.value.trim()));
  }
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      if (input) input.value = '';
      persistCurrentTag('');
    });
  }
}

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

  // Attach tag handlers once — safe regardless of auth state
  attachTagHandlers();

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
        // Show capture UI immediately from cached auth state. Token validation
        // and current-tab checks run in the background and can revise the UI.
        initialSection.style.display = 'none';
        connectSection.style.display = 'none';
        captureSection.style.display = 'block';

        captureVisibleBtn.disabled = false;
        captureFullBtn.disabled = false;
        captureSelectionBtn.disabled = false;

        const existingWarning = document.getElementById('captureWarning');
        if (existingWarning) existingWarning.remove();

        applyCurrentTabCheck();
        validateTokenInBackground(authState);
        loadCurrentTag();
        refreshTagSuggestions(authState);
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

  async function applyCurrentTabCheck() {
    try {
      const tabCheck = await chrome.runtime.sendMessage({ action: 'checkCurrentTab' });

      // Bail if UI has moved off the capture section in the meantime
      if (captureSection.style.display === 'none') return;

      if (!tabCheck.canCapture) {
        captureVisibleBtn.disabled = true;
        captureFullBtn.disabled = true;
        captureSelectionBtn.disabled = true;

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
      }
    } catch (error) {
      console.warn('[Popup] Failed to check current tab:', error);
    }
  }

  async function validateTokenInBackground(authState) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000);

      const validateResponse = await fetch(`${authState.instanceUrl}/api/v1/addon/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_token: authState.accessToken }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      let invalid = false;
      if (validateResponse.ok) {
        const validationData = await validateResponse.json();
        if (!validationData.valid) invalid = true;
      } else if (validateResponse.status === 401) {
        invalid = true;
      }

      if (invalid) {
        console.log('[Popup] Token no longer valid, clearing auth state');
        await chrome.runtime.sendMessage({ action: 'logout' });
        initialSection.style.display = 'block';
        connectSection.style.display = 'none';
        captureSection.style.display = 'none';
      }
    } catch (error) {
      // Network errors or timeouts: keep the optimistic UI — the upload path
      // will surface any real auth failure via its own error handling.
      console.warn('[Popup] Background token validation failed:', error);
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
