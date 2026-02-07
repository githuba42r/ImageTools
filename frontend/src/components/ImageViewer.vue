<template>
  <div v-if="image" class="viewer-overlay" @click="handleClose">
    <div class="viewer-container" @click.stop>
      <!-- Header -->
      <div class="viewer-header">
        <div class="viewer-title">
          <span class="filename">{{ image.original_filename }}</span>
          <span class="dimensions">{{ image.width }} × {{ image.height }}</span>
        </div>
        <button @click="handleClose" class="btn-close" title="Close (Esc)">
          <span class="icon">✕</span>
        </button>
      </div>

      <!-- Main image area -->
      <div class="viewer-body">
        <img 
          :src="fullImageUrl" 
          :alt="image.original_filename"
          class="full-image"
        />
      </div>

      <!-- Footer with metadata -->
      <div class="viewer-footer">
        <div class="metadata-grid">
          <div class="metadata-item">
            <span class="meta-label">Format:</span>
            <span class="meta-value">{{ image.format }}</span>
          </div>
          <div class="metadata-item">
            <span class="meta-label">Original Size:</span>
            <span class="meta-value">{{ formatSize(image.original_size) }}</span>
          </div>
          <div class="metadata-item">
            <span class="meta-label">Current Size:</span>
            <span class="meta-value">{{ formatSize(image.current_size) }}</span>
          </div>
          <div v-if="compressionRatio" class="metadata-item">
            <span class="meta-label">Saved:</span>
            <span class="meta-value savings">{{ compressionRatio }}%</span>
          </div>
        </div>

        <!-- EXIF Data Section (collapsible) -->
        <div v-if="showExif && exifData" class="exif-section">
          <h3 class="exif-title">EXIF Metadata</h3>
          
          <!-- GPS Coordinates if available -->
          <div v-if="hasGpsData" class="gps-section">
            <div class="gps-header">
              <span class="gps-icon">📍</span>
              <span class="gps-title">Location</span>
            </div>
            <div class="gps-info">
              <div class="gps-coords">
                <span class="coord-label">Latitude:</span>
                <span class="coord-value">{{ formatLatitude(exifData.GPS.latitude, exifData.GPS.latitude_ref) }}</span>
              </div>
              <div class="gps-coords">
                <span class="coord-label">Longitude:</span>
                <span class="coord-value">{{ formatLongitude(exifData.GPS.longitude, exifData.GPS.longitude_ref) }}</span>
              </div>
              <div v-if="exifData.GPS.altitude" class="gps-coords">
                <span class="coord-label">Altitude:</span>
                <span class="coord-value">{{ formatAltitude(exifData.GPS.altitude) }}</span>
              </div>
            </div>
            <button @click="openGoogleMaps" class="btn-maps" title="View location on Google Maps">
              <span class="maps-icon">🗺️</span>
              Open in Google Maps
            </button>
          </div>
          
          <div class="exif-grid">
            <div v-for="(value, key) in filteredExifData" :key="key" class="exif-item">
              <span class="exif-key">{{ key }}:</span>
              <span class="exif-value">{{ formatExifValue(key, value) }}</span>
            </div>
          </div>
          <p v-if="Object.keys(filteredExifData).length === 0 && !hasGpsData" class="no-exif">No EXIF data available</p>
        </div>

        <!-- Navigation buttons -->
        <div class="viewer-actions">
          <button 
            @click="handlePrevious" 
            class="btn-nav"
            :disabled="!hasPrevious"
            title="Previous image (←)"
          >
            <span class="icon">←</span>
            Previous
          </button>
          <button 
            @click="toggleExif" 
            class="btn-action btn-exif"
            :title="showExif ? 'Hide EXIF data' : 'Show EXIF data'"
          >
            <span class="icon">ℹ</span>
            {{ showExif ? 'Hide' : 'Show' }} EXIF
          </button>
          <button 
            @click="handleDownload" 
            class="btn-action"
            title="Download image"
          >
            <span class="icon">⬇</span>
            Download
          </button>
          <button 
            @click="handleNext" 
            class="btn-nav"
            :disabled="!hasNext"
            title="Next image (→)"
          >
            Next
            <span class="icon">→</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { imageService } from '../services/api';

