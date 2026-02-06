import axios from 'axios';

const API_BASE_URL = '/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Session API
export const sessionService = {
  async createSession(userId = null) {
    const response = await api.post('/sessions', { user_id: userId });
    return response.data;
  },

  async getSession(sessionId) {
    const response = await api.get(`/sessions/${sessionId}`);
    return response.data;
  },

  async validateSession(sessionId) {
    const response = await api.get(`/sessions/${sessionId}/validate`);
    return response.data;
  },
};

// Image API
export const imageService = {
  async uploadImage(sessionId, file) {
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('file', file);

    const response = await api.post('/images', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async getSessionImages(sessionId) {
    const response = await api.get(`/images/session/${sessionId}`);
    return response.data;
  },

  async getImage(imageId) {
    const response = await api.get(`/images/${imageId}`);
    return response.data;
  },

  async deleteImage(imageId) {
    const response = await api.delete(`/images/${imageId}`);
    return response.data;
  },

  getImageUrl(imageId) {
    return `${API_BASE_URL}/images/${imageId}/current`;
  },

  getThumbnailUrl(imageId) {
    return `${API_BASE_URL}/images/${imageId}/thumbnail`;
  },

  async rotateImage(imageId, degrees) {
    const response = await api.post(`/images/${imageId}/rotate`, { degrees });
    return response.data;
  },

  async flipImage(imageId, direction) {
    const response = await api.post(`/images/${imageId}/flip`, { direction });
    return response.data;
  },

  async getExifData(imageId) {
    const response = await api.get(`/images/${imageId}/exif`);
    return response.data;
  },

  async downloadImagesAsZip(imageIds) {
    const response = await api.post('/images/download-zip', 
      { image_ids: imageIds },
      { responseType: 'blob' }
    );
    return response.data;
  },
};

// Compression API
export const compressionService = {
  async compressImage(imageId, preset, customParams = null) {
    const requestData = {
      preset,
      ...customParams,
    };

    const response = await api.post(`/compression/${imageId}`, requestData);
    return response.data;
  },

  async getPresets() {
    const response = await api.get('/compression/presets');
    return response.data;
  },
};

// History API
export const historyService = {
  async getHistory(imageId) {
    const response = await api.get(`/history/${imageId}`);
    return response.data;
  },

  async undoOperation(imageId) {
    const response = await api.post(`/history/${imageId}/undo`);
    return response.data;
  },

  async canUndo(imageId) {
    const response = await api.get(`/history/${imageId}/can-undo`);
    return response.data;
  },
};
