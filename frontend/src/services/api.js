import axios from 'axios';

const API_BASE_URL = '/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // 10 second timeout
});

// Track if we're currently showing offline modal
let isOffline = false;
let offlineCallback = null;

// Set callback for offline detection
export const setOfflineCallback = (callback) => {
  offlineCallback = callback;
};

// Request interceptor to add session ID header
api.interceptors.request.use(
  config => {
    // Get session ID from localStorage
    const sessionId = localStorage.getItem('imagetools_session_id');
    
    // Check if using session override from environment
    const sessionOverride = import.meta?.env?.VITE_SESSION_OVERRIDE;
    const activeSessionId = (sessionOverride && sessionOverride.trim() !== '') ? sessionOverride : sessionId;
    
    // Add X-Session-ID header if session exists
    if (activeSessionId) {
      config.headers['X-Session-ID'] = activeSessionId;
    }
    
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// Response interceptor to detect offline
api.interceptors.response.use(
  response => response,
  error => {
    // Check if error is network error (backend offline)
    if (!error.response && (error.code === 'ERR_NETWORK' || error.code === 'ECONNABORTED')) {
      if (!isOffline && offlineCallback) {
        isOffline = true;
        offlineCallback();
      }
    }
    return Promise.reject(error);
  }
);

// Call this when connection is restored
export const markOnline = () => {
  isOffline = false;
};

// Session API
export const sessionService = {
  async createSession(userId = null, customSessionId = null) {
    const payload = { user_id: userId };
    if (customSessionId) {
      payload.custom_session_id = customSessionId;
    }
    const response = await api.post('/sessions', payload);
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

  async resizeImage(imageId, width, height) {
    const response = await api.post(`/images/${imageId}/resize`, { width, height });
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

  async saveEditedImage(imageId, formData) {
    const response = await api.post(`/images/${imageId}/edit`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
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

// Profile API
export const profileService = {
  async createProfile(profileData) {
    const response = await api.post('/profiles', profileData);
    return response.data;
  },

  async getProfiles() {
    const response = await api.get('/profiles');
    return response.data;
  },

  async getProfile(profileId) {
    const response = await api.get(`/profiles/${profileId}`);
    return response.data;
  },

  async updateProfile(profileId, profileData) {
    const response = await api.put(`/profiles/${profileId}`, profileData);
    return response.data;
  },

  async deleteProfile(profileId) {
    await api.delete(`/profiles/${profileId}`);
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
