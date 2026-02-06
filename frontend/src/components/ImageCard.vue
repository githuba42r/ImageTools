<template>
  <div 
    class="image-card" 
    :class="{ 'selected': isSelected }"
    @click="handleCardClick"
  >
    <div class="image-preview" @click.stop="handleImageClick">
      <img :src="thumbnailUrl" :alt="image.original_filename" :title="image.original_filename" />
      
      <!-- Processing Overlay -->
      <div v-if="isProcessing" class="processing-overlay">
        <div class="processing-modal">
          <div class="spinner"></div>
          <div class="processing-text">{{ processingMessage }}</div>
        </div>
      </div>
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
            @click="openResizeModal" 
            class="btn-icon btn-resize"
            :disabled="isProcessing"
            :title="'Resize image'"
          >
            <span class="icon">⇲</span>
            <span class="tooltip">Resize</span>
          </button>

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
            @click="openChatInterface" 
            class="btn-icon btn-ai"
            :disabled="isProcessing"
            :title="'AI Chat - Ask AI to modify image'"
          >
            <span class="icon">💬</span>
            <span class="tooltip">AI Chat</span>
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

    <!-- Chat Interface Modal -->
    <ChatInterface
      v-if="showChatInterface"
      :image="image"
      :sessionId="sessionId"
      :selectedModel="selectedModel"
      :isConnected="isOpenRouterConnected"
      @close="closeChatInterface"
      @operationsApplied="handleOperationsApplied"
    />

    <!-- Resize Modal -->
    <div v-if="showResizeModal" class="modal-backdrop" @click="closeResizeModal">
      <div class="resize-modal" @click.stop>
        <div class="resize-header">
          <h3>Resize Image</h3>
          <button class="close-btn" @click="closeResizeModal">✕</button>
        </div>
        
        <div class="resize-content">
          <div class="resize-preview">
            <div class="preview-label">Preview</div>
            <div class="preview-box">
              <div 
                class="preview-image"
                :style="{
                  width: previewWidth + 'px',
                  height: previewHeight + 'px',
                  backgroundImage: `url(${thumbnailUrl})`
                }"
              ></div>
            </div>
            <div class="preview-dimensions">
              {{ calculatedWidth }} × {{ calculatedHeight }} px
            </div>
          </div>
          
          <div class="resize-controls">
            <div class="control-group">
              <label>Width</label>
              <div class="input-wrapper">
                <input 
                  type="number" 
                  v-model="resizeWidth" 
                  @input="onWidthChange"
                  :min="1"
                  class="resize-input"
                />
                <select v-model="widthUnit" @change="onWidthUnitChange" class="unit-select">
                  <option value="px">px</option>
                  <option value="%">%</option>
                </select>
              </div>
            </div>
            
            <div class="control-group">
              <label>Height</label>
              <div class="input-wrapper">
                <input 
                  type="number" 
                  v-model="resizeHeight" 
                  @input="onHeightChange"
                  :min="1"
                  class="resize-input"
                />
                <select v-model="heightUnit" @change="onHeightUnitChange" class="unit-select">
                  <option value="px">px</option>
                  <option value="%">%</option>
                </select>
              </div>
            </div>
            
            <div class="control-group">
              <label class="checkbox-label">
                <input 
                  type="checkbox" 
                  v-model="lockAspectRatio"
                  @change="onAspectLockChange"
                />
                <span>Lock aspect ratio</span>
              </label>
            </div>
            
            <div class="result-info">
              <div class="result-row">
                <span class="label">Original:</span>
                <span class="value">{{ image.width }} × {{ image.height }}</span>
              </div>
              <div class="result-row">
                <span class="label">New size:</span>
                <span class="value">{{ calculatedWidth }} × {{ calculatedHeight }}</span>
              </div>
              <div class="result-row">
                <span class="label">Scale:</span>
                <span class="value">{{ scalePercentage }}%</span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="resize-footer">
          <button class="btn-modal btn-cancel" @click="closeResizeModal">Cancel</button>
          <button class="btn-modal btn-apply" @click="applyResize">Apply</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { useImageStore } from '../stores/imageStore';
