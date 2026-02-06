<template>
  <div id="app">
    <header class="app-header" :class="{ 'compact': imageCount > 0 }">
      <div class="header-content">
        <div class="header-left">
          <h1 class="has-tooltip">
            🖼️ Image Tools
            <span class="tooltip-text">Image Tools v1.0 | Session: {{ sessionId ? sessionId.substring(0, 8) + '...' : 'None' }}</span>
          </h1>
          <p v-if="imageCount === 0" class="subtitle">Compress and manage your images</p>
          
          <!-- Image count and selection info -->
          <div v-if="imageCount > 0" class="image-stats">
            <span class="image-count">{{ imageCount }} image{{ imageCount !== 1 ? 's' : '' }}</span>
            <span v-if="selectedCount > 0" class="selected-count">
              ({{ selectedCount }} selected)
            </span>
          </div>
        </div>
        
        <div v-if="imageCount > 0" class="header-right">
          <!-- Toolbar actions -->
          <div class="toolbar-actions">
            <button 
              @click="selectAll" 
              class="btn-icon btn-header"
              :disabled="imageCount === 0"
              title="Select all images"
            >
              <span class="icon">☑</span>
              <span class="tooltip">Select All</span>
            </button>

            <button 
              @click="clearSelection" 
              class="btn-icon btn-header"
              :disabled="selectedCount === 0"
              title="Clear selection"
            >
              <span class="icon">☐</span>
              <span class="tooltip">Clear Selection</span>
            </button>

            <!-- Bulk compress with icon popup -->
            <div class="preset-selector-wrapper" @click.stop>
              <button 
                @click="toggleBulkPresetMenu" 
                class="btn-icon btn-header btn-compress-bulk"
                :disabled="selectedCount === 0 || isBulkProcessing"
                :title="`Bulk compress ${selectedCount} selected`"
              >
                <span class="icon">{{ isBulkProcessing ? '⏳' : (bulkSelectedPreset ? getPresetIcon(bulkSelectedPreset) : '⚡') }}</span>
                <span class="tooltip">{{ isBulkProcessing ? 'Processing...' : 'Bulk Compress' }}</span>
              </button>
              
              <div v-if="showBulkPresetMenu" class="preset-menu" @click.stop>
                <button 
                  v-for="preset in presets" 
                  :key="preset.name"
                  @click="selectBulkPreset(preset.name)"
                  class="preset-option"
                  :class="{ 'active': bulkSelectedPreset === preset.name }"
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
              @click="handleDownloadZip" 
              class="btn-icon btn-header"
              :disabled="selectedCount === 0"
              title="Download selected images as ZIP"
            >
              <span class="icon">⬇</span>
              <span class="tooltip">Download ZIP</span>
            </button>

            <button 
              @click="showClearAllConfirm = true" 
              class="btn-icon btn-header btn-danger-header"
              :disabled="imageCount === 0"
              title="Clear all images"
            >
              <span class="icon">🗑</span>
              <span class="tooltip">Clear All</span>
            </button>
          </div>
          
          <div class="header-spacer"></div>
          
          <UploadArea @upload-complete="handleUploadComplete" :compact="true" :inline="true" />
        </div>
      </div>
    </header>

    <main class="app-main">
      <div class="container">
        <div v-if="isLoading" class="loading-state">
          <div class="spinner-large"></div>
          <p>Loading session...</p>
        </div>

        <div v-else-if="error" class="error-state">
          <p>{{ error }}</p>
          <button @click="initializeApp" class="btn btn-primary">
            Retry
          </button>
        </div>

        <div v-else>
          <div v-if="imageCount > 0" class="content-with-images">
            <div class="main-content">
              <div class="image-gallery">
                <ImageCard
                  v-for="image in images"
                  :key="image.id"
                  :image="image"
                  :presets="presets"
                  @image-click="handleImageClick"
                  @edit-click="handleEditClick"
                />
              </div>
            </div>
          </div>

          <div v-else>
            <UploadArea @upload-complete="handleUploadComplete" :compact="false" :inline="false" />
          </div>
        </div>
      </div>
    </main>

    <!-- Clear All Confirmation Modal -->
    <div v-if="showClearAllConfirm" class="modal-overlay" @click="showClearAllConfirm = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Clear All Images?</h2>
        </div>
        <div class="modal-body">
          <p>Are you sure you want to remove all <strong>{{ imageCount }}</strong> image{{ imageCount !== 1 ? 's' : '' }}?</p>
          <p class="modal-warning">This action cannot be undone.</p>
        </div>
        <div class="modal-footer">
          <button 
            @click="showClearAllConfirm = false" 
            class="btn-modal btn-cancel"
            :disabled="isClearingAll"
          >
            Cancel
          </button>
          <button 
            @click="confirmClearAll" 
            class="btn-modal btn-danger"
            :disabled="isClearingAll"
          >
            {{ isClearingAll ? '⏳ Removing...' : '🗑 Remove All' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Image Viewer Modal -->
    <ImageViewer 
      v-if="viewerImage"
      :image="viewerImage"
      :all-images="images"
      @close="handleCloseViewer"
      @navigate="handleNavigateViewer"
    />

    <!-- Image Editor Modal -->
    <ImageEditor
      v-if="editingImage"
      :image="editingImage"
      @save="handleEditorSave"
      @close="handleEditorClose"
    />

  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { useSessionStore } from './stores/sessionStore';
import { useImageStore } from './stores/imageStore';
import { storeToRefs } from 'pinia';
import { imageService } from './services/api';
import UploadArea from './components/UploadArea.vue';
import ImageCard from './components/ImageCard.vue';
import ImageViewer from './components/ImageViewer.vue';
import ImageEditor from './components/ImageEditor.vue';

const sessionStore = useSessionStore();
const imageStore = useImageStore();

const { sessionId } = storeToRefs(sessionStore);
const { images, imageCount, selectedCount, presets } = storeToRefs(imageStore);

const isLoading = ref(true);
const error = ref(null);
const showBulkPresetMenu = ref(false);
const bulkSelectedPreset = ref('');
const isBulkProcessing = ref(false);
const showClearAllConfirm = ref(false);
const isClearingAll = ref(false);
const viewerImage = ref(null);
const editingImage = ref(null);

const initializeApp = async () => {
  isLoading.value = true;
  error.value = null;

  try {
    await sessionStore.initializeSession();
    await Promise.all([
      imageStore.loadSessionImages(),
      imageStore.loadPresets()
    ]);
  } catch (err) {
    error.value = 'Failed to initialize application: ' + err.message;
    console.error('Initialization error:', err);
  } finally {
    isLoading.value = false;
  }
};

const handleUploadComplete = ({ successCount, failCount }) => {
  if (successCount > 0) {
    console.log(`Successfully uploaded ${successCount} image(s)`);
  }
  if (failCount > 0) {
    console.error(`Failed to upload ${failCount} image(s)`);
  }
};

const handleImageClick = (image) => {
  console.log('Image clicked:', image.id);
  viewerImage.value = image;
};

const handleCloseViewer = () => {
  viewerImage.value = null;
};

const handleNavigateViewer = (image) => {
  viewerImage.value = image;
};

const handleEditClick = (image) => {
  console.log('Edit clicked for image:', image.id);
  editingImage.value = image;
};

const handleEditorSave = async (blob) => {
  if (!editingImage.value) return;

  try {
    console.log('Saving edited image...', {
      imageId: editingImage.value.id,
      filename: editingImage.value.original_filename,
      blobSize: blob.size,
      blobType: blob.type
    });

    // Create FormData with the edited image blob
    const formData = new FormData();
    formData.append('file', blob, editingImage.value.original_filename);

    // Call backend API to save edited image
    const response = await imageService.saveEditedImage(editingImage.value.id, formData);
    
    console.log('API response:', response);
    
    // Refresh the image in the store
    await imageStore.loadSessionImages();
    
    // Close the editor
    editingImage.value = null;
    
    console.log('Image edited successfully:', response);
  } catch (error) {
    console.error('Failed to save edited image:', error);
    console.error('Error details:', {
      message: error.message,
      response: error.response?.data,
      status: error.response?.status
    });
    alert('Failed to save edited image. Please try again.');
  }
};

const handleEditorClose = () => {
  editingImage.value = null;
};

// Toolbar actions
const selectAll = () => {
  imageStore.selectAll();
};

const clearSelection = () => {
  imageStore.clearSelection();
};

const getPresetIcon = (presetName) => {
  const icons = {
    email: '📧',
    web: '🌐',
    web_hq: '⭐',
    custom: '⚙️'
  };
  return icons[presetName] || '⚡';
};

const toggleBulkPresetMenu = () => {
  showBulkPresetMenu.value = !showBulkPresetMenu.value;
};

const selectBulkPreset = async (presetName) => {
  bulkSelectedPreset.value = presetName;
  showBulkPresetMenu.value = false;
  // Auto-compress when preset is selected
  await handleBulkCompress(presetName);
};

const handleBulkCompress = async (presetName) => {
  if (!presetName || selectedCount.value === 0) return;

  isBulkProcessing.value = true;
  try {
    const results = await imageStore.compressSelected(presetName);
    const successCount = results.filter(r => r.success).length;
    console.log(`Compressed ${successCount}/${results.length} images`);
  } catch (error) {
    console.error('Bulk compression failed:', error);
  } finally {
    isBulkProcessing.value = false;
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

const handleDownloadZip = async () => {
  if (selectedCount.value === 0) return;

  try {
    // Get the blob from the API
    const blob = await imageService.downloadImagesAsZip(imageStore.selectedImages);
    
    // Create download link with date in filename
    const date = new Date().toISOString().split('T')[0]; // YYYY-MM-DD format
    const filename = `Images-${date}.zip`;
    
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    
    // Cleanup
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    
    console.log(`Downloaded ${imageStore.selectedImages.length} images as ${filename}`);
  } catch (error) {
    console.error('Download ZIP failed:', error);
  }
};

const handleClickOutside = () => {
  if (showBulkPresetMenu.value) {
    showBulkPresetMenu.value = false;
  }
};

const confirmClearAll = async () => {
  isClearingAll.value = true;
  try {
    // Delete all images
    const deletePromises = images.value.map(image => imageStore.deleteImage(image.id));
    await Promise.all(deletePromises);
    
    showClearAllConfirm.value = false;
    console.log(`Removed all ${deletePromises.length} images`);
  } catch (error) {
    console.error('Failed to clear all images:', error);
  } finally {
    isClearingAll.value = false;
  }
};

const handleKeyboardShortcuts = (event) => {
  // Don't trigger shortcuts if viewer is open or in an input field
  if (viewerImage.value || event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
    return;
  }

  // Ctrl/Cmd + A: Select all images
  if ((event.ctrlKey || event.metaKey) && event.key === 'a' && imageCount.value > 0) {
    event.preventDefault();
    selectAll();
  }

  // Escape: Clear selection
  if (event.key === 'Escape' && selectedCount.value > 0) {
    clearSelection();
  }

  // Delete: Delete selected images (with confirmation would be better, but for now just log)
  if (event.key === 'Delete' && selectedCount.value > 0) {
    event.preventDefault();
    // For safety, we'll just clear selection instead of deleting
    // To enable deletion, uncomment the lines below
    // const confirmed = confirm(`Delete ${selectedCount.value} selected image(s)?`);
    // if (confirmed) {
    //   imageStore.selectedImages.forEach(id => imageStore.deleteImage(id));
    // }
    console.log('Delete key pressed. For safety, this only clears selection. Use remove buttons to delete.');
    clearSelection();
  }
};

onMounted(() => {
  initializeApp();
  document.addEventListener('click', handleClickOutside);
  document.addEventListener('keydown', handleKeyboardShortcuts);
});

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside);
  document.removeEventListener('keydown', handleKeyboardShortcuts);
});
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background-color: #f0f2f5;
  color: #333;
}

