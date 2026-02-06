<template>
  <div 
    class="image-card" 
    :class="{ 'selected': isSelected }"
    @click="handleCardClick"
  >
    <div class="image-preview" @click.stop="handleImageClick">
      <img :src="thumbnailUrl" :alt="image.original_filename" :title="image.original_filename" />
    </div>

    <div class="image-info">
      <div class="info-row">
        <span class="label">Size:</span>
        <span class="value">{{ formatSize(image.current_size) }}</span>
      </div>
      <div class="info-row">
        <span class="label">Original:</span>
        <span class="value">{{ formatSize(image.original_size) }}</span>
      </div>
      <div class="info-row">
        <span class="label">Dimensions:</span>
        <span class="value">{{ image.width }} × {{ image.height }}</span>
      </div>
      <div v-if="compressionRatio" class="info-row compression-ratio">
        <span class="label">Saved:</span>
        <span class="value">{{ compressionRatio }}%</span>
      </div>
    </div>

    <div class="card-actions" @click.stop>
      <div class="icon-buttons" v-if="!showDeleteConfirm">
        <div class="preset-selector-wrapper">
          <button 
            @click="togglePresetMenu" 
            class="btn-icon btn-preset"
            :disabled="isProcessing"
            :title="`Compress with ${getPresetLabel(selectedPreset)}`"
          >
            <span class="icon">{{ getPresetIcon(selectedPreset) }}</span>
            <span class="tooltip">{{ getPresetLabel(selectedPreset) }}</span>
          </button>
          
          <div v-if="showPresetMenu" class="preset-menu" @click.stop>
            <button 
              v-for="preset in presets" 
              :key="preset.name"
              @click="selectPreset(preset.name)"
              class="preset-option"
              :class="{ 'active': selectedPreset === preset.name }"
            >
              <span class="preset-icon">{{ getPresetIcon(preset.name) }}</span>
              <div class="preset-info">
                <span class="preset-label">{{ preset.label }}</span>
                <span class="preset-desc">{{ preset.description }}</span>
              </div>
            </button>
          </div>
        </div>
        <button 
          @click="handleRotate" 
          class="btn-icon"
          :disabled="isProcessing"
          :title="'Rotate 90° clockwise'"
        >
          <span class="icon">↻</span>
          <span class="tooltip">Rotate 90°</span>
        </button>

        <button 
          @click="handleFlipHorizontal" 
          class="btn-icon"
          :disabled="isProcessing"
          :title="'Flip horizontally'"
        >
          <span class="icon">⇄</span>
          <span class="tooltip">Flip H</span>
        </button>

        <button 
          @click="handleFlipVertical" 
          class="btn-icon"
          :disabled="isProcessing"
          :title="'Flip vertically'"
        >
          <span class="icon">⇅</span>
          <span class="tooltip">Flip V</span>
        </button>

        <button 
          @click="handleEdit" 
          class="btn-icon btn-edit"
          :disabled="isProcessing"
          :title="'Open advanced editor'"
        >
          <span class="icon">✏️</span>
          <span class="tooltip">Edit</span>
        </button>

        <button 
          @click="handleRemoveBackground" 
          class="btn-icon btn-ai"
          :disabled="isProcessing"
          :title="'Remove background (AI)'"
        >
          <span class="icon">🎨</span>
          <span class="tooltip">Remove BG</span>
        </button>

        <button 
          @click="handleUndo" 
          class="btn-icon"
          :disabled="!canUndo || isProcessing"
          :title="'Undo last operation'"
        >
          <span class="icon">↶</span>
          <span class="tooltip">Undo</span>
        </button>

        <button 
          @click="handleDownload" 
          class="btn-icon"
          :disabled="isProcessing"
          :title="'Download image'"
        >
          <span class="icon">⬇</span>
          <span class="tooltip">Download</span>
        </button>

        <button 
          @click="showDeleteConfirm = true" 
          class="btn-icon btn-danger-icon"
          :disabled="isProcessing"
          :title="'Remove image'"
        >
          <span class="icon">🗑</span>
          <span class="tooltip">Remove</span>
        </button>
      </div>
      
      <!-- Remove confirmation -->
      <div v-else class="delete-confirm">
        <span class="delete-message">Remove {{ image.original_filename }}?</span>
        <div class="delete-actions">
          <button 
            @click="confirmDelete" 
            class="btn-confirm btn-danger"
            :disabled="isProcessing"
          >
            {{ isProcessing ? '⏳' : '✓' }} Remove
          </button>
          <button 
            @click="showDeleteConfirm = false" 
            class="btn-confirm btn-cancel"
            :disabled="isProcessing"
          >
            ✕ Cancel
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { useImageStore } from '../stores/imageStore';
import { historyService } from '../services/api';

