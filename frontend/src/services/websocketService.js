/**
 * WebSocket Service
 * 
 * Manages WebSocket connection to backend for real-time communication and immediate offline detection.
 * Features:
 * - Automatic reconnection with exponential backoff (max 3 retries)
 * - Ping/pong heartbeat to detect connection issues
 * - Callbacks for connection state changes
 * - Shows offline modal after 3 failed reconnection attempts
 */

let ws = null;
let reconnectAttempts = 0;
let maxReconnectAttempts = 3;
let reconnectTimeout = null;
let isConnected = false;
let isIntentionallyClosed = false;
let onOfflineCallback = null;
let onOnlineCallback = null;
let onNewImageCallback = null;
let onPairingRevokedCallback = null;
let pingTimeout = null;
let currentSessionId = null;

/**
 * Get WebSocket URL based on current location
 */
function getWebSocketUrl(sessionId) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  
  // In development, Vite proxy doesn't support WebSocket upgrade
  // So we connect directly to the backend port
  if (import.meta.env.DEV) {
    // Extract port from VITE_API_URL if available, otherwise use default 8081
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8081';
    const url = new URL(apiUrl);
    const port = url.port || '8081';
    return `${protocol}//${window.location.hostname}:${port}/ws?session_id=${sessionId}`;
  }
  
  // In production, use same host as current page
  return `${protocol}//${window.location.host}/ws?session_id=${sessionId}`;
}

/**
 * Calculate reconnect delay with exponential backoff
 * Attempt 1: 1 second
 * Attempt 2: 2 seconds
 * Attempt 3: 4 seconds
 */
function getReconnectDelay() {
  return Math.min(1000 * Math.pow(2, reconnectAttempts), 4000);
}

/**
 * Reset ping timeout
 * If we don't receive a ping within 15 seconds, assume connection is dead
 */
function resetPingTimeout() {
  if (pingTimeout) {
    clearTimeout(pingTimeout);
  }
  
  pingTimeout = setTimeout(() => {
    console.warn('[WebSocket] No ping received in 15s, connection may be dead');
    if (ws) {
      ws.close();
    }
  }, 15000);
}

/**
 * Connect to WebSocket
 */
