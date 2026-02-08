/**
 * Service for mobile app pairing and QR code generation
 */
import { api } from './api';

const mobileService = {
  /**
   * Create a new mobile app pairing
   * @param {string} sessionId - Session ID to link the pairing to
   * @param {string} deviceName - Optional device name
   * @returns {Promise} Pairing data
   */
  async createPairing(sessionId, deviceName = null) {
    const response = await api.post('/mobile/pairings', {
      session_id: sessionId,
      device_name: deviceName
    });
    return response.data;
  },

  /**
   * Get QR code data for a pairing
   * @param {string} pairingId - Pairing ID
   * @returns {Promise} QR code data
   */
  async getQRCodeData(pairingId) {
    const response = await api.get(`/mobile/pairings/qr-data/${pairingId}`);
    return response.data;
  },

  /**
   * Get a specific pairing by ID
   * @param {string} pairingId - Pairing ID
   * @returns {Promise} Pairing data
   */
  async getPairing(pairingId) {
    const response = await api.get(`/mobile/pairings/${pairingId}`);
    return response.data;
  },

  /**
   * Get all pairings for a session
   * @param {string} sessionId - Session ID
   * @param {boolean} activeOnly - Only return active pairings
   * @returns {Promise} List of pairings
   */
  async getSessionPairings(sessionId, activeOnly = true) {
    const response = await api.get(`/mobile/pairings/session/${sessionId}`, {
      params: { active_only: activeOnly }
    });
    return response.data;
  },

  /**
   * List all paired devices for a session (with device metadata)
   * @param {string} sessionId - Session ID
   * @returns {Promise} List of paired devices with metadata
   */
  async listPairedDevices(sessionId) {
    const response = await api.get(`/mobile/pairings/session/${sessionId}/list`);
    return response.data;
  },

  /**
   * Delete/deactivate a pairing
   * @param {string} pairingId - Pairing ID
   * @returns {Promise}
   */
  async deletePairing(pairingId) {
    const response = await api.delete(`/mobile/pairings/${pairingId}`);
    return response.data;
  },

  /**
   * Revoke all pairings for a session
   * @param {string} sessionId - Session ID
   * @returns {Promise}
   */
  async revokeAllPairings(sessionId) {
    const response = await api.post(`/mobile/pairings/session/${sessionId}/revoke-all`);
    return response.data;
  }
};

export default mobileService;