import { historyService } from '../services/api';
import ChatInterface from './ChatInterface.vue';

const props = defineProps({
  image: {
    type: Object,
    required: true
  },
  presets: {
    type: Array,
    default: () => []
  },
  sessionId: {
    type: String,
    required: true
  },
  selectedModel: {
    type: String,
    default: null
  },
  isOpenRouterConnected: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['image-click', 'edit-click']);

const imageStore = useImageStore();
const selectedPreset = ref('');
const isProcessing = ref(false);
const processingMessage = ref('');
const canUndo = ref(false);
const showPresetMenu = ref(false);
const imageRefreshKey = ref(Date.now());
const showDeleteConfirm = ref(false);
const showChatInterface = ref(false);

// Resize modal state
const showResizeModal = ref(false);
const resizeWidth = ref(0);
const resizeHeight = ref(0);
const widthUnit = ref('px');
const heightUnit = ref('px');
const lockAspectRatio = ref(true);
const aspectRatio = ref(1);

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

// Resize computed properties
const calculatedWidth = computed(() => {
  if (widthUnit.value === '%') {
    return Math.round(props.image.width * (resizeWidth.value / 100));
  }
  return Math.round(resizeWidth.value);
});

const calculatedHeight = computed(() => {
  if (heightUnit.value === '%') {
    return Math.round(props.image.height * (resizeHeight.value / 100));
  }
  return Math.round(resizeHeight.value);
});

const scalePercentage = computed(() => {
  const widthScale = (calculatedWidth.value / props.image.width) * 100;
  const heightScale = (calculatedHeight.value / props.image.height) * 100;
  return Math.round((widthScale + heightScale) / 2);
});

const previewWidth = computed(() => {
  const maxPreviewSize = 150;
  const scale = Math.min(maxPreviewSize / calculatedWidth.value, maxPreviewSize / calculatedHeight.value, 1);
  return Math.round(calculatedWidth.value * scale);
});

const previewHeight = computed(() => {
  const maxPreviewSize = 150;
  const scale = Math.min(maxPreviewSize / calculatedWidth.value, maxPreviewSize / calculatedHeight.value, 1);
  return Math.round(calculatedHeight.value * scale);
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
  processingMessage.value = 'Compressing...';
  try {
    await imageStore.compressImage(props.image.id, selectedPreset.value);
    imageRefreshKey.value = Date.now(); // Force image refresh
    await checkCanUndo();
  } catch (error) {
    console.error('Compression failed:', error);
  } finally {
    isProcessing.value = false;
    processingMessage.value = '';
  }
};

const handleRotate = async () => {
  isProcessing.value = true;
  processingMessage.value = 'Rotating...';
  try {
    await imageStore.rotateImage(props.image.id, 90);
    imageRefreshKey.value = Date.now(); // Force image refresh
    await checkCanUndo();
  } catch (error) {
    console.error('Rotate failed:', error);
  } finally {
    isProcessing.value = false;
    processingMessage.value = '';
  }
};

const handleFlipHorizontal = async () => {
  isProcessing.value = true;
  processingMessage.value = 'Flipping...';
  try {
    await imageStore.flipImage(props.image.id, 'horizontal');
    imageRefreshKey.value = Date.now(); // Force image refresh
    await checkCanUndo();
  } catch (error) {
    console.error('Flip failed:', error);
  } finally {
    isProcessing.value = false;
    processingMessage.value = '';
  }
};

const handleFlipVertical = async () => {
  isProcessing.value = true;
  processingMessage.value = 'Flipping...';
  try {
    await imageStore.flipImage(props.image.id, 'vertical');
    imageRefreshKey.value = Date.now(); // Force image refresh
    await checkCanUndo();
  } catch (error) {
    console.error('Flip failed:', error);
  } finally {
    isProcessing.value = false;
    processingMessage.value = '';
  }
};

const handleUndo = async () => {
  isProcessing.value = true;
  processingMessage.value = 'Undoing...';
  try {
    await imageStore.undoOperation(props.image.id);
    imageRefreshKey.value = Date.now(); // Force image refresh
    selectedPreset.value = ''; // Reset preset selection
    await checkCanUndo();
  } catch (error) {
    console.error('Undo failed:', error);
  } finally {
    isProcessing.value = false;
    processingMessage.value = '';
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
  processingMessage.value = 'Removing background...';
  try {
    await imageStore.removeBackground(props.image.id);
    // Wait for Vue to update the DOM before refreshing the image
    await nextTick();
    imageRefreshKey.value = Date.now(); // Force image refresh
    await checkCanUndo();
  } catch (error) {
    console.error('Background removal failed:', error);
  } finally {
    isProcessing.value = false;
    processingMessage.value = '';
  }
};

const openChatInterface = () => {
  showChatInterface.value = true;
};

const closeChatInterface = () => {
  showChatInterface.value = false;
};

const handleOperationsApplied = (operations) => {
  console.log('Operations applied:', operations);
  imageRefreshKey.value = Date.now(); // Force reload
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

// Resize modal methods
const openResizeModal = () => {
  resizeWidth.value = props.image.width;
  resizeHeight.value = props.image.height;
  widthUnit.value = 'px';
  heightUnit.value = 'px';
  lockAspectRatio.value = true;
  aspectRatio.value = props.image.width / props.image.height;
  showResizeModal.value = true;
};

const closeResizeModal = () => {
  showResizeModal.value = false;
};

const onWidthChange = () => {
  if (lockAspectRatio.value) {
    if (widthUnit.value === 'px') {
      resizeHeight.value = Math.round(resizeWidth.value / aspectRatio.value);
    } else {
      resizeHeight.value = resizeWidth.value;
    }
    heightUnit.value = widthUnit.value;
  }
};

const onHeightChange = () => {
  if (lockAspectRatio.value) {
    if (heightUnit.value === 'px') {
      resizeWidth.value = Math.round(resizeHeight.value * aspectRatio.value);
    } else {
      resizeWidth.value = resizeHeight.value;
    }
    widthUnit.value = heightUnit.value;
  }
};

const onWidthUnitChange = () => {
  // Convert value when switching units
  if (widthUnit.value === '%') {
    // Convert from px to %
    resizeWidth.value = Math.round((resizeWidth.value / props.image.width) * 100);
  } else {
    // Convert from % to px
    resizeWidth.value = Math.round((resizeWidth.value / 100) * props.image.width);
  }
  
  if (lockAspectRatio.value) {
    heightUnit.value = widthUnit.value;
    resizeHeight.value = resizeWidth.value;
  }
};

const onHeightUnitChange = () => {
  // Convert value when switching units
  if (heightUnit.value === '%') {
    // Convert from px to %
    resizeHeight.value = Math.round((resizeHeight.value / props.image.height) * 100);
  } else {
    // Convert from % to px
    resizeHeight.value = Math.round((resizeHeight.value / 100) * props.image.height);
  }
  
  if (lockAspectRatio.value) {
    widthUnit.value = heightUnit.value;
    resizeWidth.value = resizeHeight.value;
  }
};

const onAspectLockChange = () => {
  if (lockAspectRatio.value) {
    aspectRatio.value = calculatedWidth.value / calculatedHeight.value;
    onWidthChange();
  }
};

const applyResize = async () => {
  const width = calculatedWidth.value;
  const height = calculatedHeight.value;
  
  if (width <= 0 || height <= 0) {
    alert('Width and height must be greater than 0');
    return;
  }
  
  closeResizeModal();
  isProcessing.value = true;
  processingMessage.value = 'Resizing...';
  
  try {
    await imageStore.resizeImage(props.image.id, width, height);
    await nextTick();
    imageRefreshKey.value = Date.now();
    await checkCanUndo();
  } catch (error) {
    console.error('Resize failed:', error);
    alert('Resize failed: ' + error.message);
  } finally {
    isProcessing.value = false;
    processingMessage.value = '';
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

// Watch updated_at to catch any image updates
watch(() => props.image.updated_at, (newTime, oldTime) => {
  if (newTime !== oldTime) {
    console.log('[ImageCard] Image updated_at changed, updating cache key');
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
  position: relative;
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

.processing-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  backdrop-filter: blur(2px);
}

.processing-modal {
  background-color: white;
  padding: 1.5rem 2rem;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  min-width: 150px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #9C27B0;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.processing-text {
  font-size: 0.9rem;
  font-weight: 600;
  color: #333;
  text-align: center;
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
  grid-column: span 1;
}

.btn-preset {
  background-color: white;
  color: #333;
  border-color: #ddd;
  width: 100%;
}

.btn-preset:hover:not(:disabled) {
  background-color: #f5f5f5;
  border-color: #bbb;
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
  z-index: 1000000;
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
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0.35rem;
  position: relative;
  overflow: visible;
  z-index: 10;
}

.btn-icon {
  position: relative;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: white;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  min-height: 40px;
  z-index: 100;
}

.btn-icon:hover:not(:disabled) {
  background-color: #f5f5f5;
  border-color: #bbb;
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

.btn-danger-icon:hover:not(:disabled) {
  border-color: #bbb;
  background-color: #f5f5f5;
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

/* Resize Button */
.btn-resize {
  background-color: white;
  color: #333;
  border-color: #ddd;
}

.btn-resize:hover:not(:disabled) {
  background-color: #f5f5f5;
  border-color: #bbb;
}

/* Resize Modal */
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  backdrop-filter: blur(3px);
}

.resize-modal {
  background-color: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.resize-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid #e0e0e0;
}

.resize-header h3 {
  margin: 0;
  font-size: 1.25rem;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #666;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background-color: #f5f5f5;
  color: #333;
}

.resize-content {
  padding: 1.5rem;
  display: flex;
  gap: 2rem;
  overflow-y: auto;
}

.resize-preview {
  flex: 0 0 180px;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.preview-label {
  font-weight: 600;
  font-size: 0.9rem;
  color: #333;
}

.preview-box {
  width: 180px;
  height: 180px;
  border: 2px dashed #ddd;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f9f9f9;
  padding: 10px;
}

.preview-image {
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.preview-dimensions {
  font-size: 0.85rem;
  color: #666;
  text-align: center;
}

.resize-controls {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.control-group label {
  font-weight: 600;
  font-size: 0.9rem;
  color: #333;
}

.input-wrapper {
  display: flex;
  gap: 0.5rem;
}

.resize-input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.2s ease;
}

.resize-input:focus {
  outline: none;
  border-color: #FF9800;
}

.unit-select {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: white;
  font-size: 1rem;
  cursor: pointer;
  min-width: 70px;
}

.unit-select:focus {
  outline: none;
  border-color: #FF9800;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-weight: normal !important;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.result-info {
  padding: 1rem;
  background-color: #f5f5f5;
  border-radius: 6px;
  border-left: 3px solid #FF9800;
}

.result-row {
  display: flex;
  justify-content: space-between;
  padding: 0.4rem 0;
  font-size: 0.9rem;
}

.result-row .label {
  color: #666;
  font-weight: 500;
}

.result-row .value {
  color: #333;
  font-weight: 600;
}

.resize-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid #e0e0e0;
  background-color: #fafafa;
}

.btn-modal {
  padding: 0.6rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-modal.btn-cancel {
  background-color: #e0e0e0;
  color: #333;
}

.btn-modal.btn-cancel:hover {
  background-color: #bdbdbd;
}

.btn-modal.btn-apply {
  background-color: #FF9800;
  color: white;
}

.btn-modal.btn-apply:hover {
  background-color: #F57C00;
}
</style>