const props = defineProps({
  image: {
    type: Object,
    required: true
  },
  presets: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(['image-click', 'edit-click']);

const imageStore = useImageStore();
const selectedPreset = ref('');
const isProcessing = ref(false);
const canUndo = ref(false);
const showPresetMenu = ref(false);
const imageRefreshKey = ref(Date.now());
const showDeleteConfirm = ref(false);

const isSelected = computed(() => imageStore.isSelected(props.image.id));

const thumbnailUrl = computed(() => {
  const baseUrl = props.image.thumbnail_url;
  // Add cache-busting parameter to force reload after operations
  return `${baseUrl}?t=${imageRefreshKey.value}`;
});

const compressionRatio = computed(() => {
  if (props.image.current_size >= props.image.original_size) return null;
  const ratio = ((props.image.original_size - props.image.current_size) / props.image.original_size) * 100;
  return Math.round(ratio);
});

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
};

const getPresetIcon = (presetName) => {
  if (!presetName) return '⚡';
  const icons = {
    email: '📧',
    web: '🌐',
    web_hq: '⭐',
    custom: '⚙️'
  };
  return icons[presetName] || '⚡';
};

const getPresetLabel = (presetName) => {
  if (!presetName) return 'Select Preset';
  const preset = props.presets.find(p => p.name === presetName);
  return preset ? preset.label : 'Select Preset';
};

const togglePresetMenu = () => {
  showPresetMenu.value = !showPresetMenu.value;
};

const selectPreset = async (presetName) => {
  selectedPreset.value = presetName;
  showPresetMenu.value = false;
  // Auto-compress when preset is selected
  await handleCompress();
};

const handleCardClick = () => {
  imageStore.toggleSelection(props.image.id);
};

const handleImageClick = () => {
  emit('image-click', props.image);
};

const handleCompress = async () => {
  if (!selectedPreset.value) return;

  isProcessing.value = true;
  try {
    await imageStore.compressImage(props.image.id, selectedPreset.value);
    imageRefreshKey.value = Date.now(); // Force image refresh
    await checkCanUndo();
  } catch (error) {
    console.error('Compression failed:', error);
  } finally {
    isProcessing.value = false;
  }
};

const handleRotate = async () => {
  isProcessing.value = true;
  try {
    await imageStore.rotateImage(props.image.id, 90);
    imageRefreshKey.value = Date.now(); // Force image refresh
    await checkCanUndo();
  } catch (error) {
    console.error('Rotate failed:', error);
  } finally {
    isProcessing.value = false;
  }
};

const handleFlipHorizontal = async () => {
  isProcessing.value = true;
  try {
    await imageStore.flipImage(props.image.id, 'horizontal');
    imageRefreshKey.value = Date.now(); // Force image refresh
    await checkCanUndo();
  } catch (error) {
    console.error('Flip failed:', error);
  } finally {
    isProcessing.value = false;
  }
};

const handleFlipVertical = async () => {
  isProcessing.value = true;
  try {
    await imageStore.flipImage(props.image.id, 'vertical');
    imageRefreshKey.value = Date.now(); // Force image refresh
    await checkCanUndo();
  } catch (error) {
    console.error('Flip failed:', error);
  } finally {
    isProcessing.value = false;
  }
};

const handleUndo = async () => {
  isProcessing.value = true;
  try {
    await imageStore.undoOperation(props.image.id);
    imageRefreshKey.value = Date.now(); // Force image refresh
    selectedPreset.value = ''; // Reset preset selection
    await checkCanUndo();
  } catch (error) {
    console.error('Undo failed:', error);
  } finally {
    isProcessing.value = false;
  }
};

const handleDownload = () => {
  window.open(props.image.image_url, '_blank');
};

const handleEdit = () => {
  emit('edit-click', props.image);
};

const handleRemoveBackground = async () => {
  isProcessing.value = true;
  try {
    await imageStore.removeBackground(props.image.id);
    imageRefreshKey.value = Date.now(); // Force image refresh
    await checkCanUndo();
  } catch (error) {
    console.error('Background removal failed:', error);
  } finally {
    isProcessing.value = false;
  }
};

const confirmDelete = async () => {
  isProcessing.value = true;
  try {
    await imageStore.deleteImage(props.image.id);
  } catch (error) {
    console.error('Delete failed:', error);
    showDeleteConfirm.value = false;
  } finally {
    isProcessing.value = false;
  }
};

const checkCanUndo = async () => {
  try {
    const result = await historyService.canUndo(props.image.id);
    canUndo.value = result.can_undo;
  } catch (error) {
    canUndo.value = false;
  }
};

const handleClickOutside = (event) => {
  if (showPresetMenu.value) {
    showPresetMenu.value = false;
  }
};

// Watch for image changes and update refresh key to bust cache
watch(() => props.image.current_path, (newPath, oldPath) => {
  if (newPath !== oldPath) {
    console.log('[ImageCard] Image path changed, updating cache key');
    imageRefreshKey.value = Date.now();
  }
});

// Also watch thumbnail_path in case it changes independently
watch(() => props.image.thumbnail_path, (newPath, oldPath) => {
  if (newPath !== oldPath) {
    console.log('[ImageCard] Thumbnail path changed, updating cache key');
    imageRefreshKey.value = Date.now();
  }
});

onMounted(() => {
  checkCanUndo();
  document.addEventListener('click', handleClickOutside);
});

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
.image-card {
  border: 2px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
  background-color: #fff;
  transition: all 0.2s ease;
  cursor: pointer;
  position: relative;
  overflow: visible;
  isolation: isolate;
}

.image-card:hover {
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
  border-color: #bbb;
}

.image-card.selected {
  border-color: #4CAF50;
  background-color: #f1f8f4;
  box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.3);
}

