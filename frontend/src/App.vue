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
        
        <!-- Settings button - always visible -->
        <div class="settings-menu-container">
          <button 
            @click.stop="showSettingsMenu = !showSettingsMenu" 
            class="btn-icon btn-header btn-settings"
            title="Settings"
          >
            <span class="icon">⚙️</span>
            <span class="tooltip">Settings</span>
          </button>
          
          <!-- Settings Dropdown Menu -->
          <div v-if="showSettingsMenu" class="settings-dropdown" @click.stop>
            <button class="settings-menu-item" @click="openAISettings">
              <span class="menu-icon">🤖</span>
              <div class="menu-text">
                <span class="menu-title">AI Settings</span>
                <span class="menu-desc">Configure OpenRouter & models</span>
              </div>
            </button>
            
            <button class="settings-menu-item" @click="openPresetSettings">
              <span class="menu-icon">⚙️</span>
              <div class="menu-text">
                <span class="menu-title">Preset Settings</span>
                <span class="menu-desc">Manage compression presets</span>
              </div>
            </button>
            
            <button class="settings-menu-item" @click="openAbout">
              <span class="menu-icon">ℹ️</span>
              <div class="menu-text">
                <span class="menu-title">About</span>
                <span class="menu-desc">App info & session details</span>
              </div>
            </button>
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
      :is-saving="isSavingEdit"
      @save="handleEditorSave"
      @close="handleEditorClose"
    />

    <!-- AI Settings Modal -->
    <div v-if="showAISettingsModal" class="modal-overlay" @click="showAISettingsModal = false">
      <div class="settings-modal" @click.stop>
        <div class="modal-header">
          <h2>🤖 AI Settings</h2>
          <button class="close-btn" @click="showAISettingsModal = false">✕</button>
        </div>
        
        <!-- OAuth Notification Banner -->
        <div v-if="oauthNotification" class="oauth-notification" :class="'notification-' + oauthNotification.type">
          <span class="notification-icon">{{ oauthNotification.type === 'success' ? '✓' : '✕' }}</span>
          <span class="notification-message">{{ oauthNotification.message }}</span>
          <button class="notification-close" @click="oauthNotification = null">✕</button>
        </div>
        
        <div class="settings-content">
          <!-- What is OpenRouter Info Box (only when not connected) -->
          <div v-if="!openRouterConnected" class="info-box openrouter-intro">
            <p><strong>What is OpenRouter?</strong></p>
            <p>OpenRouter provides access to multiple AI models including GPT-4, Claude, and more. You'll need an OpenRouter account with credits to use AI features.</p>
            <a href="https://openrouter.ai" target="_blank" rel="noopener noreferrer">
              Create an account at openrouter.ai →
            </a>
          </div>
          
          <!-- OpenRouter AI Connection Section -->
          <div class="settings-section">
            <h3>🤖 AI Features (OpenRouter)</h3>
            <p class="section-description">
              Connect your OpenRouter account to enable AI-powered image manipulation features.
            </p>
            
            <div class="openrouter-status">
              <div class="status-indicator" :class="{ 'connected': openRouterConnected }">
                <span class="status-dot"></span>
                <span class="status-text">
                  {{ openRouterConnected ? 'Connected' : 'Not Connected' }}
                </span>
              </div>
              
              <button 
                v-if="!openRouterConnected"
                class="btn-connect" 
                @click="handleConnectOpenRouter"
              >
                Connect OpenRouter Account
              </button>
              
              <button 
                v-else
                class="btn-disconnect" 
                @click="handleDisconnectOpenRouter"
              >
                Disconnect
              </button>
            </div>
            
            <!-- Show credits info when connected -->
            <div v-if="openRouterConnected && openRouterCredits !== null" class="credits-info">
              <p>
                <strong>Credits Remaining:</strong> ${{ openRouterCredits.toFixed(4) }}
              </p>
            </div>
          </div>

          <!-- LLM Model Selection Section -->
          <div class="settings-section">
            <h3>🧠 AI Model Selection</h3>
            <p class="section-description">
              Choose which AI model to use for image manipulation.
            </p>
            
            <div class="model-selector">
              <div class="current-model-display">
                <label>Current Model:</label>
                <div v-if="selectedModel" class="selected-model-info">
                  <span class="model-icon">{{ getSelectedModelData()?.icon }}</span>
                  <div class="model-text">
                    <span class="model-name">{{ getSelectedModelData()?.name }}</span>
                    <span class="model-cost">{{ getSelectedModelData()?.cost }}</span>
                  </div>
                </div>
                <div v-else class="no-model-selected">
                  <span class="placeholder-text">No model selected</span>
                </div>
              </div>
              
              <button 
                class="btn-select-model"
                :disabled="!openRouterConnected"
                @click="showModelSelector = true"
              >
                {{ openRouterConnected ? 'Choose Model' : 'Connect to Choose' }}
              </button>
            </div>
            
            <div class="info-box">
              <p><strong>About AI Models:</strong></p>
              <p>Different models have varying capabilities, speeds, and costs. Free models are great for testing, while premium models offer better quality and advanced features.</p>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn-modal btn-primary" @click="showAISettingsModal = false">
            Close
          </button>
        </div>
      </div>
    </div>

    <!-- Preset Settings Modal -->
    <div v-if="showPresetSettingsModal" class="modal-overlay" @click="showPresetSettingsModal = false">
      <div class="settings-modal" @click.stop>
        <div class="modal-header">
          <h2>⚙️ Preset Settings</h2>
          <button class="close-btn" @click="showPresetSettingsModal = false">✕</button>
        </div>
        
        <div class="settings-content">
          <div class="settings-section">
            <h3>📦 Compression Presets</h3>
            <p class="section-description">
              Manage your compression presets and their settings.
            </p>
            
            <div class="info-box">
              <p><strong>Coming Soon:</strong></p>
              <p>Preset management features will allow you to create, edit, and delete custom compression presets.</p>
            </div>
            
            <div class="presets-list">
              <div v-for="preset in presets" :key="preset.name" class="preset-item">
                <span class="preset-icon">{{ getPresetIcon(preset.name) }}</span>
                <div class="preset-info">
                  <span class="preset-name">{{ preset.display_name }}</span>
                  <span class="preset-desc">Quality: {{ preset.quality }}%, Max: {{ preset.max_width }}x{{ preset.max_height }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn-modal btn-primary" @click="showPresetSettingsModal = false">
            Close
          </button>
        </div>
      </div>
    </div>

    <!-- About Modal -->
    <div v-if="showAboutModal" class="modal-overlay" @click="showAboutModal = false">
      <div class="settings-modal about-modal" @click.stop>
        <div class="modal-header">
          <h2>ℹ️ About Image Tools</h2>
          <button class="close-btn" @click="showAboutModal = false">✕</button>
        </div>
        
        <div class="settings-content">
          <div class="settings-section">
            <div class="app-info-large">
              <div class="app-logo">🖼️</div>
              <h3>Image Tools</h3>
              <p class="version">Version 1.2.0</p>
              <p class="stage">Stage 4: AI Features</p>
            </div>
            
            <div class="info-box">
              <p><strong>Features:</strong></p>
              <ul>
                <li>Image compression with smart presets</li>
                <li>Background removal</li>
                <li>Format conversion</li>
                <li>Batch processing</li>
                <li>AI-powered image manipulation (OpenRouter)</li>
              </ul>
            </div>
            
            <div class="info-box">
              <p><strong>Session Information:</strong></p>
              <p><strong>Session ID:</strong> <code>{{ sessionId ? sessionId.substring(0, 16) + '...' : 'None' }}</code></p>
              <p><strong>Images in Session:</strong> {{ imageCount }}</p>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn-modal btn-primary" @click="showAboutModal = false">
            Close
          </button>
        </div>
      </div>
    </div>

    <!-- Model Selection Modal -->
    <div v-if="showModelSelector" class="modal-overlay" @click="showModelSelector = false">
      <div class="model-selector-modal" @click.stop>
        <div class="modal-header">
          <h2>🧠 Choose AI Model</h2>
          <button class="close-btn" @click="showModelSelector = false">✕</button>
        </div>
        
        <div class="model-selector-content">
          <p class="selector-description">
            Select the AI model you want to use for image manipulation. Each model has different capabilities, speeds, and costs.
          </p>
          
          <div class="model-grid">
            <div 
              v-for="model in availableModels" 
              :key="model.id"
              class="model-card"
              :class="{ 'selected': selectedModel === model.id }"
              @click="selectModel(model.id)"
            >
              <div class="model-card-header">
                <span class="model-icon-large" :style="{ color: model.color }">{{ model.icon }}</span>
                <div class="model-header-text">
                  <h3 class="model-card-name">{{ model.name }}</h3>
                  <p class="model-provider">{{ model.provider }}</p>
                </div>
                <div v-if="selectedModel === model.id" class="selected-checkmark">✓</div>
              </div>
              
              <p class="model-description">{{ model.description }}</p>
              
              <div class="model-tags">
                <span 
                  v-for="tag in model.tags" 
                  :key="tag" 
                  class="model-tag"
                  :class="{ 'tag-free': tag === 'Free', 'tag-recommended': tag === 'Recommended' }"
                >
                  {{ tag }}
                </span>
              </div>
              
              <div class="model-footer">
                <div class="model-pricing">
                  <span class="pricing-label">Cost:</span>
                  <span class="pricing-value">{{ model.cost }}</span>
                </div>
                <div class="model-id">{{ model.id }}</div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn-modal btn-secondary" @click="showModelSelector = false">
            Cancel
          </button>
          <button 
            class="btn-modal btn-primary" 
            @click="showModelSelector = false"
            :disabled="!selectedModel"
          >
            Confirm Selection
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';
import { useSessionStore } from './stores/sessionStore';
import { useImageStore } from './stores/imageStore';
import { storeToRefs } from 'pinia';
import { imageService } from './services/api';
import { openRouterService, generateCodeVerifier, generateCodeChallenge } from './services/openRouterService';
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
const isSavingEdit = ref(false);

// Settings menu state
const showSettingsMenu = ref(false);
const showAISettingsModal = ref(false);
const showPresetSettingsModal = ref(false);
const showAboutModal = ref(false);

// OpenRouter OAuth state
const openRouterConnected = ref(false);
const openRouterCredits = ref(null);
const oauthNotification = ref(null); // { type: 'success' | 'error', message: string }
const selectedModel = ref('');
const showModelSelector = ref(false);

// AI Model data with details, pricing, and capabilities
const availableModels = [
  {
    id: 'google/gemini-2.0-flash-exp:free',
    name: 'Gemini 2.0 Flash',
    provider: 'Google',
    description: 'Fast, efficient model with vision capabilities. Perfect for most image tasks.',
    cost: 'Free',
    costPerMillion: '$0.00',
    tags: ['Free', 'Fast', 'Vision', 'Recommended'],
    icon: '⚡',
    color: '#4285f4'
  },
  {
    id: 'openai/gpt-4-turbo',
    name: 'GPT-4 Turbo',
    provider: 'OpenAI',
    description: 'High-quality multimodal model with excellent vision understanding and reasoning.',
    cost: '$10 / 1M tokens',
    costPerMillion: '$10.00',
    tags: ['Vision', 'High Quality', 'Popular'],
    icon: '🤖',
    color: '#10a37f'
  },
  {
    id: 'anthropic/claude-3.5-sonnet',
    name: 'Claude 3.5 Sonnet',
    provider: 'Anthropic',
    description: 'Excellent reasoning and vision capabilities with nuanced understanding.',
    cost: '$3 / 1M tokens',
    costPerMillion: '$3.00',
    tags: ['Vision', 'Reasoning', 'Recommended'],
    icon: '🧠',
    color: '#cc785c'
  },
  {
    id: 'anthropic/claude-3-opus',
    name: 'Claude 3 Opus',
    provider: 'Anthropic',
    description: 'Top-tier model with exceptional vision analysis and creative capabilities.',
    cost: '$15 / 1M tokens',
    costPerMillion: '$15.00',
    tags: ['Vision', 'Premium', 'Creative'],
    icon: '💎',
    color: '#cc785c'
  },
  {
    id: 'meta-llama/llama-3.1-70b-instruct',
    name: 'Llama 3.1 70B',
    provider: 'Meta',
    description: 'Open-source model with strong general capabilities and efficiency.',
    cost: '$0.50 / 1M tokens',
    costPerMillion: '$0.50',
    tags: ['Open Source', 'Efficient', 'Cost-effective'],
    icon: '🦙',
    color: '#0668e1'
  },
  {
    id: 'openai/gpt-4o',
    name: 'GPT-4o',
    provider: 'OpenAI',
    description: 'Latest OpenAI model optimized for speed and multimodal tasks.',
    cost: '$5 / 1M tokens',
    costPerMillion: '$5.00',
    tags: ['Vision', 'Fast', 'Latest'],
    icon: '🚀',
    color: '#10a37f'
  },
  {
    id: 'anthropic/claude-3-haiku',
    name: 'Claude 3 Haiku',
    provider: 'Anthropic',
    description: 'Fast and cost-effective model for simpler vision and text tasks.',
    cost: '$0.25 / 1M tokens',
    costPerMillion: '$0.25',
    tags: ['Fast', 'Budget', 'Vision'],
    icon: '⚡',
    color: '#cc785c'
  },
  {
    id: 'google/gemini-pro-vision',
    name: 'Gemini Pro Vision',
    provider: 'Google',
    description: 'Powerful vision model with multimodal understanding capabilities.',
    cost: '$0.125 / 1M tokens',
    costPerMillion: '$0.125',
    tags: ['Vision', 'Affordable', 'Google'],
    icon: '👁️',
    color: '#4285f4'
  }
];

const getSelectedModelData = () => {
  return availableModels.find(m => m.id === selectedModel.value);
};

const initializeApp = async () => {
  isLoading.value = true;
  error.value = null;

  try {
    await sessionStore.initializeSession();
    await Promise.all([
      imageStore.loadSessionImages(),
      imageStore.loadPresets()
    ]);
    
    // Set session ID in OpenRouter service
    if (sessionId.value) {
      openRouterService.setSessionId(sessionId.value);
    }
    
    // Check if we're returning from OAuth callback
    handleOAuthCallback();
    
    // Load OpenRouter connection status
    await loadOpenRouterStatus();
    
    // Load saved model selection from localStorage
    const savedModel = localStorage.getItem('openrouter_selected_model');
    if (savedModel) {
      selectedModel.value = savedModel;
    }
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
  console.log('[Editor Save] Starting save process...', {
    hasEditingImage: !!editingImage.value,
    blobSize: blob?.size,
    blobType: blob?.type
  });

  if (!editingImage.value) {
    console.error('[Editor Save] No image being edited');
    alert('No image to save');
    return;
  }

  if (!blob || blob.size === 0) {
    console.error('[Editor Save] Invalid blob received');
    alert('Empty image data received. Please try again.');
    return;
  }

  isSavingEdit.value = true;

  try {
    console.log('[Editor Save] Preparing FormData...', {
      imageId: editingImage.value.id,
      filename: editingImage.value.original_filename,
      blobSize: blob.size,
      blobType: blob.type
    });

    const formData = new FormData();
    formData.append('file', blob, editingImage.value.original_filename);

    console.log('[Editor Save] Calling API...');
    const startTime = Date.now();

    // Call backend API to save edited image
    const response = await imageService.saveEditedImage(editingImage.value.id, formData);
    
    const elapsed = Date.now() - startTime;
    console.log(`[Editor Save] API response received in ${elapsed}ms:`, response);
    
    // Update the specific image in the store
    console.log('[Editor Save] Updating image in store...');
    await imageStore.updateImage(editingImage.value.id, response);
    
    // Close the editor
    console.log('[Editor Save] Closing editor...');
    editingImage.value = null;
    
    console.log('[Editor Save] Save complete!');
  } catch (error) {
    console.error('[Editor Save] Failed:', error);
    console.error('[Editor Save] Error details:', {
      message: error.message,
      response: error.response?.data,
      status: error.response?.status,
      statusText: error.response?.statusText
    });
    
    let errorMessage = 'Failed to save edited image. ';
    if (error.response?.data?.detail) {
      errorMessage += error.response.data.detail;
    } else if (error.message) {
      errorMessage += error.message;
    }
    
    alert(errorMessage);
  } finally {
    isSavingEdit.value = false;
  }
};

const handleEditorClose = () => {
  editingImage.value = null;
};

// Settings menu handlers
const openAISettings = () => {
  showSettingsMenu.value = false;
  showAISettingsModal.value = true;
};

const openPresetSettings = () => {
  showSettingsMenu.value = false;
  showPresetSettingsModal.value = true;
};

const openAbout = () => {
  showSettingsMenu.value = false;
  showAboutModal.value = true;
};

// OpenRouter OAuth handlers
const loadOpenRouterStatus = async () => {
  try {
    const status = await openRouterService.getStatus();
    openRouterConnected.value = status.connected;
    openRouterCredits.value = status.credits_remaining;
  } catch (error) {
    console.error('Failed to load OpenRouter status:', error);
  }
};

const handleConnectOpenRouter = async () => {
  try {
    // 1. Generate PKCE code_verifier and code_challenge
    const codeVerifier = generateCodeVerifier();
    const codeChallenge = await generateCodeChallenge(codeVerifier);
    
    // 2. Store code_verifier in sessionStorage for callback
    sessionStorage.setItem('pkce_code_verifier', codeVerifier);
    
    // 3. Get authorization URL from backend
    const { auth_url } = await openRouterService.getAuthorizationUrl(codeChallenge);
    
    // 4. Redirect to OpenRouter
    window.location.href = auth_url;
    
  } catch (error) {
    console.error('Failed to start OAuth flow:', error);
    alert('Failed to connect to OpenRouter: ' + error.message);
  }
};

const handleOAuthCallback = async () => {
  // Check if we have a 'code' parameter in URL
  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get('code');
  
  if (!code) return; // Not a callback
  
  try {
    // Retrieve stored code_verifier
    const codeVerifier = sessionStorage.getItem('pkce_code_verifier');
    if (!codeVerifier) {
      throw new Error('Code verifier not found');
    }
    
    // Exchange code for API key (proxied through backend)
    const result = await openRouterService.exchangeCode(code, codeVerifier);
    
    if (result.success) {
      // Update connection status
      openRouterConnected.value = true;
      openRouterCredits.value = result.credits_remaining;
      
      // Clean up
      sessionStorage.removeItem('pkce_code_verifier');
      
      // Remove code from URL
      window.history.replaceState({}, document.title, window.location.pathname);
      
      // Show success notification in modal
      const creditsText = result.credits_remaining !== null 
        ? `$${result.credits_remaining.toFixed(4)}` 
        : 'N/A';
      oauthNotification.value = {
        type: 'success',
        message: `Successfully connected to OpenRouter! Credits: ${creditsText}`
      };
      
      // Open AI settings modal to show connection
      showAISettingsModal.value = true;
      
      // Auto-dismiss notification after 5 seconds
      setTimeout(() => {
        oauthNotification.value = null;
      }, 5000);
    } else {
      throw new Error('OAuth exchange failed');
    }
    
  } catch (error) {
    console.error('OAuth callback error:', error);
    
    // Show error notification in modal
    oauthNotification.value = {
      type: 'error',
      message: `Failed to connect: ${error.message}`
    };
    
    // Open AI settings modal to show error
    showAISettingsModal.value = true;
    
    // Clean up
    sessionStorage.removeItem('pkce_code_verifier');
    window.history.replaceState({}, document.title, window.location.pathname);
    
    // Auto-dismiss notification after 8 seconds (longer for errors)
    setTimeout(() => {
      oauthNotification.value = null;
    }, 8000);
  }
};

const handleDisconnectOpenRouter = async () => {
  if (!confirm('Disconnect from OpenRouter? You will need to reconnect to use AI features.')) {
    return;
  }
  
  try {
    const result = await openRouterService.revoke();
    if (result.success) {
      openRouterConnected.value = false;
      openRouterCredits.value = null;
      
      // Show success notification
      oauthNotification.value = {
        type: 'success',
        message: 'Disconnected from OpenRouter'
      };
      
      // Auto-dismiss notification after 3 seconds
      setTimeout(() => {
        oauthNotification.value = null;
      }, 3000);
    }
  } catch (error) {
    console.error('Failed to disconnect:', error);
    
    // Show error notification
    oauthNotification.value = {
      type: 'error',
      message: `Failed to disconnect: ${error.message}`
    };
    
    // Auto-dismiss notification after 5 seconds
    setTimeout(() => {
      oauthNotification.value = null;
    }, 5000);
  }
};

// Toolbar actions
const selectAll = () => {
  imageStore.selectAll();
};

const clearSelection = () => {
  imageStore.clearSelection();
};

// Model selection handler
const selectModel = (modelId) => {
  selectedModel.value = modelId;
  console.log('Model selected:', modelId);
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
  if (showSettingsMenu.value) {
    showSettingsMenu.value = false;
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
  // Handle Escape key for modals and menus (highest priority)
  if (event.key === 'Escape') {
    // Close modals in order of priority
    if (showModelSelectorModal.value) {
      showModelSelectorModal.value = false;
      return;
    }
    if (showAISettingsModal.value) {
      showAISettingsModal.value = false;
      return;
    }
    if (showPresetSettingsModal.value) {
      showPresetSettingsModal.value = false;
      return;
    }
    if (showAboutModal.value) {
      showAboutModal.value = false;
      return;
    }
    if (showSettingsMenu.value) {
      showSettingsMenu.value = false;
      return;
    }
    if (showClearAllConfirm.value) {
      showClearAllConfirm.value = false;
      return;
    }
    // If no modals open and there are selected images, clear selection
    if (selectedCount.value > 0) {
      clearSelection();
      return;
    }
  }

  // Don't trigger other shortcuts if viewer is open or in an input field
  if (viewerImage.value || event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
    return;
  }

  // Ctrl/Cmd + A: Select all images
  if ((event.ctrlKey || event.metaKey) && event.key === 'a' && imageCount.value > 0) {
    event.preventDefault();
    selectAll();
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

// Watch for model selection changes and persist to localStorage
watch(selectedModel, (newModel) => {
  if (newModel) {
    localStorage.setItem('openrouter_selected_model', newModel);
    console.log('Selected model saved:', newModel);
  }
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
  overflow: visible;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1rem;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: padding 0.3s ease;
  overflow: visible;
  position: relative;
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
  overflow: visible;
  position: relative;
}

.header-left {
  text-align: left;
  flex: 1;
  overflow: visible;
  position: relative;
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
  z-index: 999999;
  top: 125%;
  left: 0;
  transform: none;
  white-space: nowrap;
  font-size: 0.85rem;
  font-weight: normal;
  transition: opacity 0.3s, visibility 0.3s;
  pointer-events: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

.has-tooltip .tooltip-text::after {
  content: "";
  position: absolute;
  bottom: 100%;
  left: 20px;
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
  z-index: 999999;
  top: 100%;
  left: 0;
  margin-top: 0.5rem;
  white-space: nowrap;
  font-size: 0.85rem;
  font-weight: normal;
  transition: opacity 0.3s, visibility 0.3s;
  pointer-events: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

.has-tooltip .tooltip-text::after {
  content: "";
  position: absolute;
  bottom: 100%;
  left: 20px;
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
  overflow: visible;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  overflow: visible;
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
  padding-top: 2rem;
  overflow: visible;
}

.content-with-images {
  display: flex;
  gap: 1.5rem;
  align-items: flex-start;
  overflow: visible;
}

.main-content {
  flex: 1;
  min-width: 0;
  width: 100%;
  overflow: visible;
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

.btn-modal.btn-primary {
  background-color: #4CAF50;
  color: white;
}

.btn-modal.btn-primary:hover:not(:disabled) {
  background-color: #45a049;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(76, 175, 80, 0.3);
}

/* Settings Modal */
.btn-settings {
  margin-left: auto;
}

/* Settings Menu Dropdown */
.settings-menu-container {
  position: relative;
  margin-left: auto;
}

.settings-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  min-width: 280px;
  z-index: 1000;
  animation: slideDown 0.2s ease-out;
}

.settings-menu-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background: none;
  border: none;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background-color 0.2s ease;
  text-align: left;
}

.settings-menu-item:first-child {
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
}

.settings-menu-item:last-child {
  border-bottom: none;
  border-bottom-left-radius: 8px;
  border-bottom-right-radius: 8px;
}

.settings-menu-item:hover {
  background-color: #f8f9fa;
}

.menu-icon {
  font-size: 1.75rem;
  flex-shrink: 0;
}

.menu-text {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.menu-title {
  font-weight: 600;
  color: #333;
  font-size: 0.95rem;
}

.menu-desc {
  font-size: 0.8rem;
  color: #666;
}

.settings-modal {
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  max-width: 700px;
  width: 90%;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  animation: slideUp 0.3s ease;
}

.settings-modal .modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.settings-modal .close-btn {
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

.settings-modal .close-btn:hover {
  background-color: #f5f5f5;
  color: #333;
}

.settings-content {
  padding: 1.5rem;
  overflow-y: auto;
  flex: 1;
}

.settings-section {
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid #e0e0e0;
}

.settings-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.settings-section h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
  color: #333;
}

.section-description {
  margin: 0 0 1.5rem 0;
  color: #666;
  font-size: 0.95rem;
  line-height: 1.5;
}

.openrouter-status {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background-color: #fff3e0;
  border: 1px solid #ff9800;
  border-radius: 6px;
}

.status-indicator.connected {
  background-color: #e8f5e9;
  border-color: #4CAF50;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: #ff9800;
}

.status-indicator.connected .status-dot {
  background-color: #4CAF50;
}

.status-text {
  font-weight: 600;
  color: #e65100;
  font-size: 0.9rem;
}

.status-indicator.connected .status-text {
  color: #2e7d32;
}

.btn-connect {
  padding: 0.75rem 1.5rem;
  background-color: #2196F3;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.btn-connect:hover {
  background-color: #1976D2;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(33, 150, 243, 0.3);
}

.btn-connect:disabled {
  background-color: #e0e0e0;
  color: #999;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.btn-disconnect {
  padding: 0.75rem 1.5rem;
  background-color: #f44336;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.btn-disconnect:hover {
  background-color: #d32f2f;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(244, 67, 54, 0.3);
}

.credits-info {
  background-color: #e8f5e9;
  border-left: 3px solid #4CAF50;
  padding: 1rem;
  border-radius: 4px;
  margin-top: 1rem;
}

.credits-info p {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  color: #2e7d32;
  line-height: 1.5;
}

.credits-info p:last-child {
  margin-bottom: 0;
}

.credits-info strong {
  color: #1b5e20;
}

.info-box {
  background-color: #f5f5f5;
  border-left: 3px solid #2196F3;
  padding: 1rem;
  border-radius: 4px;
  margin-top: 1rem;
}

.openrouter-intro {
  margin-top: 0;
  margin-bottom: 1.5rem;
  background-color: #e3f2fd;
  border-left: 4px solid #2196F3;
  padding: 1.25rem;
}

/* OAuth Notification Banner */
.oauth-notification {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  margin: 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  animation: slideDown 0.3s ease-out;
}

.notification-success {
  background-color: #e8f5e9;
  color: #2e7d32;
  border-left: 4px solid #4CAF50;
}

.notification-error {
  background-color: #ffebee;
  color: #c62828;
  border-left: 4px solid #f44336;
}

.notification-icon {
  font-size: 1.2rem;
  font-weight: bold;
  flex-shrink: 0;
}

.notification-message {
  flex: 1;
  font-weight: 500;
  font-size: 0.95rem;
}

.notification-close {
  background: none;
  border: none;
  font-size: 1.2rem;
  color: inherit;
  opacity: 0.7;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.notification-close:hover {
  opacity: 1;
  background-color: rgba(0, 0, 0, 0.1);
}

/* Presets List */
.presets-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1rem;
}

.preset-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background-color: #f8f9fa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}

.preset-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.preset-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
}

.preset-name {
  font-weight: 600;
  color: #333;
  font-size: 0.95rem;
}

.preset-desc {
  font-size: 0.85rem;
  color: #666;
}

/* About Modal Styles */
.about-modal {
  max-width: 600px;
}

.app-info-large {
  text-align: center;
  padding: 2rem 1rem 1rem 1rem;
}

.app-logo {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.app-info-large h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.75rem;
  color: #333;
}

.app-info-large .version {
  margin: 0 0 0.25rem 0;
  font-size: 1rem;
  color: #666;
  font-weight: 600;
}

.app-info-large .stage {
  margin: 0;
  font-size: 0.9rem;
  color: #999;
}

.about-modal code {
  background-color: #f5f5f5;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  color: #333;
}

.info-box p {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  color: #555;
  line-height: 1.5;
}

.info-box p:last-child {
  margin-bottom: 0;
}

.info-box strong {
  color: #333;
}

.info-box ul {
  margin: 0.5rem 0 0 0;
  padding-left: 1.5rem;
}

.info-box li {
  margin: 0.5rem 0;
  font-size: 0.9rem;
  color: #555;
  line-height: 1.5;
}

.info-box a {
  color: #2196F3;
  text-decoration: none;
  font-weight: 600;
}

.info-box a:hover {
  text-decoration: underline;
}

.model-selector {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1rem;
}

.current-model-display {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.current-model-display label {
  font-weight: 600;
  color: #333;
  font-size: 0.9rem;
}

.selected-model-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background-color: #f8f9fa;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
}

.model-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.model-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.model-name {
  font-weight: 600;
  color: #333;
  font-size: 1rem;
}

.model-cost {
  font-size: 0.85rem;
  color: #666;
}

.no-model-selected {
  padding: 1rem;
  background-color: #f8f9fa;
  border: 2px dashed #ddd;
  border-radius: 8px;
  text-align: center;
}

.placeholder-text {
  color: #999;
  font-style: italic;
}

.btn-select-model {
  padding: 0.75rem 1.5rem;
  background-color: #2196F3;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-select-model:hover:not(:disabled) {
  background-color: #1976D2;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(33, 150, 243, 0.3);
}

.btn-select-model:disabled {
  background-color: #e0e0e0;
  color: #999;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* Model Selector Modal */
.model-selector-modal {
  background-color: white;
  border-radius: 12px;
  width: 90%;
  max-width: 1200px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  animation: modalSlideIn 0.3s ease-out;
}

.model-selector-content {
  padding: 1.5rem;
  overflow-y: auto;
  flex: 1;
}

.selector-description {
  margin: 0 0 1.5rem 0;
  color: #666;
  font-size: 0.95rem;
  line-height: 1.5;
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 1.25rem;
}

.model-card {
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  padding: 1.25rem;
  cursor: pointer;
  transition: all 0.2s ease;
  background-color: white;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  position: relative;
}

.model-card:hover {
  border-color: #2196F3;
  box-shadow: 0 4px 12px rgba(33, 150, 243, 0.15);
  transform: translateY(-2px);
}

.model-card.selected {
  border-color: #4CAF50;
  background-color: #f1f8f4;
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.2);
}

.model-card-header {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  position: relative;
}

.model-icon-large {
  font-size: 2.5rem;
  flex-shrink: 0;
}

.model-header-text {
  flex: 1;
}

.model-card-name {
  margin: 0 0 0.25rem 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: #333;
}

.model-provider {
  margin: 0;
  font-size: 0.85rem;
  color: #666;
  font-weight: 500;
}

.selected-checkmark {
  position: absolute;
  top: 0;
  right: 0;
  width: 28px;
  height: 28px;
  background-color: #4CAF50;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 1rem;
}

.model-description {
  margin: 0;
  font-size: 0.9rem;
  color: #555;
  line-height: 1.5;
  flex: 1;
}

.model-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.model-tag {
  padding: 0.35rem 0.75rem;
  background-color: #e3f2fd;
  color: #1976D2;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.model-tag.tag-free {
  background-color: #e8f5e9;
  color: #2e7d32;
}

.model-tag.tag-recommended {
  background-color: #fff3e0;
  color: #ef6c00;
}

.model-footer {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid #e0e0e0;
}

.model-pricing {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pricing-label {
  font-size: 0.85rem;
  color: #666;
  font-weight: 500;
}

.pricing-value {
  font-size: 0.95rem;
  font-weight: 700;
  color: #333;
}

.model-id {
  font-size: 0.75rem;
  color: #999;
  font-family: 'Courier New', monospace;
  word-break: break-all;
}

/* Modal footer buttons */
.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #e0e0e0;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-modal {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.95rem;
}

.btn-modal.btn-primary {
  background-color: #2196F3;
  color: white;
}

.btn-modal.btn-primary:hover:not(:disabled) {
  background-color: #1976D2;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.3);
}

.btn-modal.btn-primary:disabled {
  background-color: #e0e0e0;
  color: #999;
  cursor: not-allowed;
}

.btn-modal.btn-secondary {
  background-color: #f5f5f5;
  color: #333;
}

.btn-modal.btn-secondary:hover {
  background-color: #e0e0e0;
}

.model-selector label {
  font-weight: 600;
  color: #333;
  min-width: 60px;
}

.model-dropdown {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 1rem;
  background-color: white;
  cursor: pointer;
  transition: border-color 0.2s ease;
}

.model-dropdown:focus {
  outline: none;
  border-color: #2196F3;
}

.model-dropdown:disabled {
  background-color: #f5f5f5;
  color: #999;
  cursor: not-allowed;
}

.app-info {
  padding: 1rem;
  background-color: #f9f9f9;
  border-radius: 6px;
}

.app-info p {
  margin: 0.5rem 0;
  font-size: 0.9rem;
  color: #555;
}

.app-info p:first-child {
  margin-top: 0;
}

.app-info p:last-child {
  margin-bottom: 0;
}

/* Responsive Design - Mobile Optimization */
@media (max-width: 768px) {
  /* Header adjustments */
  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .settings-menu-container {
    position: absolute;
    top: 1rem;
    right: 1rem;
    margin-left: 0;
  }

  .header-right {
    width: 100%;
    margin-left: 0;
  }

  .toolbar-actions {
    flex-wrap: wrap;
  }

  /* Settings dropdown positioning for mobile */
  .settings-dropdown {
    right: 0;
    left: auto;
    min-width: 260px;
  }

  /* Modal adjustments */
  .settings-modal,
  .modal-content {
    width: 95%;
    max-width: 100%;
    max-height: 90vh;
    margin: 1rem;
  }

  /* Model grid - single column on mobile */
  .model-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .model-card {
    padding: 1rem;
  }

  /* Buttons and text sizing */
  .btn-icon {
    padding: 0.6rem 1rem;
    font-size: 0.9rem;
  }

  .settings-modal h2 {
    font-size: 1.3rem;
  }

  .modal-header h2 {
    font-size: 1.25rem;
  }

  /* Image grid - 2 columns on mobile */
  .image-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 0.75rem;
  }
}

@media (max-width: 480px) {
  /* Extra small devices */
  .app-header h1 {
    font-size: 1.8rem;
  }

  .app-header.compact h1 {
    font-size: 1.2rem;
  }

  /* Even smaller modals */
  .settings-modal,
  .modal-content {
    width: 100%;
    max-height: 95vh;
    margin: 0.5rem;
    border-radius: 8px;
  }

  /* Settings dropdown full width on tiny screens */
  .settings-dropdown {
    min-width: 240px;
  }

  .settings-menu-item {
    padding: 0.75rem 1rem;
  }

  .menu-icon {
    font-size: 1.5rem;
  }

  /* Model cards more compact */
  .model-icon-large {
    font-size: 2rem;
  }

  .model-card-name {
    font-size: 1rem;
  }

  /* Image grid - single column on very small screens */
  .image-grid {
    grid-template-columns: 1fr;
  }
}

/* Tablet landscape */
@media (min-width: 769px) and (max-width: 1024px) {
  .model-grid {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  }

  .settings-modal {
    max-width: 600px;
  }
}
</style>
