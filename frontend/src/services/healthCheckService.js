/**
 * Health Check Service
 * 
 * Periodically polls the backend /health endpoint to detect when the backend goes offline.
 * Uses exponential backoff when offline to avoid overwhelming the server during recovery.
 * 
 * Features:
 * - Automatic health check polling every 30 seconds
 * - Exponential backoff when offline (30s, 60s, 120s, max 300s)
 * - Callbacks for online/offline state changes
 * - Manual start/stop control
 */

let healthCheckInterval = null;
let isCurrentlyOffline = false;
let offlineCallback = null;
let onlineCallback = null;
let pollInterval = 30000; // Default: 30 seconds
let consecutiveFailures = 0;
let isPolling = false;

/**
 * Calculate backoff interval based on consecutive failures
 * Exponential backoff: 30s, 60s, 120s, 240s, 300s (max 5 min)
 */
function getBackoffInterval() {
  if (consecutiveFailures === 0) return 30000; // 30s
  if (consecutiveFailures === 1) return 60000; // 1 min
  if (consecutiveFailures === 2) return 120000; // 2 min
  if (consecutiveFailures === 3) return 240000; // 4 min
  return 300000; // 5 min max
}

/**
 * Perform a health check by pinging the /health endpoint
 */
async function performHealthCheck() {
  try {
    const response = await fetch('/health', {
      method: 'GET',
      cache: 'no-cache',
      signal: AbortSignal.timeout(5000), // 5 second timeout
    });

    if (response.ok) {
      // Backend is healthy
      if (isCurrentlyOffline) {
        // Was offline, now back online
        console.log('[HealthCheck] Backend is back online');
        isCurrentlyOffline = false;
        consecutiveFailures = 0;
        pollInterval = 30000; // Reset to normal interval
        
        if (onlineCallback) {
          onlineCallback();
        }
      }
      
      // Reset polling interval if we're in backoff mode
      if (pollInterval > 30000) {
        console.log('[HealthCheck] Resetting poll interval to 30s');
        pollInterval = 30000;
        restartPolling();
      }
    } else {
      handleOffline();
    }
  } catch (error) {
    // Network error, timeout, or other fetch failure
    console.warn('[HealthCheck] Health check failed:', error.message);
    handleOffline();
  }
}

/**
 * Handle offline state
 */
function handleOffline() {
  consecutiveFailures++;
  
  if (!isCurrentlyOffline) {
    // Just went offline
    console.log('[HealthCheck] Backend is offline');
    isCurrentlyOffline = true;
    
    if (offlineCallback) {
      offlineCallback();
    }
  }
  
  // Apply exponential backoff
  const newInterval = getBackoffInterval();
  if (newInterval !== pollInterval) {
    console.log(`[HealthCheck] Increasing poll interval to ${newInterval / 1000}s (failure #${consecutiveFailures})`);
    pollInterval = newInterval;
    restartPolling();
  }
}

/**
 * Restart polling with new interval
 */
function restartPolling() {
  if (!isPolling) return;
  
  stopHealthCheck();
  startHealthCheck();
}

/**
 * Start periodic health checks
 */
export function startHealthCheck() {
  if (healthCheckInterval) {
    console.warn('[HealthCheck] Already running');
    return;
  }
  
  console.log('[HealthCheck] Starting health check polling (every 30s)');
  isPolling = true;
  
  // Perform initial check immediately
  performHealthCheck();
  
  // Then poll at regular intervals
  healthCheckInterval = setInterval(() => {
    performHealthCheck();
  }, pollInterval);
}

/**
 * Stop periodic health checks
 */
export function stopHealthCheck() {
  if (healthCheckInterval) {
    console.log('[HealthCheck] Stopping health check polling');
    clearInterval(healthCheckInterval);
    healthCheckInterval = null;
    isPolling = false;
  }
}

/**
 * Set callback for when backend goes offline
 */
export function setOfflineCallback(callback) {
  offlineCallback = callback;
}

/**
 * Set callback for when backend comes back online
 */
export function setOnlineCallback(callback) {
  onlineCallback = callback;
}

/**
 * Manually trigger a health check (useful for retry button)
 */
export function checkHealthNow() {
  console.log('[HealthCheck] Manual health check triggered');
  return performHealthCheck();
}

/**
 * Get current offline state
 */
export function isOffline() {
  return isCurrentlyOffline;
}

/**
 * Reset state (useful for testing)
 */
export function resetHealthCheck() {
  stopHealthCheck();
  isCurrentlyOffline = false;
  consecutiveFailures = 0;
  pollInterval = 30000;
  offlineCallback = null;
  onlineCallback = null;
}