#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1rem;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: padding 0.3s ease;
}

.app-header.compact {
  padding: 0.375rem 1rem;
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  text-align: left;
  flex: 1;
}

.header-right {
  flex-shrink: 0;
  margin-left: 2rem;
}

.app-header h1 {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
  transition: font-size 0.3s ease, margin 0.3s ease;
  cursor: help;
  position: relative;
  display: inline-block;
}

.app-header.compact h1 {
  font-size: 1.5rem;
  margin-bottom: 0;
}

/* Tooltip for h1 */
.has-tooltip {
  position: relative;
}

.has-tooltip .tooltip-text {
  visibility: hidden;
  opacity: 0;
  background-color: #333;
  color: #fff;
  text-align: center;
  border-radius: 6px;
  padding: 8px 12px;
  position: absolute;
  z-index: 1000;
  top: 125%;
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
  font-size: 0.85rem;
  font-weight: normal;
  transition: opacity 0.3s, visibility 0.3s;
  pointer-events: none;
}

.has-tooltip .tooltip-text::after {
  content: "";
  position: absolute;
  bottom: 100%;
  left: 50%;
  margin-left: -5px;
  border-width: 5px;
  border-style: solid;
  border-color: transparent transparent #333 transparent;
}

.has-tooltip:hover .tooltip-text {
  visibility: visible;
  opacity: 1;
}

