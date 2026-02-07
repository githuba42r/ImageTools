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
let pingTimeout = null;

/**
 * Get WebSocket URL based on current location
 */
function getWebSocketUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  
  // In development, Vite proxy doesn't support WebSocket upgrade
  // So we connect directly to the backend port
  if (import.meta.env.DEV) {
    return `${protocol}//${window.location.hostname}:8000/ws`;
  }
  
  // In production, use same host as current page
  return `${protocol}//${window.location.host}/ws`;
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
export function connectWebSocket() {
  if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) {
    console.log('[WebSocket] Already connected or connecting');
    return;
  }
  
  if (isIntentionallyClosed) {
    console.log('[WebSocket] Not reconnecting - intentionally closed');
    return;
  }
  
  const url = getWebSocketUrl();
  console.log(`[WebSocket] Connecting to ${url}... (attempt ${reconnectAttempts + 1}/${maxReconnectAttempts})`);
  
  try {
    ws = new WebSocket(url);
    
    ws.onopen = () => {
      console.log('[WebSocket] Connected');
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
        }
        
        // Handle other message types here in the future
        
      } catch (error) {
        console.error('[WebSocket] Failed to parse message:', error);
      }
    };
    
    ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error);
    };
    
    ws.onclose = (event) => {
      console.log('[WebSocket] Disconnected', event.code, event.reason);
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
      
      // Attempt to reconnect
      if (reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        const delay = getReconnectDelay();
        console.log(`[WebSocket] Reconnecting in ${delay}ms... (attempt ${reconnectAttempts}/${maxReconnectAttempts})`);
        
        reconnectTimeout = setTimeout(() => {
          connectWebSocket();
        }, delay);
      } else {
        // Max reconnect attempts reached - trigger offline modal
        console.error('[WebSocket] Max reconnection attempts reached, backend appears to be offline');
        
        if (onOfflineCallback) {
          onOfflineCallback();
        }
      }
    };
    
  } catch (error) {
    console.error('[WebSocket] Failed to create WebSocket:', error);
    
    // Retry if under max attempts
    if (reconnectAttempts < maxReconnectAttempts) {
      reconnectAttempts++;
      const delay = getReconnectDelay();
      reconnectTimeout = setTimeout(() => {
        connectWebSocket();
      }, delay);
    } else {
      if (onOfflineCallback) {
        onOfflineCallback();
      }
    }
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
