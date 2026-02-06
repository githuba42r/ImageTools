import { defineStore } from 'pinia';
import { imageService, compressionService, historyService } from '../services/api';
import { useSessionStore } from './sessionStore';

export const useImageStore = defineStore('image', {
  state: () => ({
    images: [],
    selectedImages: [],
    isUploading: false,
    uploadProgress: {},
    presets: [],
    error: null,
  }),

  getters: {
    imageCount: (state) => state.images.length,
    selectedCount: (state) => state.selectedImages.length,
    hasSelectedImages: (state) => state.selectedImages.length > 0,
  },

  actions: {
    async loadSessionImages() {
      const sessionStore = useSessionStore();
      if (!sessionStore.sessionId) return;

      try {
        this.images = await imageService.getSessionImages(sessionStore.sessionId);
        console.log(`Loaded ${this.images.length} images`);
      } catch (error) {
        this.error = error.message;
        console.error('Failed to load images:', error);
      }
    },

    async uploadImage(file) {
      const sessionStore = useSessionStore();
      if (!sessionStore.sessionId) {
        throw new Error('No active session');
      }

      this.isUploading = true;
      this.error = null;

      try {
        const image = await imageService.uploadImage(sessionStore.sessionId, file);
        this.images.unshift(image);
        console.log('Image uploaded:', image.id);
        return image;
      } catch (error) {
        this.error = error.response?.data?.detail || error.message;
        console.error('Failed to upload image:', error);
        throw error;
      } finally {
        this.isUploading = false;
      }
    },

    async uploadMultipleImages(files) {
      const results = [];
      for (const file of files) {
        try {
          const image = await this.uploadImage(file);
          results.push({ success: true, image });
        } catch (error) {
          results.push({ success: false, error: error.message });
        }
      }
      return results;
    },

    async compressImage(imageId, preset, customParams = null) {
      try {
        const result = await compressionService.compressImage(imageId, preset, customParams);
        
        // Refresh image data
        const updatedImage = await imageService.getImage(imageId);
        const index = this.images.findIndex(img => img.id === imageId);
        if (index !== -1) {
          this.images[index] = updatedImage;
        }

        console.log(`Image compressed: ${result.compression_ratio}% reduction`);
        return result;
      } catch (error) {
        this.error = error.response?.data?.detail || error.message;
        console.error('Failed to compress image:', error);
        throw error;
      }
    },

    async compressSelected(preset) {
      const results = [];
      for (const imageId of this.selectedImages) {
        try {
          const result = await this.compressImage(imageId, preset);
          results.push({ success: true, imageId, result });
        } catch (error) {
          results.push({ success: false, imageId, error: error.message });
        }
      }
      return results;
    },

    async deleteImage(imageId) {
      try {
        await imageService.deleteImage(imageId);
        this.images = this.images.filter(img => img.id !== imageId);
        this.selectedImages = this.selectedImages.filter(id => id !== imageId);
        console.log('Image deleted:', imageId);
      } catch (error) {
        this.error = error.message;
        console.error('Failed to delete image:', error);
        throw error;
      }
    },

    async undoOperation(imageId) {
      try {
        const result = await historyService.undoOperation(imageId);
        
        // Refresh image data
        const updatedImage = await imageService.getImage(imageId);
        const index = this.images.findIndex(img => img.id === imageId);
        if (index !== -1) {
          this.images[index] = updatedImage;
        }

        console.log('Operation undone:', imageId);
        return result;
      } catch (error) {
        this.error = error.response?.data?.detail || error.message;
        console.error('Failed to undo:', error);
        throw error;
      }
    },

    async rotateImage(imageId, degrees) {
      try {
        const result = await imageService.rotateImage(imageId, degrees);
        
        // Refresh image data
        const updatedImage = await imageService.getImage(imageId);
        const index = this.images.findIndex(img => img.id === imageId);
        if (index !== -1) {
          this.images[index] = updatedImage;
        }

        console.log(`Image rotated: ${degrees}°`);
        return result;
      } catch (error) {
        this.error = error.response?.data?.detail || error.message;
        console.error('Failed to rotate:', error);
        throw error;
      }
    },

    async loadPresets() {
      try {
        const data = await compressionService.getPresets();
        this.presets = data.presets;
      } catch (error) {
        console.error('Failed to load presets:', error);
      }
    },

    toggleSelection(imageId) {
      const index = this.selectedImages.indexOf(imageId);
      if (index === -1) {
        this.selectedImages.push(imageId);
      } else {
        this.selectedImages.splice(index, 1);
      }
    },

    selectAll() {
      this.selectedImages = this.images.map(img => img.id);
    },

    clearSelection() {
      this.selectedImages = [];
    },

    isSelected(imageId) {
      return this.selectedImages.includes(imageId);
    },
  },
});
