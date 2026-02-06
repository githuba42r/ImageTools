<template>
  <div class="upload-area" :class="{ 'compact': compact, 'inline': inline }">
    <div
      class="dropzone"
      :class="{ 'drag-over': isDragOver, 'uploading': isUploading, 'compact': compact, 'inline': inline }"
      @dragover.prevent="isDragOver = true"
      @dragleave.prevent="isDragOver = false"
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <input
        ref="fileInput"
        type="file"
        multiple
        accept="image/*"
        @change="handleFileSelect"
        style="display: none"
      />
      
      <div class="dropzone-content">
        <div v-if="!isUploading">
          <div class="upload-icon">{{ inline ? '➕' : '📁' }}</div>
          <p class="upload-text">{{ inline ? 'Add Images' : (compact ? 'Add more' : 'Drop images here or click to browse') }}</p>
          <p v-if="!compact && !inline" class="upload-hint">Supports: JPG, PNG, GIF, BMP, WEBP, TIFF</p>
          <p v-if="!compact && !inline" class="upload-limit">Max {{ maxImages }} images per session</p>
        </div>
        
        <div v-else class="uploading-state">
          <div class="spinner"></div>
          <p v-if="!compact && !inline">Uploading...</p>
        </div>
      </div>
    </div>

    <div v-if="error && !inline" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useImageStore } from '../stores/imageStore';
import { storeToRefs } from 'pinia';

const props = defineProps({
  compact: {
    type: Boolean,
    default: false
  },
  inline: {
    type: Boolean,
    default: false
  }
});

const imageStore = useImageStore();
const { isUploading } = storeToRefs(imageStore);

const fileInput = ref(null);
const isDragOver = ref(false);
const error = ref(null);
const maxImages = 5;

const emit = defineEmits(['upload-complete']);

const triggerFileInput = () => {
  fileInput.value?.click();
};

const handleFileSelect = async (event) => {
  const files = Array.from(event.target.files);
  await uploadFiles(files);
  event.target.value = '';
};

const handleDrop = async (event) => {
  isDragOver.value = false;
  const files = Array.from(event.dataTransfer.files).filter(
    file => file.type.startsWith('image/')
  );
  await uploadFiles(files);
};

const uploadFiles = async (files) => {
  if (files.length === 0) {
    error.value = 'No valid image files selected';
    return;
  }

  error.value = null;

  try {
    const results = await imageStore.uploadMultipleImages(files);
    
    const successCount = results.filter(r => r.success).length;
    const failCount = results.filter(r => !r.success).length;

    if (failCount > 0) {
      error.value = `${successCount} uploaded, ${failCount} failed`;
    }

    emit('upload-complete', { successCount, failCount });
  } catch (err) {
    error.value = err.message;
  }
};
</script>

<style scoped>
.upload-area {
  margin-bottom: 2rem;
}

.upload-area.compact {
  margin-bottom: 0;
  width: 200px;
  flex-shrink: 0;
}

.upload-area.inline {
  margin-bottom: 0;
  width: auto;
}

.dropzone {
  border: 2px dashed #ccc;
  border-radius: 8px;
  padding: 3rem 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background-color: #fafafa;
  min-height: 75vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dropzone.compact {
  padding: 1.5rem 1rem;
  min-height: 300px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.dropzone.inline {
  padding: 0.75rem 1.5rem;
  min-height: auto;
  border-color: rgba(255, 255, 255, 0.4);
  background-color: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
}

.dropzone:hover {
  border-color: #4CAF50;
  background-color: #f0f8f0;
}

.dropzone.inline:hover {
  border-color: rgba(255, 255, 255, 0.7);
  background-color: rgba(255, 255, 255, 0.2);
}

.dropzone.drag-over {
  border-color: #4CAF50;
  background-color: #e8f5e9;
  transform: scale(1.02);
}

.dropzone.inline.drag-over {
  border-color: rgba(255, 255, 255, 0.9);
  background-color: rgba(255, 255, 255, 0.25);
  transform: scale(1.05);
}

.dropzone.compact.drag-over {
  transform: scale(1.05);
}

.dropzone.uploading {
  pointer-events: none;
  opacity: 0.7;
}

.dropzone-content {
  pointer-events: none;
}

.inline .dropzone-content {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.upload-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.compact .upload-icon {
  font-size: 2rem;
  margin-bottom: 0.75rem;
}

.inline .upload-icon {
  font-size: 1.25rem;
  margin-bottom: 0;
}

.upload-text {
  font-size: 1.2rem;
  font-weight: 500;
  margin-bottom: 0.5rem;
  color: #333;
}

.compact .upload-text {
  font-size: 0.95rem;
  margin-bottom: 0.25rem;
}

.inline .upload-text {
  font-size: 0.9rem;
  margin-bottom: 0;
  color: white;
  font-weight: 600;
}

.upload-hint {
  font-size: 0.9rem;
  color: #666;
  margin-bottom: 0.25rem;
}

.upload-limit {
  font-size: 0.85rem;
  color: #999;
}

.uploading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.compact .uploading-state {
  gap: 0.5rem;
}

.inline .uploading-state {
  flex-direction: row;
  gap: 0.5rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #4CAF50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.compact .spinner {
  width: 30px;
  height: 30px;
  border-width: 3px;
}

.inline .spinner {
  width: 20px;
  height: 20px;
  border-width: 2px;
  border-color: rgba(255, 255, 255, 0.3);
  border-top-color: white;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  margin-top: 1rem;
  padding: 0.75rem;
  background-color: #ffebee;
  border: 1px solid #ef5350;
  border-radius: 4px;
  color: #c62828;
  font-size: 0.9rem;
}

.compact .error-message {
  font-size: 0.8rem;
  padding: 0.5rem;
}
</style>
