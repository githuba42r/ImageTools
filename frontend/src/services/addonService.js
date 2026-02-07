/**
 * Browser Addon Service
 * Handles authorization and registration for browser addons
 */

const API_BASE_URL = '/api/v1';

class AddonService {
  /**
   * Create a new addon authorization
   * @param {string} sessionId - Session ID to link the addon to
   * @param {string} browserName - Browser type (firefox or chrome)
   * @returns {Promise<Object>} Authorization response with registration URL
   */
  async createAuthorization(sessionId, browserName = null) {
    const response = await fetch(`${API_BASE_URL}/addon/authorize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        browser_name: browserName,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create authorization');
    }

    return response.json();
  }

  /**
   * Get list of connected addons for a session
   * @param {string} sessionId - Session ID
   * @returns {Promise<Array>} List of connected addons
   */
  async listConnectedAddons(sessionId) {
    const response = await fetch(`${API_BASE_URL}/addon/authorizations/session/${sessionId}/list`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch connected addons');
    }

    return response.json();
  }

  /**
   * Revoke an addon authorization
   * @param {string} authId - Authorization ID to revoke
   * @returns {Promise<Object>} Revocation confirmation
   */
  async revokeAuthorization(authId) {
    const response = await fetch(`${API_BASE_URL}/addon/authorizations/${authId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to revoke authorization');
    }

    return response.json();
  }

  /**
   * Revoke all addon authorizations for a session
   * @param {string} sessionId - Session ID
   * @returns {Promise<Object>} Revocation confirmation
   */
  async revokeAllAuthorizations(sessionId) {
    const response = await fetch(`${API_BASE_URL}/addon/authorizations/session/${sessionId}/revoke-all`, {
      method: 'POST',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to revoke authorizations');
    }

    return response.json();
  }
}

export default new AddonService();
