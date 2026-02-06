<template>
  <div class="gallery-toolbar">
    <div class="toolbar-left">
      <span class="image-count">{{ imageCount }} image{{ imageCount !== 1 ? 's' : '' }}</span>
      <span v-if="selectedCount > 0" class="selected-count">
        ({{ selectedCount }} selected)
      </span>
    </div>

    <div class="toolbar-actions">
      <button 
        @click="selectAll" 
        class="btn-icon btn-sm"
        :disabled="imageCount === 0"
        title="Select all images"
      >
        <span class="icon">☑</span>
        <span class="tooltip">Select All</span>
      </button>

      <button 
        @click="clearSelection" 
        class="btn-icon btn-sm"
        :disabled="selectedCount === 0"
        title="Clear selection"
      >
        <span class="icon">☐</span>
        <span class="tooltip">Clear Selection</span>
      </button>

      <div class="bulk-compress-group">
        <select 
          v-model="bulkPreset" 
          class="preset-select"
          :disabled="selectedCount === 0"
        >
          <option value="">Bulk compress...</option>
          <option v-for="preset in presets" :key="preset.name" :value="preset.name">
            {{ preset.label }}
          </option>
        </select>

        <button 
          @click="handleBulkCompress" 
          class="btn-icon btn-compress"
          :disabled="selectedCount === 0 || !bulkPreset || isProcessing"
          title="Compress selected images"
        >
          <span class="icon">{{ isProcessing ? '⏳' : '⚡' }}</span>
          <span class="tooltip">{{ isProcessing ? 'Processing...' : 'Compress Selected' }}</span>
        </button>
      </div>

      <button 
        @click="handleDownloadSelected" 
        class="btn-icon btn-sm"
        :disabled="selectedCount === 0"
        title="Download selected images"
      >
        <span class="icon">⬇</span>
        <span class="tooltip">Download Selected</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useImageStore } from '../stores/imageStore';
import { storeToRefs } from 'pinia';

const props = defineProps({
  presets: {
    type: Array,
    default: () => []
  }
});

const imageStore = useImageStore();
const { imageCount, selectedCount } = storeToRefs(imageStore);

const bulkPreset = ref('');
const isProcessing = ref(false);

const selectAll = () => {
  imageStore.selectAll();
};

const clearSelection = () => {
  imageStore.clearSelection();
};

const handleBulkCompress = async () => {
  if (!bulkPreset.value || selectedCount.value === 0) return;

  isProcessing.value = true;
  try {
    const results = await imageStore.compressSelected(bulkPreset.value);
    const successCount = results.filter(r => r.success).length;
    console.log(`Compressed ${successCount}/${results.length} images`);
  } catch (error) {
    console.error('Bulk compression failed:', error);
  } finally {
    isProcessing.value = false;
  }
};

const handleDownloadSelected = () => {
  imageStore.selectedImages.forEach(imageId => {
    const image = imageStore.images.find(img => img.id === imageId);
    if (image) {
      window.open(image.image_url, '_blank');
    }
  });
};
</script>

<style scoped>
.gallery-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background-color: #f5f5f5;
  border-radius: 8px;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.image-count {
  font-weight: 600;
  color: #333;
}

.selected-count {
  color: #4CAF50;
  font-weight: 500;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.bulk-compress-group {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.btn-icon {
  position: relative;
  padding: 0.5rem 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: white;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
}

.btn-icon:hover:not(:disabled) {
  background-color: #f5f5f5;
  border-color: #4CAF50;
  transform: translateY(-2px);
}

.btn-icon:active:not(:disabled) {
  transform: translateY(0);
}

.btn-icon:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-icon .icon {
  font-size: 1.1rem;
  display: block;
}

.btn-sm {
  padding: 0.4rem 0.6rem;
}

.btn-sm .icon {
  font-size: 1rem;
}

.btn-compress {
  background-color: #4CAF50;
  color: white;
  border-color: #4CAF50;
}

.btn-compress:hover:not(:disabled) {
  background-color: #45a049;
  border-color: #45a049;
}

.btn-compress:disabled {
  background-color: #ccc;
  border-color: #ccc;
}

.preset-select {
  padding: 0.5rem 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.85rem;
  background-color: white;
  cursor: pointer;
}

.preset-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.preset-select:focus {
  outline: none;
  border-color: #4CAF50;
}

.tooltip {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%) translateY(-8px);
  background-color: #333;
  color: white;
  padding: 0.4rem 0.6rem;
  border-radius: 4px;
  font-size: 0.75rem;
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.2s ease, transform 0.2s ease;
  z-index: 10;
}

.tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 4px solid transparent;
  border-top-color: #333;
}

.btn-icon:hover:not(:disabled) .tooltip {
  opacity: 1;
  transform: translateX(-50%) translateY(-4px);
}
</style>