.image-preview {
  width: 100%;
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f5f5f5;
  border-radius: 4px;
  overflow: hidden;
  cursor: zoom-in;
  margin-bottom: 1rem;
}

.image-preview:hover {
  background-color: #f0f0f0;
}

.image-preview img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.image-info {
  margin-bottom: 1rem;
  font-size: 0.85rem;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 0.25rem 0;
}

.info-row .label {
  color: #666;
}

.info-row .value {
  font-weight: 500;
  color: #333;
}

.info-row.compression-ratio .value {
  color: #4CAF50;
  font-weight: 600;
}

.card-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  position: relative;
  overflow: visible;
  z-index: 1;
}

.preset-selector-wrapper {
  position: relative;
  overflow: visible;
}

.btn-preset {
  background-color: #4CAF50;
  color: white;
  border-color: #4CAF50;
}

.btn-preset:hover:not(:disabled) {
  background-color: #45a049;
  border-color: #45a049;
}

.preset-menu {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 0.25rem;
  background: white;
  border: 1px solid #ddd;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  z-index: 100;
  min-width: 250px;
  max-height: 300px;
  overflow-y: auto;
}

.preset-option {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.75rem;
  border: none;
  background: white;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.2s ease;
  border-bottom: 1px solid #f0f0f0;
}

.preset-option:last-child {
  border-bottom: none;
}

.preset-option:hover {
  background-color: #f5f5f5;
}

.preset-option.active {
  background-color: #e8f5e9;
  border-left: 3px solid #4CAF50;
}

.preset-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.preset-info {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  flex: 1;
}

.preset-label {
  font-weight: 600;
  color: #333;
  font-size: 0.9rem;
}

.preset-desc {
  font-size: 0.75rem;
  color: #666;
}

.icon-buttons {
  display: flex;
  gap: 0.35rem;
  justify-content: space-between;
  position: relative;
  overflow: visible;
  z-index: 10;
}

.btn-icon {
  flex: 1;
  position: relative;
  padding: 0.4rem 0.25rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: white;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  z-index: 100;
}

.btn-icon:hover:not(:disabled) {
  background-color: #f5f5f5;
  border-color: #4CAF50;
  transform: translateY(-2px);
  z-index: 999998;
}

.btn-icon:active:not(:disabled) {
  transform: translateY(0);
}

.btn-icon:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-icon .icon {
  font-size: 1rem;
  display: block;
  color: #333;
}

.btn-preset .icon {
  color: white;
}

.btn-edit {
  background-color: #2196F3;
  color: white;
  border-color: #2196F3;
}

.btn-edit:hover:not(:disabled) {
  background-color: #1976D2;
  border-color: #1976D2;
}

.btn-edit .icon {
  color: white;
}

.btn-ai {
  background-color: #9C27B0;
  color: white;
  border-color: #9C27B0;
}

.btn-ai:hover:not(:disabled) {
  background-color: #7B1FA2;
  border-color: #7B1FA2;
}

.btn-ai .icon {
  color: white;
}

.btn-danger-icon:hover:not(:disabled) {
  border-color: #f44336;
  background-color: #ffebee;
}

.tooltip {
  position: absolute;
  top: auto;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%) translateY(-8px);
  background-color: rgba(0, 0, 0, 0.9);
  color: white;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  font-size: 0.75rem;
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.2s ease, transform 0.2s ease;
  z-index: 999999;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

.tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: rgba(0, 0, 0, 0.9);
}

.btn-icon:hover:not(:disabled) .tooltip {
  opacity: 1;
  transform: translateX(-50%) translateY(-12px);
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

.delete-confirm {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.5rem;
  background-color: #fff3e0;
  border: 1px solid #ff9800;
  border-radius: 4px;
}

.delete-message {
  font-size: 0.9rem;
  font-weight: 500;
  color: #e65100;
  text-align: center;
  word-break: break-word;
}

.delete-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
}

.btn-confirm {
  flex: 1;
  padding: 0.6rem;
  border: none;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
}

.btn-confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-danger {
  background-color: #f44336;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background-color: #d32f2f;
  transform: translateY(-1px);
}

.btn-cancel {
  background-color: #e0e0e0;
  color: #333;
}

.btn-cancel:hover:not(:disabled) {
  background-color: #bdbdbd;
  transform: translateY(-1px);
}
</style>