const props = defineProps({
  image: {
    type: Object,
    default: null
  },
  allImages: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(['close', 'navigate']);

const showExif = ref(false);
const exifData = ref({});
const isLoadingExif = ref(false);

const fullImageUrl = computed(() => {
  if (!props.image) return '';
  return `${props.image.image_url}?t=${Date.now()}`;
});

const compressionRatio = computed(() => {
  if (!props.image || props.image.current_size >= props.image.original_size) return null;
  const ratio = ((props.image.original_size - props.image.current_size) / props.image.original_size) * 100;
  return Math.round(ratio);
});

const currentIndex = computed(() => {
  return props.allImages.findIndex(img => img.id === props.image?.id);
});

const hasPrevious = computed(() => {
  return currentIndex.value > 0;
});

const hasNext = computed(() => {
  return currentIndex.value < props.allImages.length - 1;
});

// GPS-related computed properties
const hasGpsData = computed(() => {
  return exifData.value.GPS && 
         exifData.value.GPS.latitude !== undefined && 
         exifData.value.GPS.longitude !== undefined;
});

const filteredExifData = computed(() => {
  if (!exifData.value) return {};
  // Filter out GPS data as it's displayed separately
  const filtered = { ...exifData.value };
  delete filtered.GPS;
  return filtered;
});

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
};

const handleClose = () => {
  emit('close');
};

const handlePrevious = () => {
  if (hasPrevious.value) {
    const newImage = props.allImages[currentIndex.value - 1];
    emit('navigate', newImage);
  }
};

const handleNext = () => {
  if (hasNext.value) {
    const newImage = props.allImages[currentIndex.value + 1];
    emit('navigate', newImage);
  }
};

const handleDownload = () => {
  window.open(props.image.image_url, '_blank');
};

const toggleExif = async () => {
  showExif.value = !showExif.value;
  
  // Load EXIF data if not already loaded
  if (showExif.value && Object.keys(exifData.value).length === 0 && !isLoadingExif.value) {
    isLoadingExif.value = true;
    try {
      const response = await imageService.getExifData(props.image.id);
      exifData.value = response.exif || {};
    } catch (error) {
      console.error('Failed to load EXIF data:', error);
      exifData.value = { error: 'Failed to load EXIF data' };
    } finally {
      isLoadingExif.value = false;
    }
  }
};

// GPS formatting functions
const formatLatitude = (lat, ref) => {
  if (!lat) return '';
  const absLat = Math.abs(lat);
  const direction = ref || (lat >= 0 ? 'N' : 'S');
  return `${absLat.toFixed(6)}° ${direction}`;
};

const formatLongitude = (lon, ref) => {
  if (!lon) return '';
  const absLon = Math.abs(lon);
  const direction = ref || (lon >= 0 ? 'E' : 'W');
  return `${absLon.toFixed(6)}° ${direction}`;
};

const formatAltitude = (alt) => {
  if (alt === undefined) return '';
  const absAlt = Math.abs(alt);
  const direction = alt >= 0 ? 'above' : 'below';
  return `${absAlt.toFixed(1)}m ${direction} sea level`;
};

const formatExifValue = (key, value) => {
  // Don't format if value is an object (like GPS which is already filtered)
  if (typeof value === 'object') return JSON.stringify(value);
  return value;
};

const openGoogleMaps = () => {
  if (!hasGpsData.value) return;
  const lat = exifData.value.GPS.latitude;
  const lon = exifData.value.GPS.longitude;
  const url = `https://www.google.com/maps?q=${lat},${lon}`;
  window.open(url, '_blank');
};

const handleKeydown = (event) => {
  if (!props.image) return;

  switch (event.key) {
    case 'Escape':
      handleClose();
      break;
    case 'ArrowLeft':
      handlePrevious();
      break;
    case 'ArrowRight':
      handleNext();
      break;
  }
};

onMounted(() => {
  document.addEventListener('keydown', handleKeydown);
  // Prevent body scroll when modal is open
  document.body.style.overflow = 'hidden';
});

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown);
  document.body.style.overflow = '';
});
</script>

