/**
 * OpenRouter OAuth2 PKCE Service
 * 
 * Handles OAuth2 PKCE flow for OpenRouter API key enrollment.
 * All API keys are stored encrypted on the backend - they never reach the frontend.
 */

// ============================================================================
// PKCE Helper Functions
// ============================================================================

/**
 * Generate a random code_verifier for PKCE flow
 * @returns {string} Base64URL-encoded random string (43-128 characters)
 */
export function generateCodeVerifier() {
  const array = new Uint8Array(32); // 32 bytes = 43 chars when base64url encoded
  crypto.getRandomValues(array);
  return base64URLEncode(array);
}

/**
 * Generate SHA-256 code_challenge from code_verifier
 * @param {string} verifier - The code verifier
 * @returns {Promise<string>} Base64URL-encoded SHA-256 hash
 */
export async function generateCodeChallenge(verifier) {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return base64URLEncode(new Uint8Array(hash));
}

/**
 * Encode buffer to Base64URL format (RFC 4648)
 * @param {Uint8Array} buffer - Buffer to encode
 * @returns {string} Base64URL-encoded string
 */
function base64URLEncode(buffer) {
  return btoa(String.fromCharCode(...buffer))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
}

// ============================================================================
// OpenRouter API Service Class
// ============================================================================

class OpenRouterService {
  constructor() {
    // Dynamically determine API URL based on environment
    // In production (Docker), frontend and backend are served from same origin
    // In development, backend runs on port 8081
    const isDevelopment = window.location.hostname === 'localhost' && window.location.port === '5173';
    const apiBase = isDevelopment 
      ? 'http://localhost:8081'
      : window.location.origin;
    
    this.baseURL = `${apiBase}/api/v1/openrouter`;
    this.sessionId = null;
  }

  /**
   * Set the session ID for API requests
   * @param {string} sessionId - Current session ID
   */
  setSessionId(sessionId) {
    this.sessionId = sessionId;
  }

  /**
   * Get headers with session ID
   * @returns {Object} Headers object
   */
  _getHeaders() {
    const headers = {
      'Content-Type': 'application/json',
    };
    
    if (this.sessionId) {
      headers['X-Session-ID'] = this.sessionId;
    }
    
    return headers;
  }

  /**
   * Get OAuth authorization URL from backend
   * @param {string} codeChallenge - PKCE code challenge (S256)
   * @returns {Promise<Object>} { auth_url: string }
   */
  async getAuthorizationUrl(codeChallenge) {
    const response = await fetch(`${this.baseURL}/oauth/authorize-url`, {
      method: 'POST',
      headers: this._getHeaders(),
      body: JSON.stringify({
        code_challenge: codeChallenge,
        code_challenge_method: 'S256'
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get authorization URL');
    }

    return response.json();
  }

  /**
   * Exchange authorization code for API key (proxied through backend)
   * Note: The API key stays on the backend and is never sent to the frontend
   * @param {string} code - Authorization code from OAuth callback
   * @param {string} codeVerifier - PKCE code verifier
   * @returns {Promise<Object>} { success: bool, key_label: string, has_key: bool, credits_remaining: float, credits_total: float }
   */
  async exchangeCode(code, codeVerifier) {
    const response = await fetch(`${this.baseURL}/oauth/exchange`, {
      method: 'POST',
      headers: this._getHeaders(),
      body: JSON.stringify({
        code,
        code_verifier: codeVerifier,
        code_challenge_method: 'S256'
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to exchange authorization code');
    }

    return response.json();
  }

  /**
   * Get OpenRouter connection status
   * @returns {Promise<Object>} { has_key: bool, connected: bool, key_label: string, credits_remaining: float, credits_total: float, created_at: string, last_used_at: string }
   */
  async getStatus() {
    const response = await fetch(`${this.baseURL}/oauth/status`, {
      method: 'GET',
      headers: this._getHeaders()
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get status');
    }

    return response.json();
  }

  /**
   * Revoke/disconnect OpenRouter API key
   * @returns {Promise<Object>} { success: bool, message: string }
   */
  async revoke() {
    const response = await fetch(`${this.baseURL}/oauth/revoke`, {
      method: 'POST',
      headers: this._getHeaders()
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to revoke key');
    }

    return response.json();
  }

  /**
   * Get all available models from OpenRouter
   * @returns {Promise<Array>} Array of model objects with id, name, pricing, context_length, etc.
   */
  async getModels() {
    const response = await fetch('https://openrouter.ai/api/v1/models', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error('Failed to fetch models from OpenRouter');
    }

    const result = await response.json();
    return result.data || [];
  }

  /**
   * Get user settings (selected model, etc.)
   * @returns {Promise<Object>} { selected_model_id: string|null }
   */
  async getSettings() {
    const apiBase = this._getApiBase();
    const response = await fetch(`${apiBase}/api/v1/settings`, {
      method: 'GET',
      headers: this._getHeaders()
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get settings');
    }

    return response.json();
  }

  /**
   * Update selected AI model
   * @param {string} modelId - OpenRouter model ID (e.g., "google/gemini-2.0-flash-exp:free")
   * @returns {Promise<Object>} { selected_model_id: string }
   */
  async updateModel(modelId) {
    const apiBase = this._getApiBase();
    const response = await fetch(`${apiBase}/api/v1/settings/model`, {
      method: 'PUT',
      headers: this._getHeaders(),
      body: JSON.stringify({ model_id: modelId })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update model');
    }

    return response.json();
  }

  /**
   * Get base API URL based on environment
   * @returns {string} Base API URL
   * @private
   */
  _getApiBase() {
    const isDevelopment = window.location.hostname === 'localhost' && window.location.port === '5173';
    return isDevelopment ? 'http://localhost:8081' : window.location.origin;
  }
}

// ============================================================================
// Export singleton instance
// ============================================================================

export const openRouterService = new OpenRouterService();
