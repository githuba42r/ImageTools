/**
 * Service for mobile app pairing and QR code generation
 */
import { api } from './api';

const mobileService = {
  /**
   * Create a new mobile app pairing
   * @param {string} userId - User ID to link the pairing to
   * @param {string} deviceName - Optional device name
   * @returns {Promise} Pairing data
   */
  async createPairing(userId, deviceName = null) {
    const response = await api.post('/mobile/pairings', {
      user_id: userId,
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
   * Get all pairings for a user
   * @param {string} userId - User ID
   * @param {boolean} activeOnly - Only return active pairings
   * @returns {Promise} List of pairings
   */
  async getUserPairings(userId, activeOnly = true) {
    const response = await api.get(`/mobile/pairings/user/${userId}`, {
      params: { active_only: activeOnly }
    });
    return response.data;
  },

  /**
   * List all paired devices for a user (with device metadata)
   * @param {string} userId - User ID
   * @returns {Promise} List of paired devices with metadata
   */
  async listPairedDevices(userId) {
    const response = await api.get(`/mobile/pairings/user/${userId}/list`);
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
   * Revoke all pairings for a user
   * @param {string} userId - User ID
   * @returns {Promise}
   */
  async revokeAllPairings(userId) {
    const response = await api.post(`/mobile/pairings/user/${userId}/revoke-all`);
    return response.data;
  }
};

export default mobileService;