.subtitle {
  font-size: 1.1rem;
  opacity: 0.9;
}

.image-stats {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.95rem;
  margin-top: 0.5rem;
}

.image-count {
  font-weight: 600;
}

.selected-count {
  color: #a5d6a7;
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0;
}

.header-spacer {
  width: 20%;
  min-width: 2rem;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-icon {
  position: relative;
  padding: 0.6rem;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 4px;
  background-color: rgba(255, 255, 255, 0.15);
  color: white;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover:not(:disabled) {
  background-color: rgba(255, 255, 255, 0.25);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-2px);
}

.btn-icon:active:not(:disabled) {
  transform: translateY(0);
}

.btn-icon:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.btn-icon .icon {
  font-size: 1.25rem;
  display: block;
}

.btn-header {
  padding: 0.5rem 0.7rem;
}

.btn-header .icon {
  font-size: 1.1rem;
}

.btn-compress-bulk {
  background-color: rgba(76, 175, 80, 0.3);
  border-color: rgba(76, 175, 80, 0.5);
}

.btn-compress-bulk:hover:not(:disabled) {
  background-color: rgba(76, 175, 80, 0.5);
  border-color: rgba(76, 175, 80, 0.7);
}

.btn-danger-header {
  background-color: rgba(244, 67, 54, 0.3);
  border-color: rgba(244, 67, 54, 0.5);
}

.btn-danger-header:hover:not(:disabled) {
  background-color: rgba(244, 67, 54, 0.5);
  border-color: rgba(244, 67, 54, 0.7);
}

.preset-selector-wrapper {
  position: relative;
}

.preset-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 0.5rem;
  background: white;
  border: 1px solid #ddd;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  z-index: 1000;
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
  color: #333;
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

/* Tooltip for title */
.has-tooltip .tooltip-text {
  visibility: hidden;
  opacity: 0;
  background-color: #333;
  color: #fff;
  text-align: center;
  border-radius: 6px;
  padding: 8px 12px;
  position: absolute;
  z-index: 1000;
  top: 100%;
  left: 0;
  margin-top: 0.5rem;
  white-space: nowrap;
  font-size: 0.85rem;
  font-weight: normal;
  transition: opacity 0.3s, visibility 0.3s;
  pointer-events: none;
}

.has-tooltip .tooltip-text::after {
  content: "";
  position: absolute;
  bottom: 100%;
  left: 1rem;
  margin-left: 0;
  border-width: 5px;
  border-style: solid;
  border-color: transparent transparent #333 transparent;
}

.has-tooltip:hover .tooltip-text {
  visibility: visible;
  opacity: 1;
}

/* Tooltip for action buttons */
.tooltip {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%) translateY(8px);
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
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 4px solid transparent;
  border-bottom-color: #333;
}