export function connectWebSocket(sessionId) {
  if (!sessionId) {
    console.warn('[WebSocket] Cannot connect without session ID');
    return;
  }
  
  currentSessionId = sessionId;
  
  if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) {
    console.log('[WebSocket] Already connected or connecting');
    return;
  }
  
  if (isIntentionallyClosed) {
    console.log('[WebSocket] Not reconnecting - intentionally closed');
    return;
  }
  
  // Check if we've exceeded max attempts BEFORE trying to connect
  if (reconnectAttempts >= maxReconnectAttempts) {
    console.error('[WebSocket] Max reconnection attempts reached, backend appears to be offline');
    if (onOfflineCallback) {
      onOfflineCallback();
    }
    return;
  }
  
  const url = getWebSocketUrl(sessionId);
  console.log(`[WebSocket] Connecting to ${url}... (attempt ${reconnectAttempts + 1}/${maxReconnectAttempts})`);
  
  try {
    ws = new WebSocket(url);
    
    ws.onopen = () => {
      console.log('[WebSocket] Connected successfully');
      isConnected = true;
      reconnectAttempts = 0; // Reset on successful connection
      
      // Start ping timeout
      resetPingTimeout();
      
      // Notify online
      if (onOnlineCallback) {
        onOnlineCallback();
      }
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'ping') {
          // Reset ping timeout on every ping received
          resetPingTimeout();
        } else if (data.type === 'new_image') {
          // Handle new image uploaded from mobile
          console.log('[WebSocket] New image uploaded:', data.image_id);
          if (onNewImageCallback) {
            onNewImageCallback(data);
          }
        } else if (data.type === 'pairing_revoked') {
          // Handle pairing revoked from Android device
          console.log('[WebSocket] Pairing revoked:', data.pairing_id);
          if (onPairingRevokedCallback) {
            onPairingRevokedCallback(data);
          }
        }
        
        // Handle other message types here in the future
        
      } catch (error) {
        console.error('[WebSocket] Failed to parse message:', error);
      }
    };
    
    ws.onerror = (error) => {
      console.error('[WebSocket] Connection error:', error);
    };
    
    ws.onclose = (event) => {
      console.log(`[WebSocket] Disconnected (code: ${event.code}, reason: ${event.reason || 'none'})`);
      isConnected = false;
      
      // Clear ping timeout
      if (pingTimeout) {
        clearTimeout(pingTimeout);
        pingTimeout = null;
      }
      
      // Don't reconnect if intentionally closed
      if (isIntentionallyClosed) {
        console.log('[WebSocket] Not reconnecting - intentionally closed');
        return;
      }
      
      // Increment attempt counter
      reconnectAttempts++;
      console.log(`[WebSocket] Reconnection attempt ${reconnectAttempts}/${maxReconnectAttempts} failed`);
      
      // Check if we've exceeded max attempts
      if (reconnectAttempts >= maxReconnectAttempts) {
        console.error('[WebSocket] Max reconnection attempts reached, triggering offline modal');
        if (onOfflineCallback) {
          onOfflineCallback();
        }
        return;
      }
      
      // Schedule reconnection with exponential backoff
      const delay = getReconnectDelay();
      console.log(`[WebSocket] Scheduling reconnection in ${delay}ms...`);
      
      reconnectTimeout = setTimeout(() => {
        connectWebSocket(currentSessionId);
      }, delay);
    };
    
  } catch (error) {
    console.error('[WebSocket] Failed to create WebSocket:', error);
    
    // Increment attempt counter
    reconnectAttempts++;
    
    // Check if we've exceeded max attempts
    if (reconnectAttempts >= maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnection attempts reached (creation error)');
      if (onOfflineCallback) {
        onOfflineCallback();
      }
      return;
    }
    
    // Schedule reconnection
    const delay = getReconnectDelay();
    reconnectTimeout = setTimeout(() => {
      connectWebSocket(currentSessionId);
    }, delay);
  }
}

/**
 * Disconnect WebSocket
 */
export function disconnectWebSocket() {
  isIntentionallyClosed = true;
  
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = null;
  }
  
  if (pingTimeout) {
    clearTimeout(pingTimeout);
    pingTimeout = null;
  }
  
  if (ws) {
    console.log('[WebSocket] Closing connection');
    ws.close();
    ws = null;
  }
  
  isConnected = false;
  reconnectAttempts = 0;
}

/**
 * Set callback for when backend goes offline (after 3 failed reconnects)
 */
export function setOfflineCallback(callback) {
  onOfflineCallback = callback;
}

/**
 * Set callback for when backend comes back online
 */
export function setOnlineCallback(callback) {
  onOnlineCallback = callback;
}

/**
 * Set callback for when a new image is uploaded
 */
export function setNewImageCallback(callback) {
  onNewImageCallback = callback;
}

/**
 * Set callback for when a pairing is revoked
 */
export function setPairingRevokedCallback(callback) {
  onPairingRevokedCallback = callback;
}

/**
 * Compatibility exports for old function names
 */
export const setWebSocketOfflineCallback = setOfflineCallback;
export const setWebSocketOnlineCallback = setOnlineCallback;

/**
 * Check if WebSocket is currently connected
 */
export function isWebSocketConnected() {
  return isConnected && ws && ws.readyState === WebSocket.OPEN;
}

/**
 * Reset reconnection attempts (call when manual retry succeeds)
 */
export function resetReconnectAttempts() {
  reconnectAttempts = 0;
  isIntentionallyClosed = false;
}

/**
 * Get current reconnection attempt count
 */
export function getReconnectAttempts() {
  return reconnectAttempts;
}
