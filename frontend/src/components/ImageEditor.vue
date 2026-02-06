<template>
  <div v-if="image" class="editor-overlay" @click.self="handleCancel">
    <div class="editor-container">
      <div class="editor-header">
        <h2>Edit: {{ image.original_filename }}</h2>
        <div class="editor-actions">
          <button @click="handleCancel" class="btn-cancel">Cancel</button>
          <button @click="handleSave" class="btn-save">Save</button>
        </div>
      </div>
      <div ref="editorContainer" class="editor-body"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';
import ImageEditor from 'tui-image-editor';
import 'tui-image-editor/dist/tui-image-editor.css';

const props = defineProps({
  image: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['save', 'close']);

const editorContainer = ref(null);
let editorInstance = null;

const initializeEditor = () => {
  if (!editorContainer.value || !props.image) return;

  // Clean up existing instance
  if (editorInstance) {
    editorInstance.destroy();
  }

  // Initialize Toast UI Image Editor
  editorInstance = new ImageEditor(editorContainer.value, {
    includeUI: {
      loadImage: {
        path: props.image.image_url,
        name: props.image.original_filename
      },
      theme: {
        'common.bi.image': '',
        'common.bisize.width': '0px',
        'common.bisize.height': '0px',
        'common.backgroundImage': 'none',
        'common.backgroundColor': '#1e1e1e',
        'common.border': '0px'
      },
      menu: ['crop', 'flip', 'rotate', 'draw', 'shape', 'icon', 'text', 'mask', 'filter'],
      initMenu: 'filter',
      uiSize: {
        width: '100%',
        height: '100%'
      },
      menuBarPosition: 'bottom',
      usageStatistics: false
    },
    cssMaxWidth: 1200,
    cssMaxHeight: 800,
    selectionStyle: {
      cornerSize: 20,
      rotatingPointOffset: 70
    }
  });

  // Hide the load and download buttons
  const loadBtn = editorContainer.value.querySelector('.tie-btn-load');
  const downloadBtn = editorContainer.value.querySelector('.tie-btn-download');
  if (loadBtn) loadBtn.style.display = 'none';
  if (downloadBtn) downloadBtn.style.display = 'none';
};

const handleSave = async () => {
  if (!editorInstance) return;

  try {
    // Get the edited image as a data URL
    const dataURL = editorInstance.toDataURL();
    
    // Convert data URL to blob
    const response = await fetch(dataURL);
    const blob = await response.blob();
    
    // Emit save event with blob
    emit('save', blob);
  } catch (error) {
    console.error('Error saving image:', error);
    alert('Failed to save image. Please try again.');
  }
};

const handleCancel = () => {
  emit('close');
};

// Handle Escape key
const handleKeyDown = (e) => {
  if (e.key === 'Escape') {
    handleCancel();
  }
};

onMounted(() => {
  initializeEditor();
  window.addEventListener('keydown', handleKeyDown);
});

onBeforeUnmount(() => {
  if (editorInstance) {
    editorInstance.destroy();
  }
  window.removeEventListener('keydown', handleKeyDown);
});

// Reinitialize when image changes
watch(() => props.image, () => {
  if (props.image) {
    initializeEditor();
  }
});
</script>

<style scoped>
.editor-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.95);
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.editor-container {
  width: 100%;
  height: 100%;
  max-width: 1400px;
  max-height: 900px;
  background-color: #2c2c2c;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background-color: #1e1e1e;
  border-bottom: 1px solid #3a3a3a;
}

.editor-header h2 {
  margin: 0;
  color: #ffffff;
  font-size: 18px;
  font-weight: 500;
}

.editor-actions {
  display: flex;
  gap: 10px;
}

.editor-actions button {
  padding: 8px 20px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel {
  background-color: #3a3a3a;
  color: #ffffff;
}

.btn-cancel:hover {
  background-color: #4a4a4a;
}

.btn-save {
  background-color: #4CAF50;
  color: white;
}

.btn-save:hover {
  background-color: #45a049;
}

.editor-body {
  flex: 1;
  overflow: hidden;
  position: relative;
}

/* Override some Toast UI styles for better appearance */
:deep(.tui-image-editor-canvas-container) {
  background-color: #2c2c2c;
}

:deep(.tui-image-editor-menu) {
  background-color: #1e1e1e;
}

:deep(.tui-image-editor-item) {
  color: #ffffff;
}

:deep(.tui-image-editor-submenu) {
  background-color: #2c2c2c;
}
</style>