.btn-icon:hover:not(:disabled) .tooltip {
  opacity: 1;
  transform: translateX(-50%) translateY(4px);
}

.app-main {
  flex: 1;
  padding: 2rem 1rem;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
}

.loading-state,
.error-state {
  text-align: center;
  padding: 3rem 2rem;
}

.spinner-large {
  width: 60px;
  height: 60px;
  border: 6px solid #f3f3f3;
  border-top: 6px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-state {
  color: #c62828;
}

.error-state .btn {
  margin-top: 1rem;
}

.image-gallery {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
}

.content-with-images {
  display: flex;
  gap: 1.5rem;
  align-items: flex-start;
}

.main-content {
  flex: 1;
  min-width: 0;
  width: 100%;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn-primary {
  background-color: #667eea;
  color: white;
}

.btn-primary:hover {
  background-color: #5568d3;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.modal-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  max-width: 500px;
  width: 90%;
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    transform: translateY(50px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.modal-header {
  padding: 1.5rem;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #333;
}

.modal-body {
  padding: 1.5rem;
}

.modal-body p {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  color: #555;
  line-height: 1.5;
}

.modal-body p:last-child {
  margin-bottom: 0;
}

.modal-warning {
  color: #f57c00;
  font-weight: 600;
  font-size: 0.95rem;
}

.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #e0e0e0;
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.btn-modal {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-modal:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-modal.btn-cancel {
  background-color: #e0e0e0;
  color: #333;
}

.btn-modal.btn-cancel:hover:not(:disabled) {
  background-color: #bdbdbd;
}

.btn-modal.btn-danger {
  background-color: #f44336;
  color: white;
}

.btn-modal.btn-danger:hover:not(:disabled) {
  background-color: #d32f2f;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(244, 67, 54, 0.3);
}
</style>
