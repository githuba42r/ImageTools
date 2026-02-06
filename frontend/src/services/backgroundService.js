import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8081/api/v1';

/**
 * Background removal service
 * Uses rembg for FREE local background removal (no API costs)
 */
export const backgroundService = {
  /**
   * Remove background from an image
   * @param {string} imageId - Image ID
   * @param {Object} options - Background removal options
   * @param {boolean} options.alphaMatting - Use alpha matting for better edges (slower)
   * @param {number} options.alphaMattingForegroundThreshold - Foreground threshold (0-255)
   * @param {number} options.alphaMattingBackgroundThreshold - Background threshold (0-255)
   * @param {string} options.model - rembg model (u2net, u2net_human_seg, isnet-general-use, isnet-anime)
   * @returns {Promise<Object>} Background removal result
   */
  async removeBackground(imageId, options = {}) {
    const {
      alphaMatting = false,
      alphaMattingForegroundThreshold = 240,
      alphaMattingBackgroundThreshold = 10,
      model = 'u2net'
    } = options;

    try {
      const response = await axios.post(
        `${API_URL}/background/${imageId}/remove-background`,
        {
          alpha_matting: alphaMatting,
          alpha_matting_foreground_threshold: alphaMattingForegroundThreshold,
          alpha_matting_background_threshold: alphaMattingBackgroundThreshold,
          model
        }
      );

      return response.data;
    } catch (error) {
      console.error('Background removal failed:', error);
      throw error;
    }
  },

  /**
   * Get available rembg models
   * @returns {Promise<Object>} Map of model names to descriptions
   */
  async getAvailableModels() {
    try {
      const response = await axios.get(`${API_URL}/background/models`);
      return response.data;
    } catch (error) {
      console.error('Failed to get available models:', error);
      throw error;
    }
  }
};
