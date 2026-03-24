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

// Request interceptor to add user ID header
api.interceptors.request.use(
  config => {
    // Get user ID from localStorage
    const userId = localStorage.getItem('imagetools_user_id');
    
    // Check if using user override from environment
    const userOverride = import.meta?.env?.VITE_USER_OVERRIDE;
    const activeUserId = (userOverride && userOverride.trim() !== '') ? userOverride : userId;
    
    // Add X-User-ID header if user exists
    if (activeUserId) {
      config.headers['X-User-ID'] = activeUserId;
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

// User API
export const userService = {
  async getOrCreateUser(hintId = null) {
    const payload = {};
    if (hintId) {
      payload.hint_id = hintId;
    }
    const response = await api.post('/users', payload);
    return response.data;
  },

  async getUser(userId) {
    const response = await api.get(`/users/${userId}`);
    return response.data;
  },

  async validateUser(userId) {
    const response = await api.get(`/users/${userId}/validate`);
    return response.data;
  },
};

// Image API
export const imageService = {
  async uploadImage(userId, file) {
    const formData = new FormData();
    formData.append('user_id', userId);
    formData.append('file', file);

    const response = await api.post('/images', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async getUserImages(userId) {
    const response = await api.get(`/images/user/${userId}`);
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

// Share Link API
export const shareService = {
  async createShareLink(imageId) {
    const response = await api.post(`/images/${imageId}/share`);
    return response.data;
  },
};