<style scoped>
.viewer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.95);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
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

.viewer-container {
  width: 95vw;
  height: 95vh;
  max-width: 1400px;
  background-color: #1a1a1a;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.8);
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    transform: translateY(30px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #333;
  background-color: #242424;
  border-radius: 12px 12px 0 0;
}

.viewer-title {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.filename {
  font-size: 1.1rem;
  font-weight: 600;
  color: #fff;
}

.dimensions {
  font-size: 0.85rem;
  color: #999;
}

.btn-close {
  background: none;
  border: none;
  color: #fff;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.btn-close:hover {
  background-color: rgba(255, 255, 255, 0.1);
  transform: scale(1.1);
}

.viewer-body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  overflow: auto;
  min-height: 0;
}

.full-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 4px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
}

.viewer-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #333;
  background-color: #242424;
  border-radius: 0 0 12px 12px;
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.metadata-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.meta-label {
  font-size: 0.75rem;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.meta-value {
  font-size: 0.95rem;
  color: #fff;
  font-weight: 500;
}

.meta-value.savings {
  color: #4CAF50;
  font-weight: 600;
}

.exif-section {
  margin: 1rem 0;
  padding: 1rem;
  background-color: #1a1a1a;
  border-radius: 6px;
  border: 1px solid #333;
}

.exif-title {
  font-size: 0.9rem;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.75rem;
  font-weight: 600;
}

.gps-section {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background-color: #242424;
  border-radius: 6px;
  border: 1px solid #3a3a3a;
}

.gps-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.gps-icon {
  font-size: 1.2rem;
}

.gps-title {
  font-size: 0.9rem;
  color: #fff;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.gps-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.gps-coords {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.coord-label {
  font-size: 0.8rem;
  color: #999;
  min-width: 80px;
  font-weight: 500;
}

.coord-value {
  font-size: 0.9rem;
  color: #4CAF50;
  font-weight: 600;
  font-family: 'Courier New', monospace;
}

.btn-maps {
  width: 100%;
  padding: 0.6rem 1rem;
  background: linear-gradient(135deg, #4CAF50, #45a049);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: all 0.2s;
}

.btn-maps:hover {
  background: linear-gradient(135deg, #45a049, #3d8b40);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
}

.btn-maps:active {
  transform: translateY(0);
}

.maps-icon {
  font-size: 1.1rem;
}

.exif-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
  max-height: 200px;
  overflow-y: auto;
}

.exif-item {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.exif-key {
  font-size: 0.75rem;
  color: #888;
  font-weight: 500;
}

.exif-value {
  font-size: 0.85rem;
  color: #ccc;
  word-break: break-word;
}

.no-exif {
  color: #666;
  font-size: 0.85rem;
  font-style: italic;
  text-align: center;
  padding: 1rem;
}

.viewer-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.btn-nav,
.btn-action {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  border: 1px solid #555;
  border-radius: 6px;
  background-color: #2a2a2a;
  color: #fff;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-nav:hover:not(:disabled),
.btn-action:hover {
  background-color: #3a3a3a;
  border-color: #4CAF50;
  transform: translateY(-2px);
}

.btn-nav:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.btn-action {
  background-color: #4CAF50;
  border-color: #4CAF50;
}

.btn-action:hover {
  background-color: #45a049;
  border-color: #45a049;
}

.btn-exif {
  background-color: #2196F3;
  border-color: #2196F3;
}

.btn-exif:hover {
  background-color: #1976D2;
  border-color: #1976D2;
}

.icon {
  font-size: 1.1rem;
}

/* Responsive */
@media (max-width: 768px) {
  .viewer-container {
    width: 100vw;
    height: 100vh;
    border-radius: 0;
  }

  .viewer-header {
    border-radius: 0;
  }

  .viewer-footer {
    border-radius: 0;
  }

  .metadata-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .viewer-actions {
    flex-wrap: wrap;
  }

  .btn-nav,
  .btn-action {
    flex: 1;
    min-width: 120px;
  }
}
</style>
