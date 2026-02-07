<template>
  <div id="app">
    <header class="app-header" :class="{ 'compact': imageCount > 0 }">
      <div class="header-content">
        <div class="header-left">
          <div class="title-container">
            <h1 class="has-tooltip">
              🖼️ Image Tools
              <span class="tooltip-text">Image Tools v1.0 | Session: {{ sessionId ? sessionId.substring(0, 8) + '...' : 'None' }}</span>
            </h1>
            
            <button 
              @click="openAbout" 
              class="btn-info-icon"
              title="About & Session Info"
            >
              ℹ️
            </button>
            
            <!-- Username display -->
            <div v-if="username" class="username-display">
              <span class="user-icon">👤</span>
              <span class="username-text">{{ username }}</span>
            </div>
          </div>
          
          <p v-if="imageCount === 0" class="subtitle">Compress and manage your images</p>
          
          <!-- Image count and selection info -->
          <div v-if="imageCount > 0" class="image-stats">
            <span class="image-count">
              {{ imageCount }} / {{ appConfig.max_images_per_session }} image{{ imageCount !== 1 ? 's' : '' }}
              <span class="expiry-info" :title="`Images expire after ${appConfig.session_expiry_days} days`">
                (expires in {{ appConfig.session_expiry_days }} days)
              </span>
            </span>
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
            
            <button class="settings-menu-item" @click="openImageCardSettings">
              <span class="menu-icon">🖼️</span>
              <div class="menu-text">
                <span class="menu-title">Image Card Settings</span>
                <span class="menu-desc">Customize card size & layout</span>
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
                  v-for="image in imageStore.images"
                  :key="image.id"
                  :image="image"
                  :presets="presets"
                  :sessionId="sessionId"
                  :selectedModel="selectedModel"
                  :isOpenRouterConnected="openRouterConnected"
                  :expiryDays="appConfig.session_expiry_days"
                  :cardSize="imageCardSize"
                  @image-click="handleImageClick"
                  @edit-click="handleEditClick"
                  @switchModel="handleSwitchModel"
                  @showModelDetails="handleShowModelDetails"
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
        <button class="modal-close-btn" @click="showAISettingsModal = false">✕</button>
        
        <div class="modal-header">
          <h2>🤖 AI Settings</h2>
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
              Choose which AI model to use for image manipulation. Click the card to change models.
            </p>
            
            <!-- Model Card Display (Clickable) -->
            <div 
              v-if="selectedModel && getSelectedModelData()"
              class="selected-model-card clickable"
              :class="{ 'disabled': !openRouterConnected }"
              @click="openRouterConnected && openModelSelector()"
            >
              <div class="model-card-header">
                <span class="model-icon-large" :style="{ color: getSelectedModelData()?.color }">
                  {{ getSelectedModelData()?.icon }}
                </span>
                <div class="model-header-text">
                  <h3 class="model-card-name">{{ getSelectedModelData()?.name }}</h3>
                  <p class="model-provider">{{ getSelectedModelData()?.provider }}</p>
                </div>
                <span class="click-hint">✏️</span>
              </div>
              
              <div class="model-description-container">
                <p 
                  class="model-description" 
                  :class="{ 'expanded': expandedDescriptions.has('ai-settings-selected') }"
                >
                  {{ expandedDescriptions.has('ai-settings-selected') ? getSelectedModelData()?.description : getSelectedModelData()?.descriptionShort }}
                </p>
                <button 
                  v-if="getSelectedModelData()?.description?.length > 200"
                  @click.stop="toggleDescription('ai-settings-selected')"
                  class="btn-toggle-description"
                >
                  {{ expandedDescriptions.has('ai-settings-selected') ? 'Show less' : 'Show more' }}
                </button>
              </div>
              
              <div class="model-tags">
                <span 
                  v-for="tag in getSelectedModelData()?.tags" 
                  :key="tag" 
                  class="model-tag"
                  :class="{ 
                    'tag-free': tag === 'Free', 
                    'tag-recommended': tag === 'Recommended',
                    'tag-image-editing': tag === 'Image Editing'
                  }"
                >
                  {{ tag }}
                </span>
              </div>
              
              <div class="model-specs">
                <div class="spec-item" v-if="getSelectedModelData()?.contextWindow">
                  <span class="spec-label">Context:</span>
                  <span class="spec-value">{{ formatContextWindow(getSelectedModelData()?.contextWindow) }}</span>
                </div>
                <div class="spec-item" v-if="getSelectedModelData()?.maxTokens">
                  <span class="spec-label">Max Output:</span>
                  <span class="spec-value">{{ formatTokens(getSelectedModelData()?.maxTokens) }}</span>
                </div>
              </div>
              
              <div class="model-footer">
                <div class="model-pricing">
                  <span class="pricing-label">Cost:</span>
                  <span class="pricing-value">{{ getSelectedModelData()?.cost }}</span>
                </div>
                <div class="model-id">{{ getSelectedModelData()?.id }}</div>
              </div>
            </div>
            
            <!-- No Model Selected Placeholder -->
            <div 
              v-else
              class="selected-model-card clickable placeholder"
              :class="{ 'disabled': !openRouterConnected }"
              @click="openRouterConnected && openModelSelector()"
            >
              <div class="placeholder-content">
                <span class="placeholder-icon">🤖</span>
                <h3 class="placeholder-title">No Model Selected</h3>
                <p class="placeholder-text">
                  {{ openRouterConnected ? 'Click here to choose an AI model' : 'Connect to OpenRouter to choose a model' }}
                </p>
              </div>
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
        <button class="modal-close-btn" @click="showPresetSettingsModal = false">✕</button>
        
        <div class="modal-header">
          <h2>⚙️ Preset Settings</h2>
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
        <button class="modal-close-btn" @click="showAboutModal = false">✕</button>
        
        <div class="modal-header">
          <h2>ℹ️ About Image Tools</h2>
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
              <p v-if="username"><strong>User:</strong> <code>{{ username }}</code></p>
              <p><strong>Session ID:</strong> <code>{{ sessionId ? sessionId.substring(0, 16) + '...' : 'None' }}</code></p>
              <p><strong>Images in Session:</strong> {{ imageCount }} / {{ appConfig.max_images_per_session }}</p>
            </div>
            
            <div class="info-box info-box-highlight">
              <p><strong>⚠️ Important Information:</strong></p>
              <ul>
                <li><strong>Temporary Storage:</strong> All uploaded images are temporary and will be automatically removed after <strong>{{ appConfig.session_expiry_days }} days</strong></li>
                <li><strong>Session Limit:</strong> You can upload a maximum of <strong>{{ appConfig.max_images_per_session }} images</strong> per session</li>
                <li><strong>File Size Limit:</strong> Maximum upload size is <strong>{{ appConfig.max_upload_size_mb }} MB</strong> per image</li>
              </ul>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn-modal btn-secondary" @click="openMobileQRModal" style="margin-right: auto;">
            📱 Mobile App Link
          </button>
          <button class="btn-modal btn-secondary" @click="openAddonModal" style="margin-left: 0.5rem;">
            🧩 Browser Addon
          </button>
          <button class="btn-modal btn-primary" @click="showAboutModal = false">
            Close
          </button>
        </div>
      </div>
    </div>

    <!-- Mobile QR Code Modal -->
    <div v-if="showMobileQRModal" class="modal-overlay" @click="showMobileQRModal = false">
      <div class="settings-modal" @click.stop>
        <button class="modal-close-btn" @click="showMobileQRModal = false">✕</button>
        
        <div class="modal-header">
          <h2>📱 Mobile App Pairing</h2>
        </div>
        
        <div class="settings-content">
          <!-- Success State: Device Paired -->
          <div v-if="qrCodePaired" class="pairing-success-container">
            <div class="success-icon">✓</div>
            <h3 style="color: #10b981; margin: 20px 0 10px;">Device Paired Successfully!</h3>
            <p style="color: #666; margin-bottom: 30px;">
              Your mobile device is now connected. You can share images from your gallery.
            </p>
            
            <!-- Circular countdown -->
            <div class="circular-countdown">
              <svg class="countdown-svg" width="120" height="120">
                <circle
                  class="countdown-circle-bg"
                  cx="60"
                  cy="60"
                  r="54"
                  fill="none"
                  stroke="#e5e7eb"
                  stroke-width="8"
                />
                <circle
                  class="countdown-circle"
                  cx="60"
                  cy="60"
                  r="54"
                  fill="none"
                  stroke="#10b981"
                  stroke-width="8"
                  stroke-linecap="round"
                  :stroke-dasharray="339.292"
                  :stroke-dashoffset="339.292 * (1 - qrCodeSuccessCountdown / 30)"
                  transform="rotate(-90 60 60)"
                />
                <text
                  x="60"
                  y="60"
                  text-anchor="middle"
                  dominant-baseline="middle"
                  font-size="28"
                  font-weight="bold"
                  fill="#10b981"
                >
                  {{ qrCodeSuccessCountdown }}
                </text>
              </svg>
              <p style="margin-top: 15px; font-size: 0.9em; color: #666;">
                Closing in {{ qrCodeSuccessCountdown }} seconds...
              </p>
            </div>
            
            <!-- Close button -->
            <div style="margin-top: 30px;">
              <button class="btn-modal btn-primary" @click="closeMobileQRAndAbout">
                Close
              </button>
            </div>
          </div>
          
          <!-- Normal State: Show QR Code -->
          <div v-else-if="!qrCodePaired" class="info-box">
            <p style="margin-bottom: 15px;">
              Scan this QR code with the Image Tools Android app to link your mobile device for easy image sharing.
            </p>
            
            <div v-if="isGeneratingQRCode" class="qr-code-loading">
              <div class="loading-spinner"></div>
              <p>Generating QR code...</p>
            </div>
            
            <div v-else-if="qrCodeError" class="qr-code-error">
              <p>❌ {{ qrCodeError }}</p>
              <button @click="regenerateQRCode" class="btn-modal btn-secondary" style="margin-top: 10px;">
                Try Again
              </button>
            </div>
            
            <div v-else-if="qrCodeDataUrl" class="qr-code-container">
              <div style="display: flex; justify-content: center; margin-bottom: 15px;">
                <img :src="qrCodeDataUrl" alt="QR Code for Mobile App" class="qr-code-image" />
              </div>
              
              <p style="margin-top: 10px; font-size: 0.9em; color: #666; text-align: center;">
                This QR code pairs your mobile device with this session for secure image uploads.
              </p>
              <p style="margin-top: 8px; font-size: 1.1em; color: #ff6b35; font-weight: 600; text-align: center;">
                ⏱️ Expires in {{ qrCodeTimeRemaining }} • Single-use only
              </p>
              
              <div style="display: flex; justify-content: center; margin-top: 15px;">
                <button @click="regenerateQRCode" class="btn-modal btn-secondary">
                  🔄 Regenerate QR Code
                </button>
              </div>
              
              <div class="info-box info-box-highlight" style="margin-top: 20px;">
                <p><strong>How to use:</strong></p>
                <ol style="margin: 10px 0; padding-left: 20px;">
                  <li>Open the Image Tools app on your Android device</li>
                  <li>Tap "Scan QR Code" to scan the code above</li>
                  <li>Once paired, share images from your Gallery to "Image Tools"</li>
                </ol>
                
                <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #dee2e6;">
                  <p style="margin-bottom: 10px; font-weight: 600;">📱 Alternative: Direct Pairing Link</p>
                  <p style="margin-bottom: 12px; font-size: 0.9em; color: #666;">
                    Open this page on your Android device and tap the button below to pair directly:
                  </p>
                  <a 
                    :href="getPairingIntentUrl()"
                    class="btn-modal btn-primary"
                    style="display: block; text-align: center; text-decoration: none; width: 100%;"
                  >
                    🔗 Pair This Device
                  </a>
                  <p style="margin-top: 10px; font-size: 0.85em; color: #666; text-align: center;">
                    (This only works if you're viewing this page on your Android device)
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="modal-footer" v-if="!qrCodePaired">
          <button class="btn-modal btn-primary" @click="showMobileQRModal = false">
            Close
          </button>
        </div>
      </div>
    </div>

    <!-- Browser Addon Connection Modal -->
    <div v-if="showAddonModal" class="modal-overlay" @click="showAddonModal = false">
      <div class="settings-modal" @click.stop>
        <button class="modal-close-btn" @click="showAddonModal = false">✕</button>
        
        <div class="modal-header">
          <h2>🧩 Browser Addon Connection</h2>
        </div>
        
        <div class="settings-content">
          <div class="settings-section">
            <div class="info-box">
              <p><strong>Connect Browser Addon for Screenshot Capture</strong></p>
              <p style="margin-top: 10px;">
                Install our browser addon to capture screenshots (full page, visible area, or selected region) 
                and send them directly to Image Tools.
              </p>
            </div>
            
            <!-- Generate Connection String Button -->
            <div v-if="!addonRegistrationUrl" style="margin-top: 20px;">
              <button 
                class="btn-modal btn-primary" 
                @click="generateAddonRegistrationUrl"
                :disabled="isGeneratingAddonUrl"
                style="width: 100%;"
              >
                {{ isGeneratingAddonUrl ? 'Generating...' : '🔗 Get Connection String' }}
              </button>
            </div>
            
            <!-- Connection Instructions (after string is generated and copied) -->
            <div v-if="addonRegistrationUrl" class="info-box info-box-success" style="margin-top: 20px;">
              <p style="margin-bottom: 15px;">
                <strong v-if="addonUrlCopied">✓ Connection string copied to clipboard!</strong>
                <strong v-else style="color: #f59e0b;">⚠️ Connection string generated</strong>
              </p>
              
              <div v-if="!addonUrlCopied" style="margin-bottom: 15px;">
                <button 
                  class="btn-modal btn-primary" 
                  @click="copyAddonUrl"
                  style="width: 100%;"
                >
                  📋 Copy Connection String to Clipboard
                </button>
              </div>
              
              <div style="background: #fff3cd; padding: 12px; border-radius: 6px; margin-bottom: 15px; border: 2px solid #ffc107; text-align: center;">
                <p style="margin: 0; font-size: 1.2em; font-weight: bold; color: #856404;">
                  ⏱️ Expires in: {{ Math.floor(addonCountdownSeconds / 60) }}:{{ String(addonCountdownSeconds % 60).padStart(2, '0') }}
                </p>
              </div>
              
              <p style="margin-bottom: 10px;"><strong>How to connect:</strong></p>
              <ol style="margin-left: 20px; line-height: 1.8;">
                <li>Click the ImageTools extension icon in your browser toolbar</li>
                <li>Click the "Connect to ImageTools" button</li>
                <li>Paste the connection string when prompted</li>
                <li>Click "Connect" to complete the setup</li>
              </ol>
              <p style="margin-top: 15px; font-size: 0.85em; color: #666;">
                💡 Connection string expires in 2 minutes. 
                <a href="#" @click.prevent="addonRegistrationUrl = null; addonCountdownSeconds = 0; addonUrlCopied = false; if (addonCountdownInterval) clearInterval(addonCountdownInterval);" style="color: #6366f1; text-decoration: underline;">
                  Generate new string
                </a>
              </p>
            </div>
            
            <!-- Connected Addons List -->
            <div v-if="connectedAddons && connectedAddons.length > 0" style="margin-top: 30px;">
              <h3 style="margin-bottom: 10px;">Connected Addons:</h3>
              <div v-for="addon in connectedAddons" :key="addon.id" class="connected-device-item">
                <div class="device-info">
                  <span class="device-icon">🧩</span>
                  <div class="device-details">
                    <strong>{{ addon.browser_name || 'Browser' }} {{ addon.browser_version ? `v${addon.browser_version}` : '' }}</strong>
                    <p style="font-size: 0.85em; color: #666; margin-top: 4px;">
                      <span v-if="addon.os_name">{{ addon.os_name }} • </span>
                      Connected: {{ formatDate(addon.created_at) }}
                      <span v-if="addon.last_used_at"> • Last used: {{ formatDate(addon.last_used_at) }}</span>
                    </p>
                  </div>
                </div>
                <div v-if="addonPendingRevoke === addon.id" style="display: flex; gap: 8px;">
                  <button 
                    class="btn-revoke-confirm" 
                    @click="revokeAddonAuthorization(addon.id)"
                    title="Confirm disconnect"
                  >
                    ✓ Confirm
                  </button>
                  <button 
                    class="btn-revoke-cancel" 
                    @click="cancelRevokeAddon"
                    title="Cancel"
                  >
                    ✕
                  </button>
                </div>
                <button 
                  v-else
                  class="btn-revoke" 
                  @click="revokeAddonAuthorization(addon.id)"
                  title="Disconnect this browser"
                >
                  ✕
                </button>
              </div>
            </div>
            
            <!-- Browser Install Links -->
            <div class="info-box info-box-highlight" style="margin-top: 30px;">
              <p><strong>📥 Install Browser Addon:</strong></p>
              
              <!-- Current Browser (Highlighted) -->
              <div style="margin-top: 15px;">
                <a 
                  v-if="currentBrowser.storeUrl" 
                  :href="currentBrowser.storeUrl" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  class="addon-install-link current-browser"
                  :title="`Install for ${currentBrowser.name}`"
                >
                  <span style="font-size: 1.5em;">{{ currentBrowser.icon }}</span>
                  <span style="font-weight: 600;">Install for {{ currentBrowser.name }}</span>
                  <span style="font-size: 0.85em; opacity: 0.8;">(Recommended)</span>
                </a>
                <div 
                  v-else
                  class="addon-install-link disabled"
                  :title="`${currentBrowser.name} addon not available yet`"
                >
                  <span style="font-size: 1.5em;">{{ currentBrowser.icon }}</span>
                  <span style="font-weight: 600;">{{ currentBrowser.name }}</span>
                  <span style="font-size: 0.85em; opacity: 0.8;">(Not available)</span>
                </div>
              </div>
              
              <!-- Other Browsers -->
              <details style="margin-top: 15px;">
                <summary style="cursor: pointer; font-size: 0.9em; color: #6b7280; user-select: none;">
                  Install for other browsers
                </summary>
                <div style="margin-top: 10px; display: flex; flex-direction: column; gap: 8px;">
                  <a 
                    v-if="currentBrowser.name !== 'Firefox'"
                    href="https://addons.mozilla.org/firefox/addon/[addon-slug-here]" 
                    target="_blank"
                    rel="noopener noreferrer"
                    class="addon-install-link other-browser firefox"
                    title="Install Firefox addon"
                  >
                    🦊 Firefox
                  </a>
                  
                  <a 
                    v-if="currentBrowser.name !== 'Chrome'"
                    href="https://chrome.google.com/webstore/detail/[addon-id-here]" 
                    target="_blank"
                    rel="noopener noreferrer"
                    class="addon-install-link other-browser chrome"
                    title="Install Chrome addon (also works for Edge)"
                  >
                    🔵 Chrome / Edge
                  </a>
                </div>
              </details>
              
              <p style="margin-top: 15px; font-size: 0.85em; color: #666; line-height: 1.5;">
                💡 <strong>Note:</strong> The addons are ready to use! Click the link above to install for your browser. 
                The store URLs will be updated once the addons are published.
              </p>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn-modal btn-primary" @click="showAddonModal = false">
            Close
          </button>
        </div>
      </div>
    </div>

    <!-- Image Card Settings Modal -->
    <div v-if="showImageCardSettingsModal" class="modal-overlay" @click="showImageCardSettingsModal = false">
      <div class="settings-modal" @click.stop>
        <button class="modal-close-btn" @click="showImageCardSettingsModal = false">✕</button>
        
        <div class="modal-header">
          <h2>🖼️ Image Card Settings</h2>
        </div>
        
        <div class="settings-content">
          <div class="settings-section">
            <h3>Card Size</h3>
            <p class="setting-description">Adjust the size of image cards in the gallery</p>
            
            <div class="size-options">
              <label 
                class="size-option"
                :class="{ active: imageCardSize === 'small' }"
              >
                <input 
                  type="radio" 
                  name="cardSize" 
                  value="small" 
                  v-model="imageCardSize"
                />
                <div class="option-content">
                  <span class="option-icon">📱</span>
                  <div class="option-text">
                    <span class="option-title">Small</span>
                    <span class="option-desc">200px preview height</span>
                  </div>
                </div>
              </label>
              
              <label 
                class="size-option"
                :class="{ active: imageCardSize === 'medium' }"
              >
                <input 
                  type="radio" 
                  name="cardSize" 
                  value="medium" 
                  v-model="imageCardSize"
                />
                <div class="option-content">
                  <span class="option-icon">💻</span>
                  <div class="option-text">
                    <span class="option-title">Medium</span>
                    <span class="option-desc">300px preview height</span>
                  </div>
                </div>
              </label>
              
              <label 
                class="size-option"
                :class="{ active: imageCardSize === 'large' }"
              >
                <input 
                  type="radio" 
                  name="cardSize" 
                  value="large" 
                  v-model="imageCardSize"
                />
                <div class="option-content">
                  <span class="option-icon">🖥️</span>
                  <div class="option-text">
                    <span class="option-title">Large</span>
                    <span class="option-desc">400px preview height</span>
                  </div>
                </div>
              </label>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn-modal btn-primary" @click="showImageCardSettingsModal = false">
            Done
          </button>
        </div>
      </div>
    </div>

    <!-- Model Selection Modal -->
    <div v-if="showModelSelector" class="modal-overlay" @click="showModelSelector = false">
      <div class="model-selector-modal" @click.stop>
        <button class="modal-close-btn" @click="showModelSelector = false">✕</button>
        
        <div class="modal-header">
          <h2>🧠 Choose AI Model</h2>
        </div>
        
        <div class="model-selector-content">
          <p class="selector-description">
            Select the AI model you want to use for image manipulation. Each model has different capabilities, speeds, and costs.
          </p>
          
          <!-- Filter Controls -->
          <div class="model-filters">
            <div class="filter-search">
              <input 
                v-model="modelSearchQuery"
                type="text"
                placeholder="🔍 Search models..."
                class="search-input"
              />
            </div>
            <div class="filter-toggle">
              <label class="toggle-switch">
                <input type="checkbox" v-model="showOnlyFreeModels" />
                <span class="toggle-slider"></span>
                <span class="toggle-label">Free only</span>
              </label>
            </div>
            <div class="filter-toggle">
              <label class="toggle-switch">
                <input type="checkbox" v-model="showOnlyImageEditingModels" />
                <span class="toggle-slider"></span>
                <span class="toggle-label">Image editing only</span>
              </label>
            </div>
            <div class="filter-tags">
              <label class="filter-label">Tags:</label>
              <select v-model="selectedTagFilter" class="tag-filter-select">
                <option value="">All Tags</option>
                <option v-for="tag in availableTags" :key="tag" :value="tag">{{ tag }}</option>
              </select>
            </div>
          </div>

          <!-- Loading state -->
          <div v-if="isLoadingModels" class="models-loading">
            <span class="loading-spinner">⏳</span>
            <p>Loading models from OpenRouter...</p>
          </div>

          <!-- Error state -->
          <div v-if="modelsLoadError" class="models-error">
            <p>❌ {{ modelsLoadError }}</p>
            <button class="btn-retry" @click="loadAllModels">Retry</button>
          </div>

          <!-- Recommended Models Section -->
          <div v-if="!isLoadingModels && !modelsLoadError && filteredRecommendedModels.length > 0" class="models-section">
            <h3 class="section-header">⭐ Recommended Models</h3>
            <div class="model-grid">
              <div 
                v-for="model in filteredRecommendedModels" 
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
                
                <div class="model-description-container">
                  <p 
                    class="model-description" 
                    :class="{ 'expanded': expandedDescriptions.has(model.id) }"
                  >
                    {{ expandedDescriptions.has(model.id) ? model.description : model.descriptionShort }}
                  </p>
                  <button 
                    v-if="model.description.length > 200"
                    @click.stop="toggleDescription(model.id)"
                    class="btn-toggle-description"
                  >
                    {{ expandedDescriptions.has(model.id) ? 'Show less' : 'Show more' }}
                  </button>
                </div>
                
                <div class="model-tags">
                  <span 
                    v-for="tag in model.tags" 
                    :key="tag" 
                    class="model-tag"
                    :class="{ 
                      'tag-free': tag === 'Free', 
                      'tag-recommended': tag === 'Recommended',
                      'tag-image-editing': tag === 'Image Editing'
                    }"
                  >
                    {{ tag }}
                  </span>
                </div>
                
                <div class="model-specs">
                  <div class="spec-item" v-if="model.contextWindow">
                    <span class="spec-label">Context:</span>
                    <span class="spec-value">{{ formatContextWindow(model.contextWindow) }}</span>
                  </div>
                  <div class="spec-item" v-if="model.maxTokens">
                    <span class="spec-label">Max Output:</span>
                    <span class="spec-value">{{ formatTokens(model.maxTokens) }}</span>
                  </div>
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

          <!-- Divider between recommended and all models -->
          <div v-if="!isLoadingModels && !modelsLoadError && filteredRecommendedModels.length > 0 && filteredOtherModels.length > 0" class="section-divider">
            <span>All Models ({{ filteredOtherModels.length }})</span>
          </div>

          <!-- All Other Models Section -->
          <div v-if="!isLoadingModels && !modelsLoadError && filteredOtherModels.length > 0" class="models-section">
            <div class="model-grid">
              <div 
                v-for="model in filteredOtherModels" 
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
                
                <div class="model-description-container">
                  <p 
                    class="model-description" 
                    :class="{ 'expanded': expandedDescriptions.has(model.id) }"
                  >
                    {{ expandedDescriptions.has(model.id) ? model.description : model.descriptionShort }}
                  </p>
                  <button 
                    v-if="model.description.length > 200"
                    @click.stop="toggleDescription(model.id)"
                    class="btn-toggle-description"
                  >
                    {{ expandedDescriptions.has(model.id) ? 'Show less' : 'Show more' }}
                  </button>
                </div>
                
                <div class="model-tags">
                  <span 
                    v-for="tag in model.tags" 
                    :key="tag" 
                    class="model-tag"
                    :class="{ 
                      'tag-free': tag === 'Free', 
                      'tag-recommended': tag === 'Recommended',
                      'tag-image-editing': tag === 'Image Editing'
                    }"
                  >
                    {{ tag }}
                  </span>
                </div>
                
                <div class="model-specs">
                  <div class="spec-item" v-if="model.contextWindow">
                    <span class="spec-label">Context:</span>
                    <span class="spec-value">{{ formatContextWindow(model.contextWindow) }}</span>
                  </div>
                  <div class="spec-item" v-if="model.maxTokens">
                    <span class="spec-label">Max Output:</span>
                    <span class="spec-value">{{ formatTokens(model.maxTokens) }}</span>
                  </div>
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

          <!-- No results -->
          <div v-if="!isLoadingModels && !modelsLoadError && filteredRecommendedModels.length === 0 && filteredOtherModels.length === 0" class="no-results">
            <p>No models found matching your search.</p>
          </div>
          
          <!-- About AI Models Info -->
          <div v-if="!isLoadingModels && !modelsLoadError" class="info-box model-info">
            <p><strong>About AI Models:</strong></p>
            <p>Different models have varying capabilities, speeds, and costs. Free models are great for testing, while premium models offer better quality and advanced features.</p>
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

    <!-- Offline Detection Modal -->
    <OfflineModal 
      v-if="showOfflineModal"
      ref="offlineModalRef"
      @retry="handleOfflineRetry"
    />

    <!-- Toast Notifications -->
    <ToastNotification />

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue';
import { useSessionStore } from './stores/sessionStore';
import { useImageStore } from './stores/imageStore';
import { storeToRefs } from 'pinia';
import { imageService, sessionService, setOfflineCallback, markOnline } from './services/api';
import { openRouterService, generateCodeVerifier, generateCodeChallenge } from './services/openRouterService';
import { chatService } from './services/chatService';
import mobileService from './services/mobileService';
import addonService from './services/addonService';
import QRCode from 'qrcode';
import { 
  startHealthCheck, 
  stopHealthCheck, 
  setOfflineCallback as setHealthOfflineCallback,
  setOnlineCallback as setHealthOnlineCallback,
  checkHealthNow
} from './services/healthCheckService';
import {
  connectWebSocket,
  disconnectWebSocket,
  setOfflineCallback as setWebSocketOfflineCallback,
  setOnlineCallback as setWebSocketOnlineCallback,
  setNewImageCallback,
  resetReconnectAttempts
} from './services/websocketService';
import UploadArea from './components/UploadArea.vue';
import ImageCard from './components/ImageCard.vue';
import ImageViewer from './components/ImageViewer.vue';
import ImageEditor from './components/ImageEditor.vue';
import OfflineModal from './components/OfflineModal.vue';
import ToastNotification from './components/ToastNotification.vue';

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
const showOfflineModal = ref(false);
const offlineModalRef = ref(null);

// Settings menu state
const showSettingsMenu = ref(false);
const showAISettingsModal = ref(false);
const showPresetSettingsModal = ref(false);
const showAboutModal = ref(false);
const showImageCardSettingsModal = ref(false);
const showMobileQRModal = ref(false);
const showAddonModal = ref(false);

// Addon authorization state
const addonRegistrationUrl = ref(null);
const isGeneratingAddonUrl = ref(false);
const addonUrlCopied = ref(false);
const connectedAddons = ref([]);
const addonCountdownSeconds = ref(0);
const addonPendingRevoke = ref(null); // Track which addon is pending revoke confirmation
let addonCountdownInterval = null;

// Image card settings
const imageCardSize = ref(localStorage.getItem('imageCardSize') || 'small');

// App configuration state
const appConfig = ref({
  session_expiry_days: 7,
  max_images_per_session: 5,
  max_upload_size_mb: 20
});

// OpenRouter OAuth state
const openRouterConnected = ref(false);
const openRouterCredits = ref(null);
const oauthNotification = ref(null); // { type: 'success' | 'error', message: string }
const selectedModel = ref('');
const showModelSelector = ref(false);
const selectedModelForDetails = ref(null);
const showModelDetailsModal = ref(false);

// Model loading and filtering state
const allModels = ref([]);
const isLoadingModels = ref(false);
const modelsLoadError = ref(null);
const modelSearchQuery = ref('');
const showOnlyFreeModels = ref(false);
const showOnlyImageEditingModels = ref(true); // Enabled by default
const selectedTagFilter = ref('');
const expandedDescriptions = ref(new Set()); // Track which model descriptions are expanded

// Recommended model IDs (hardcoded list of preferred models)
const recommendedModelIds = [
  // Vision models (text+image->text) for viewing/analysis
  'qwen/qwen3-vl-8b-instruct',                        // Best value - cheapest vision model
  'google/gemini-2.5-flash-lite-preview-09-2025',    // Google's low-cost option
  'qwen/qwen3-vl-30b-a3b-instruct',                  // Better quality, affordable
  'allenai/molmo-2-8b',                              // Video support, low cost
  'google/gemini-3-flash-preview',                   // High quality Google option
  'anthropic/claude-3.5-sonnet',                     // Premium quality
  
  // Image editing models (text+image->text+image) for object removal, inpainting
  'google/gemini-2.5-flash-image',                   // Low cost editing
  'openai/gpt-5-image-mini',                         // Mid-range editing
  'google/gemini-3-pro-image-preview',               // High quality editing
  'google/gemini-4-pro-image-preview',               // Latest Gemini 4 with image editing
];

// Provider icons and colors mapping
const providerInfo = {
  'google': { icon: '⚡', color: '#4285f4' },
  'anthropic': { icon: '🧠', color: '#cc785c' },
  'openai': { icon: '🤖', color: '#10a37f' },
  'meta': { icon: '🦙', color: '#0668e1' },
  'meta-llama': { icon: '🦙', color: '#0668e1' },
  'mistralai': { icon: '🌪️', color: '#ff7f00' },
  'qwen': { icon: '🔷', color: '#1890ff' },
  'nvidia': { icon: '💚', color: '#76b900' },
  'cohere': { icon: '🔮', color: '#39594d' },
  'allenai': { icon: '🔬', color: '#00a4e4' },
  'default': { icon: '🤖', color: '#666' }
};

// Mobile app pairing / QR code state
const qrCodeDataUrl = ref(null);
const qrCodePairingId = ref(null);
const qrData = ref(null);
const isGeneratingQRCode = ref(false);
const qrCodeError = ref(null);
const qrCodeExpiresAt = ref(null);
const qrCodeSecondsRemaining = ref(0);
const qrCodePaired = ref(false);
const qrCodeSuccessCountdown = ref(30);
const pairingCodeCopied = ref(false);
let qrCodeTimerInterval = null;
let qrCodePollingInterval = null;
let qrCodeSuccessInterval = null;

// Get provider info from model ID
const getProviderInfo = (modelId) => {
  const provider = modelId.split('/')[0].toLowerCase();
  return providerInfo[provider] || providerInfo.default;
};

// Parse model data from OpenRouter API
const parseModelFromAPI = (apiModel) => {
  const provider = apiModel.id.split('/')[0];
  const providerDetails = getProviderInfo(apiModel.id);
  
  // Calculate cost display
  let costDisplay = 'Free';
  let isFree = false;
  
  if (apiModel.pricing) {
    const promptCost = parseFloat(apiModel.pricing.prompt || 0);
    const completionCost = parseFloat(apiModel.pricing.completion || 0);
    
    if (promptCost === 0 && completionCost === 0) {
      costDisplay = 'Free';
      isFree = true;
    } else {
      // Average of prompt and completion cost per 1M tokens
      const avgCost = ((promptCost + completionCost) / 2) * 1000000;
      costDisplay = `$${avgCost.toFixed(2)} / 1M`;
    }
  }
  
  // Generate tags
  const tags = [];
  if (isFree) tags.push('Free');
  if (recommendedModelIds.includes(apiModel.id)) tags.push('Recommended');
  if (apiModel.architecture?.modality?.includes('image')) tags.push('Vision');
  
  // Check if model can output images (image editing capability)
  if (apiModel.architecture?.modality?.includes('->text+image') || 
      apiModel.architecture?.modality?.includes('->image')) {
    tags.push('Image Editing');
  }
  
  if (apiModel.top_provider?.is_moderated) tags.push('Moderated');
  if (apiModel.context_length >= 100000) tags.push('Large Context');
  
  // Extract capabilities from description or supported parameters
  if (apiModel.description?.toLowerCase().includes('reasoning')) tags.push('Reasoning');
  if (apiModel.description?.toLowerCase().includes('code') || apiModel.description?.toLowerCase().includes('coding')) tags.push('Coding');
  if (apiModel.description?.toLowerCase().includes('fast') || apiModel.name?.toLowerCase().includes('turbo')) tags.push('Fast');
  
  return {
    id: apiModel.id,
    name: apiModel.name,
    provider: provider.charAt(0).toUpperCase() + provider.slice(1).replace('-', ' '),
    description: apiModel.description?.split('\n')[0] || 'No description available',
    descriptionShort: apiModel.description?.split('\n')[0]?.substring(0, 200) || 'No description available',
    cost: costDisplay,
    isFree: isFree,
    tags: tags,
    icon: providerDetails.icon,
    color: providerDetails.color,
    contextWindow: apiModel.context_length || null,
    maxTokens: apiModel.top_provider?.max_completion_tokens || null,
    isRecommended: recommendedModelIds.includes(apiModel.id)
  };
};

// Load all models from OpenRouter API
const loadAllModels = async () => {
  isLoadingModels.value = true;
  modelsLoadError.value = null;
  
  try {
    const apiModels = await openRouterService.getModels();
    allModels.value = apiModels
      .filter(m => m.id && m.name) // Filter out invalid models
      .map(parseModelFromAPI)
      .sort((a, b) => {
        // Sort: Recommended first, then by name
        if (a.isRecommended && !b.isRecommended) return -1;
        if (!a.isRecommended && b.isRecommended) return 1;
        return a.name.localeCompare(b.name);
      });
    
    console.log(`Loaded ${allModels.value.length} models from OpenRouter`);
  } catch (error) {
    console.error('Failed to load models:', error);
    modelsLoadError.value = error.message || 'Failed to load models from OpenRouter';
  } finally {
    isLoadingModels.value = false;
  }
};

// Get all unique tags from models
const availableTags = computed(() => {
  const tags = new Set();
  allModels.value.forEach(model => {
    model.tags.forEach(tag => tags.add(tag));
  });
  return Array.from(tags).sort();
});

// Get username from session
const username = computed(() => {
  // First check if sessionData has user_id
  if (sessionStore.sessionData && sessionStore.sessionData.user_id) {
    return sessionStore.sessionData.user_id;
  }
  
  // Check if session override is being used (for testing)
  const sessionOverride = import.meta.env.VITE_SESSION_OVERRIDE;
  if (sessionOverride && sessionOverride.trim() !== '') {
    return sessionOverride;
  }
  
  // Check if sessionId looks like a username (not a UUID)
  if (sessionId.value) {
    // UUIDs have format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    const isUUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(sessionId.value);
    if (!isUUID) {
      // Session ID doesn't look like UUID, might be a username
      return sessionId.value;
    }
  }
  
  return null;
});

// Format QR code countdown timer
const qrCodeTimeRemaining = computed(() => {
  const seconds = qrCodeSecondsRemaining.value;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
});

// Detect current browser
const currentBrowser = computed(() => {
  const userAgent = navigator.userAgent;
  
  if (userAgent.indexOf('Firefox/') > -1) {
    return { name: 'Firefox', icon: '🦊', storeUrl: 'https://addons.mozilla.org/firefox/addon/[addon-slug-here]' };
  } else if (userAgent.indexOf('Chrome/') > -1 || userAgent.indexOf('Edg/') > -1) {
    // Chrome or Edge (Edge users will get Chrome extension)
    return { name: 'Chrome', icon: '🔵', storeUrl: 'https://chrome.google.com/webstore/detail/[addon-id-here]' };
  } else if (userAgent.indexOf('Safari/') > -1 && userAgent.indexOf('Chrome') === -1) {
    return { name: 'Safari', icon: '🧭', storeUrl: null };
  } else {
    return { name: 'Browser', icon: '🌐', storeUrl: null };
  }
});

// Fetch app configuration from backend
const fetchAppConfig = async () => {
  try {
    const response = await fetch('/api/v1/settings/app-config');
    if (response.ok) {
      const data = await response.json();
      appConfig.value = data;
      console.log('App config loaded:', data);
    }
  } catch (error) {
    console.error('Failed to fetch app config:', error);
  }
};

// Filter models based on search query, free toggle, image editing toggle, and tag filter
const filterModels = (models) => {
  return models.filter(model => {
    // Free filter
    if (showOnlyFreeModels.value && !model.isFree) {
      return false;
    }
    
    // Image editing filter
    if (showOnlyImageEditingModels.value && !model.tags.includes('Image Editing')) {
      return false;
    }
    
    // Tag filter
    if (selectedTagFilter.value && !model.tags.includes(selectedTagFilter.value)) {
      return false;
    }
    
    // Search filter
    if (modelSearchQuery.value) {
      const query = modelSearchQuery.value.toLowerCase();
      const searchableText = [
        model.name,
        model.provider,
        model.description,
        model.id,
        ...model.tags
      ].join(' ').toLowerCase();
      
      if (!searchableText.includes(query)) {
        return false;
      }
    }
    
    return true;
  });
};

// Filtered recommended models
const filteredRecommendedModels = computed(() => {
  const recommended = allModels.value.filter(m => m.isRecommended);
  const filtered = filterModels(recommended);
  
  // Promote selected model to the top
  if (selectedModel.value) {
    const selectedIndex = filtered.findIndex(m => m.id === selectedModel.value);
    if (selectedIndex > 0) {
      const selectedModelData = filtered.splice(selectedIndex, 1)[0];
      filtered.unshift(selectedModelData);
    }
  }
  
  return filtered;
});

// Filtered other models
const filteredOtherModels = computed(() => {
  const others = allModels.value.filter(m => !m.isRecommended);
  const filtered = filterModels(others);
  
  // Promote selected model to the top
  if (selectedModel.value) {
    const selectedIndex = filtered.findIndex(m => m.id === selectedModel.value);
    if (selectedIndex > 0) {
      const selectedModelData = filtered.splice(selectedIndex, 1)[0];
      filtered.unshift(selectedModelData);
    }
  }
  
  return filtered;
});

// Format context window for display
const formatContextWindow = (tokens) => {
  if (!tokens) return 'Unknown';
  if (tokens >= 1000000) return `${(tokens / 1000000).toFixed(1)}M`;
  if (tokens >= 1000) return `${(tokens / 1000).toFixed(0)}K`;
  return tokens.toString();
};

// Format max tokens for display
const formatTokens = (tokens) => {
  if (!tokens) return 'Unknown';
  if (tokens >= 1000) return `${(tokens / 1000).toFixed(0)}K`;
  return tokens.toString();
};

const getSelectedModelData = () => {
  return allModels.value.find(m => m.id === selectedModel.value);
};

const initializeApp = async () => {
  isLoading.value = true;
  error.value = null;

  try {
    await sessionStore.initializeSession();
    await Promise.all([
      imageStore.loadSessionImages(),
      imageStore.loadPresets(),
      fetchAppConfig()
    ]);
    
    // Set session ID in OpenRouter service
    if (sessionId.value) {
      openRouterService.setSessionId(sessionId.value);
      chatService.setSessionId(sessionId.value);
    }
    
    // Check if we're returning from OAuth callback
    handleOAuthCallback();
    
    // Load OpenRouter connection status
    await loadOpenRouterStatus();
    
    // Load saved model selection from backend
    try {
      const settings = await openRouterService.getSettings();
      if (settings.selected_model_id) {
        selectedModel.value = settings.selected_model_id;
        console.log('Loaded selected model from backend:', settings.selected_model_id);
        
        // Load all models so we can display the selected model's details
        if (allModels.value.length === 0) {
          await loadAllModels();
        }
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
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

// Handle switch model from chat recommendations
const handleSwitchModel = async (modelId) => {
  await selectModel(modelId);
  // Close any open modals if needed
};

// Handle show model details from chat recommendations  
const handleShowModelDetails = (modelId) => {
  // Find the model in allModels
  const model = allModels.value.find(m => m.id === modelId);
  if (model) {
    selectedModelForDetails.value = model;
    showModelDetailsModal.value = true;
  } else {
    // If model not loaded yet, open model selector filtered to this model
    modelSearchQuery.value = modelId;
    showModelSelector.value = true;
  }
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

const openAbout = async () => {
  showSettingsMenu.value = false;
  showAboutModal.value = true;
};

const openMobileQRModal = async () => {
  showMobileQRModal.value = true;
  // Generate QR code when opening Mobile QR modal
  await generateQRCode();
};

const closeMobileQRAndAbout = () => {
  // Clear countdown interval
  if (qrCodeSuccessInterval) {
    clearInterval(qrCodeSuccessInterval);
    qrCodeSuccessInterval = null;
  }
  
  // Close both modals
  showMobileQRModal.value = false;
  showAboutModal.value = false;
  
  console.log('[QR Pairing] Manually closed both modals');
};

const openImageCardSettings = () => {
  showSettingsMenu.value = false;
  showImageCardSettingsModal.value = true;
};

// Mobile app pairing / QR code generation
const checkPairingStatus = async () => {
  if (!qrCodePairingId.value) return;
  
  try {
    const pairing = await mobileService.getPairing(qrCodePairingId.value);
    console.log('[QR Pairing] Pairing status check:', { 
      pairingId: qrCodePairingId.value, 
      used: pairing.used, 
      isActive: pairing.is_active 
    });
    
    // Check if pairing has been used
    if (pairing.used) {
      console.log('[QR Pairing] ✅ Pairing has been used! Showing success countdown...');
      qrCodePaired.value = true;
      
      // Clear the expiry timer
      if (qrCodeTimerInterval) {
        clearInterval(qrCodeTimerInterval);
        qrCodeTimerInterval = null;
      }
      
      // Clear the polling interval
      if (qrCodePollingInterval) {
        clearInterval(qrCodePollingInterval);
        qrCodePollingInterval = null;
      }
      
      // Start 30-second success countdown
      qrCodeSuccessCountdown.value = 30;
      qrCodeSuccessInterval = setInterval(() => {
        qrCodeSuccessCountdown.value--;
        console.log('[QR Pairing] Success countdown:', qrCodeSuccessCountdown.value);
        
        if (qrCodeSuccessCountdown.value <= 0) {
          clearInterval(qrCodeSuccessInterval);
          qrCodeSuccessInterval = null;
          
          console.log('[QR Pairing] Countdown complete, closing modal');
          // Close the modal
          showMobileQRModal.value = false;
          
          // Reset state
          qrCodePaired.value = false;
          qrCodeDataUrl.value = null;
          qrCodePairingId.value = null;
        }
      }, 1000);
    }
  } catch (error) {
    console.error('[QR Pairing] Failed to check pairing status:', error);
  }
};

const generateQRCode = async () => {
  if (!sessionId.value) {
    qrCodeError.value = 'No active session';
    return;
  }

  // Clear any existing timers
  if (qrCodeTimerInterval) {
    clearInterval(qrCodeTimerInterval);
    qrCodeTimerInterval = null;
  }
  
  if (qrCodePollingInterval) {
    clearInterval(qrCodePollingInterval);
    qrCodePollingInterval = null;
  }
  
  if (qrCodeSuccessInterval) {
    clearInterval(qrCodeSuccessInterval);
    qrCodeSuccessInterval = null;
  }
  
  // Reset state
  qrCodePaired.value = false;
  qrCodeSuccessCountdown.value = 30;

  try {
    isGeneratingQRCode.value = true;
    qrCodeError.value = null;

    // Create a new pairing (single-use, 2-minute timeout)
    const pairing = await mobileService.createPairing(sessionId.value, 'Mobile Device');
    qrCodePairingId.value = pairing.id;

    // Get QR code data
    const qrDataResponse = await mobileService.getQRCodeData(pairing.id);
    qrData.value = qrDataResponse; // Store for manual pairing display

    // Use instance_url from backend (which handles dev vs prod correctly)
    // In dev: backend will send its own port (8000) instead of frontend port (5173)
    // In prod: backend and frontend are on same host/port
    const instanceUrl = qrDataResponse.instance_url;
    
    console.log('[Mobile QR] Instance URL for mobile app:', instanceUrl);

    // Create QR code payload as JSON
    const qrPayload = JSON.stringify({
      instance_url: instanceUrl,
      shared_secret: qrDataResponse.shared_secret,
      pairing_id: qrDataResponse.pairing_id,
      session_id: qrDataResponse.session_id
    });

    // Generate QR code as data URL
    const dataUrl = await QRCode.toDataURL(qrPayload, {
      width: 300,
      margin: 2,
      color: {
        dark: '#000000',
        light: '#ffffff'
      }
    });

    qrCodeDataUrl.value = dataUrl;
    
    // Set expiration time (2 minutes from now)
    qrCodeExpiresAt.value = new Date(Date.now() + 2 * 60 * 1000);
    qrCodeSecondsRemaining.value = 120;
    
    // Start countdown timer
    qrCodeTimerInterval = setInterval(() => {
      const now = new Date();
      const remaining = Math.max(0, Math.floor((qrCodeExpiresAt.value - now) / 1000));
      qrCodeSecondsRemaining.value = remaining;
      
      // Auto-regenerate when expired
      if (remaining === 0) {
        clearInterval(qrCodeTimerInterval);
        qrCodeTimerInterval = null;
        
        // Only regenerate if the modal is still open and not paired
        if (showMobileQRModal.value && !qrCodePaired.value) {
          console.log('QR code expired, regenerating...');
          regenerateQRCode();
        }
      }
    }, 1000);
    
    // Start polling for pairing status every 2 seconds
    qrCodePollingInterval = setInterval(checkPairingStatus, 2000);
    
  } catch (error) {
    console.error('Failed to generate QR code:', error);
    qrCodeError.value = 'Failed to generate QR code. Please try again.';
  } finally {
    isGeneratingQRCode.value = false;
  }
};

const regenerateQRCode = async () => {
  qrCodeDataUrl.value = null;
  qrCodePairingId.value = null;
  await generateQRCode();
};

const copyPairingCode = async () => {
  try {
    const pairingText = `ImageTools Manual Pairing\n\nURL: ${qrData.value?.instance_url}\nCode: ${qrData.value?.shared_secret}`;
    await navigator.clipboard.writeText(pairingText);
    pairingCodeCopied.value = true;
    setTimeout(() => {
      pairingCodeCopied.value = false;
    }, 3000);
  } catch (err) {
    console.error('Failed to copy pairing code:', err);
  }
};

const getPairingIntentUrl = () => {
  if (!qrData.value) return '#';
  
  // Create Android deep link with pairing data
  // Format: imagetools://pair/link?url=<encoded_url>&secret=<secret>&pairing_id=<id>&session_id=<session>
  const params = new URLSearchParams({
    url: qrData.value.instance_url,
    secret: qrData.value.shared_secret,
    pairing_id: qrData.value.pairing_id,
    session_id: qrData.value.session_id
  });
  
  const deepLink = `imagetools://pair/link?${params.toString()}`;
  console.log('Generated pairing deep link:', deepLink);
  return deepLink;
};

// Browser Addon Authorization Functions
const openAddonModal = async () => {
  showSettingsMenu.value = false;
  showAboutModal.value = false;
  showAddonModal.value = true;
  
  // Load connected addons when opening modal
  await loadConnectedAddons();
};

const generateAddonRegistrationUrl = async () => {
  if (!sessionId.value) {
    console.error('[Addon] No session ID available');
    return;
  }
  
  isGeneratingAddonUrl.value = true;
  
  try {
    const authorization = await addonService.createAuthorization(sessionId.value);
    
    // Parse the registration URL to extract code and instance
    const url = new URL(authorization.registration_url);
    const code = url.searchParams.get('code');
    const instance = url.searchParams.get('instance');
    
    if (!code || !instance) {
      throw new Error('Invalid registration URL format');
    }
    
    // Create JSON object with connection info
    const connectionData = {
      code: code,
      instance: instance
    };
    
    // Base64 encode the connection string
    const jsonString = JSON.stringify(connectionData);
    const base64String = btoa(jsonString);
    
    addonRegistrationUrl.value = base64String;
    
    console.log('[Addon] Generated connection string (not displayed for security)');
    console.log('[Addon] Connection string length:', base64String.length);
    console.log('[Addon] First 20 chars:', base64String.substring(0, 20) + '...');
    
    // Automatically copy to clipboard
    try {
      // Try modern clipboard API first
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(base64String);
        addonUrlCopied.value = true;
        console.log('[Addon] Connection string automatically copied to clipboard (modern API)');
        console.log('[Addon] Verifying copy...');
        
        // Verify the copy worked
        try {
          const clipboardText = await navigator.clipboard.readText();
          if (clipboardText === base64String) {
            console.log('[Addon] ✓ Clipboard verification successful');
          } else {
            console.warn('[Addon] ⚠️ Clipboard content does not match expected string');
            console.log('[Addon] Expected length:', base64String.length, 'Got:', clipboardText.length);
          }
        } catch (readError) {
          console.warn('[Addon] Cannot verify clipboard (permission denied):', readError.message);
        }
      } else {
        // Fallback to older method
        const textarea = document.createElement('textarea');
        textarea.value = base64String;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        const success = document.execCommand('copy');
        document.body.removeChild(textarea);
        
        if (success) {
          addonUrlCopied.value = true;
          console.log('[Addon] Connection string automatically copied to clipboard (fallback)');
        } else {
          throw new Error('execCommand copy failed');
        }
      }
      
      // Show temporary success message
      setTimeout(() => {
        addonUrlCopied.value = false;
      }, 3000);
    } catch (clipboardError) {
      console.error('[Addon] Failed to auto-copy to clipboard:', clipboardError);
      addonUrlCopied.value = false;
      // Show error message to user
      alert('Failed to copy connection string to clipboard. Please try again or copy manually.');
    }
    
    // Start countdown timer (2 minutes = 120 seconds)
    addonCountdownSeconds.value = 120;
    
    // Clear any existing interval
    if (addonCountdownInterval) {
      clearInterval(addonCountdownInterval);
    }
    
    // Start countdown interval
    addonCountdownInterval = setInterval(() => {
      if (addonCountdownSeconds.value > 0) {
        addonCountdownSeconds.value--;
      } else {
        // Expired
        clearInterval(addonCountdownInterval);
        addonCountdownInterval = null;
        addonRegistrationUrl.value = null;
        console.log('[Addon] Connection string expired');
      }
    }, 1000);
    
    // Auto-expire after 2 minutes (120 seconds)
    setTimeout(() => {
      if (addonRegistrationUrl.value === base64String) {
        addonRegistrationUrl.value = null;
        addonCountdownSeconds.value = 0;
        if (addonCountdownInterval) {
          clearInterval(addonCountdownInterval);
          addonCountdownInterval = null;
        }
        console.log('[Addon] Connection string expired');
      }
    }, 2 * 60 * 1000);
    
  } catch (error) {
    console.error('[Addon] Failed to generate connection string:', error);
    alert('Failed to generate connection string. Please try again.');
  } finally {
    isGeneratingAddonUrl.value = false;
  }
};

const copyAddonUrl = async () => {
  if (!addonRegistrationUrl.value) return;
  
  try {
    console.log('[Addon] Manual copy requested');
    console.log('[Addon] String length:', addonRegistrationUrl.value.length);
    
    // Try modern clipboard API first
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(addonRegistrationUrl.value);
      addonUrlCopied.value = true;
      console.log('[Addon] Manual copy successful (modern API)');
      
      // Verify
      try {
        const clipboardText = await navigator.clipboard.readText();
        if (clipboardText === addonRegistrationUrl.value) {
          console.log('[Addon] ✓ Manual copy verification successful');
        } else {
          console.warn('[Addon] ⚠️ Manual copy verification failed');
        }
      } catch (readError) {
        console.warn('[Addon] Cannot verify clipboard:', readError.message);
      }
    } else {
      // Fallback to older method
      const textarea = document.createElement('textarea');
      textarea.value = addonRegistrationUrl.value;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      const success = document.execCommand('copy');
      document.body.removeChild(textarea);
      
      if (success) {
        addonUrlCopied.value = true;
        console.log('[Addon] Manual copy successful (fallback)');
      } else {
        throw new Error('execCommand copy failed');
      }
    }
    
    setTimeout(() => {
      addonUrlCopied.value = false;
    }, 3000);
  } catch (err) {
    console.error('[Addon] Failed to copy URL:', err);
    alert('Failed to copy to clipboard. Please try copying manually.');
  }
};

const loadConnectedAddons = async () => {
  if (!sessionId.value) return;
  
  try {
    connectedAddons.value = await addonService.listConnectedAddons(sessionId.value);
  } catch (error) {
    console.error('[Addon] Failed to load connected addons:', error);
  }
};

const revokeAddonAuthorization = async (authId) => {
  // If already pending, this is the confirm action
  if (addonPendingRevoke.value === authId) {
    try {
      await addonService.revokeAuthorization(authId);
      await loadConnectedAddons();
      addonPendingRevoke.value = null;
    } catch (error) {
      console.error('[Addon] Failed to revoke authorization:', error);
      alert('Failed to disconnect addon. Please try again.');
    }
  } else {
    // Set as pending
    addonPendingRevoke.value = authId;
  }
};

const cancelRevokeAddon = () => {
  addonPendingRevoke.value = null;
};

const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

// Watch for addon modal close and cleanup
watch(showAddonModal, (isOpen) => {
  if (!isOpen) {
    // Reset state when modal is closed
    addonRegistrationUrl.value = null;
    addonUrlCopied.value = false;
    addonCountdownSeconds.value = 0;
    addonPendingRevoke.value = null;
    
    // Clear countdown interval
    if (addonCountdownInterval) {
      clearInterval(addonCountdownInterval);
      addonCountdownInterval = null;
    }
  }
});

// Watch for imageCardSize changes and save to localStorage
watch(imageCardSize, (newSize) => {
  localStorage.setItem('imageCardSize', newSize);
  console.log('Image card size changed to:', newSize);
});

// Watch for mobile QR modal close and clear timers
watch(showMobileQRModal, (isOpen) => {
  if (!isOpen) {
    if (qrCodeTimerInterval) {
      clearInterval(qrCodeTimerInterval);
      qrCodeTimerInterval = null;
    }
    if (qrCodePollingInterval) {
      clearInterval(qrCodePollingInterval);
      qrCodePollingInterval = null;
    }
    if (qrCodeSuccessInterval) {
      clearInterval(qrCodeSuccessInterval);
      qrCodeSuccessInterval = null;
    }
  }
});

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

// Model selection handlers
const openModelSelector = async () => {
  showModelSelector.value = true;
  
  // Load models if not already loaded
  if (allModels.value.length === 0 && !isLoadingModels.value) {
    await loadAllModels();
  }
};

const selectModel = async (modelId) => {
  selectedModel.value = modelId;
  console.log('Model selected:', modelId);
  
  // Save to backend
  try {
    await openRouterService.updateModel(modelId);
    console.log('Model saved to backend:', modelId);
  } catch (error) {
    console.error('Failed to save model to backend:', error);
    // Still update the UI even if backend save fails
  }
};

const toggleDescription = (modelId) => {
  if (expandedDescriptions.value.has(modelId)) {
    expandedDescriptions.value.delete(modelId);
  } else {
    expandedDescriptions.value.add(modelId);
  }
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

const handleOfflineRetry = async () => {
  try {
    console.log('[App] Attempting manual retry...');
    // Use the health check service to check if backend is back online
    await checkHealthNow();
    // If successful, modal will be hidden by the health check service's online callback
    console.log('[App] Retry successful, backend is back online');
    // Also reset WebSocket reconnection attempts
    resetReconnectAttempts();
    // Reconnect WebSocket
    connectWebSocket();
  } catch (error) {
    // Still offline - keep modal visible and restart countdown
    console.log('[App] Retry failed, backend still offline. Restarting countdown...');
    // Ensure modal stays visible
    showOfflineModal.value = true;
    // Restart the countdown timer in the modal
    if (offlineModalRef.value) {
      offlineModalRef.value.restartCountdown();
    }
  }
};

onMounted(() => {
  initializeApp();
  document.addEventListener('click', handleClickOutside);
  document.addEventListener('keydown', handleKeyboardShortcuts);
  
  // Setup triple offline detection system:
  
  // 1. WebSocket disconnection (IMMEDIATE - highest priority)
  //    Shows modal after 3 failed reconnection attempts (~7 seconds total)
  setWebSocketOfflineCallback(() => {
    console.log('[App] WebSocket offline detected');
    showOfflineModal.value = true;
  });
  
  setWebSocketOnlineCallback(() => {
    console.log('[App] WebSocket back online');
    showOfflineModal.value = false;
    markOnline();
  });
  
  // Handle new image events from mobile uploads
  setNewImageCallback((data) => {
    console.log('[App] New image from mobile:', data.image_id);
    // Reload images to show the new upload
    imageStore.loadSessionImages();
  });
  
  // 2. Axios interceptor (IMMEDIATE - for API errors during user actions)
  setOfflineCallback(() => {
    console.log('[App] Axios interceptor detected offline');
    showOfflineModal.value = true;
  });
  
  // 3. Health check service (PERIODIC - fallback, every 30 seconds)
  setHealthOfflineCallback(() => {
    console.log('[App] Health check detected offline');
    showOfflineModal.value = true;
  });
  
  setHealthOnlineCallback(() => {
    console.log('[App] Health check detected online');
    showOfflineModal.value = false;
    markOnline();
  });
  
  // Start WebSocket connection with session ID
  if (sessionId.value) {
    connectWebSocket(sessionId.value);
  }
  
  // Watch for session ID changes and reconnect WebSocket
  watch(sessionId, (newSessionId, oldSessionId) => {
    console.log('[App] Session ID changed:', { old: oldSessionId, new: newSessionId });
    
    // Disconnect old connection if session changed
    if (oldSessionId && oldSessionId !== newSessionId) {
      disconnectWebSocket();
    }
    
    // Connect with new session ID
    if (newSessionId) {
      connectWebSocket(newSessionId);
    }
  });
  
  // Start periodic health checks (every 30 seconds) as fallback
  startHealthCheck();
});

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside);
  document.removeEventListener('keydown', handleKeyboardShortcuts);
  
  // Stop health check polling when component unmounts
  stopHealthCheck();
  
  // Disconnect WebSocket
  disconnectWebSocket();
  
  // Clear QR code timers if active
  if (qrCodeTimerInterval) {
    clearInterval(qrCodeTimerInterval);
    qrCodeTimerInterval = null;
  }
  if (qrCodePollingInterval) {
    clearInterval(qrCodePollingInterval);
    qrCodePollingInterval = null;
  }
  if (qrCodeSuccessInterval) {
    clearInterval(qrCodeSuccessInterval);
    qrCodeSuccessInterval = null;
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
  padding: 0.8rem;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: padding 0.3s ease;
  overflow: visible;
  position: relative;
}

.app-header.compact {
  padding: 0.3rem 0.8rem;
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

.title-container {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.btn-info-icon {
  background: none;
  border: none;
  font-size: 1.3rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 50%;
  transition: all 0.2s ease;
  opacity: 0.7;
  line-height: 1;
}

.btn-info-icon:hover {
  opacity: 1;
  background-color: rgba(0, 0, 0, 0.05);
  transform: scale(1.1);
}

.header-right {
  flex-shrink: 0;
  margin-left: 2rem;
}

.app-header h1 {
  font-size: 2rem;
  margin-bottom: 0.4rem;
  transition: font-size 0.3s ease, margin 0.3s ease;
  cursor: help;
  position: relative;
  display: inline-block;
}

.app-header.compact h1 {
  font-size: 1.2rem;
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
  font-size: 0.88rem;
  opacity: 0.9;
}

.username-display {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.7rem;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
  margin-left: 0.5rem;
}

.user-icon {
  font-size: 0.9rem;
  line-height: 1;
}

.username-text {
  color: rgba(255, 255, 255, 0.95);
}

.image-stats {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.76rem;
  margin-top: 0.4rem;
}

.image-count {
  font-weight: 600;
}

.expiry-info {
  font-weight: 400;
  opacity: 0.8;
  font-size: 0.9em;
  cursor: help;
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
  padding: 0.48rem;
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
  font-size: 1rem;
  display: block;
}

.btn-header {
  padding: 0.4rem 0.56rem;
}

.btn-header .icon {
  font-size: 0.88rem;
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
  padding: 0.5rem 1rem;
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
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
  padding-top: 0.5rem;
  overflow: visible;
}

/* Adjust grid columns based on card size */
.image-gallery:has(.card-size-medium) {
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.25rem;
}

.image-gallery:has(.card-size-large) {
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 1.5rem;
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
  padding: 1.2rem;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.2rem;
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

.modal-close-btn {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: none;
  border: none;
  font-size: 2rem;
  color: #999;
  cursor: pointer;
  padding: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s ease;
  z-index: 10;
  line-height: 1;
}

.modal-close-btn:hover {
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
  margin: 0 0 0.4rem 0;
  font-size: 1rem;
  color: #333;
}

.section-description {
  margin: 0 0 1.5rem 0;
  color: #666;
  font-size: 0.95rem;
  line-height: 1.5;
}

.setting-description {
  margin: 0 0 1.5rem 0;
  color: #666;
  font-size: 0.95rem;
  line-height: 1.5;
}

.size-options {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.size-option {
  position: relative;
  display: block;
  padding: 1.25rem;
  background: white;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.size-option:hover {
  border-color: #bdbdbd;
  background: #fafafa;
}

.size-option.active {
  border-color: #4CAF50;
  background: #f1f8f4;
}

.size-option input[type="radio"] {
  display: none;
}

.option-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.option-icon {
  font-size: 2rem;
  line-height: 1;
}

.option-text {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.option-title {
  font-weight: 600;
  font-size: 1.05rem;
  color: #333;
}

.option-desc {
  font-size: 0.9rem;
  color: #666;
}

.size-option.active .option-title {
  color: #2e7d32;
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

.info-box-highlight {
  background-color: #fff8e1;
  border-left: 3px solid #ffa726;
}

.info-box-success {
  background-color: #e8f5e9;
  border-left: 3px solid #4caf50;
}

.info-box-highlight ul {
  margin-left: 1.2rem;
  margin-top: 0.5rem;
}

.info-box-highlight li {
  margin-bottom: 0.5rem;
  line-height: 1.5;
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

/* Selected Model Card in AI Settings (Clickable) */
.selected-model-card {
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  padding: 1.25rem;
  background-color: white;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  position: relative;
  margin-top: 1rem;
  transition: all 0.2s ease;
}

.selected-model-card.clickable {
  cursor: pointer;
}

.selected-model-card.clickable:hover:not(.disabled) {
  border-color: #2196F3;
  box-shadow: 0 4px 12px rgba(33, 150, 243, 0.15);
  transform: translateY(-2px);
}

.selected-model-card.clickable:hover:not(.disabled) .click-hint {
  opacity: 1;
}

.selected-model-card.disabled {
  opacity: 0.6;
  cursor: not-allowed;
  background-color: #f5f5f5;
}

.selected-model-card .click-hint {
  position: absolute;
  top: 1rem;
  right: 1rem;
  font-size: 1.5rem;
  opacity: 0;
  transition: opacity 0.2s ease;
}

/* Placeholder State */
.selected-model-card.placeholder {
  border: 2px dashed #ddd;
  background-color: #f8f9fa;
}

.selected-model-card.placeholder:hover:not(.disabled) {
  border-color: #2196F3;
  background-color: #f0f7ff;
}

.placeholder-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  text-align: center;
}

.placeholder-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.placeholder-title {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: #666;
}

.placeholder-content .placeholder-text {
  margin: 0;
  color: #999;
  font-size: 0.95rem;
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

/* Model Filters */
.model-filters {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  flex-wrap: nowrap;
}

.filter-search {
  flex: 1 1 auto;
  min-width: 200px;
  max-width: 400px;
}

.search-input {
  width: 100%;
  padding: 0.6rem 0.875rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.9rem;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.search-input:focus {
  outline: none;
  border-color: #2196F3;
  box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
}

.filter-toggle {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.toggle-switch {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  user-select: none;
}

.toggle-switch input[type="checkbox"] {
  position: absolute;
  opacity: 0;
}

.toggle-slider {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
  background-color: #ccc;
  border-radius: 24px;
  transition: background-color 0.3s ease;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  width: 18px;
  height: 18px;
  left: 3px;
  top: 3px;
  background-color: white;
  border-radius: 50%;
  transition: transform 0.3s ease;
}

.toggle-switch input[type="checkbox"]:checked + .toggle-slider {
  background-color: #4CAF50;
}

.toggle-switch input[type="checkbox"]:checked + .toggle-slider::before {
  transform: translateX(20px);
}

.toggle-label {
  font-size: 0.9rem;
  color: #333;
  font-weight: 500;
  white-space: nowrap;
}

.filter-tags {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  min-width: 200px;
}

.filter-label {
  font-size: 0.9rem;
  color: #666;
  font-weight: 500;
  white-space: nowrap;
}

.tag-filter-select {
  flex: 1;
  min-width: 150px;
  max-width: 250px;
  padding: 0.6rem 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.9rem;
  background-color: white;
  cursor: pointer;
  transition: border-color 0.2s ease;
}

.tag-filter-select:focus {
  outline: none;
  border-color: #2196F3;
}

/* Loading and Error States */
.models-loading,
.models-error,
.no-results {
  text-align: center;
  padding: 3rem 2rem;
  color: #666;
}

.loading-spinner {
  font-size: 3rem;
  display: block;
  margin-bottom: 1rem;
  animation: spin 2s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.models-error {
  color: #d32f2f;
}

.btn-retry {
  margin-top: 1rem;
  padding: 0.5rem 1.5rem;
  background-color: #2196F3;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background-color 0.2s ease;
}

.btn-retry:hover {
  background-color: #1976D2;
}

/* Models Section */
.models-section {
  margin-bottom: 2rem;
}

.section-header {
  margin: 0 0 1rem 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: #333;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.section-divider {
  margin: 2rem 0;
  padding: 0.75rem 0;
  border-top: 2px solid #e0e0e0;
  border-bottom: 2px solid #e0e0e0;
  text-align: center;
  font-weight: 600;
  color: #666;
  font-size: 0.95rem;
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
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.model-description.expanded {
  display: block;
  -webkit-line-clamp: unset;
}

.model-description-container {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.btn-toggle-description {
  background: none;
  border: none;
  color: #2196F3;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0.25rem 0;
  text-align: left;
  align-self: flex-start;
  transition: color 0.2s ease;
}

.btn-toggle-description:hover {
  color: #1976D2;
  text-decoration: underline;
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

.model-tag.tag-image-editing {
  background-color: #f3e5f5;
  color: #7b1fa2;
}

.model-specs {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.spec-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.75rem;
  background-color: #f0f0f0;
  border-radius: 6px;
  font-size: 0.8rem;
}

.spec-label {
  color: #666;
  font-weight: 500;
}

.spec-value {
  color: #333;
  font-weight: 700;
}

.model-footer {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid #e0e0e0;
  margin-top: auto;
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

  /* Model filters - stack on mobile */
  .model-filters {
    flex-direction: column;
    align-items: stretch;
    gap: 0.75rem;
  }

  .filter-search {
    flex: 1;
    min-width: 100%;
    max-width: 100%;
  }

  .filter-toggle {
    width: 100%;
    justify-content: center;
  }

  .filter-tags {
    width: 100%;
    min-width: 100%;
  }

  .tag-filter-select {
    max-width: 100%;
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

/* QR Code Styles */
.qr-code-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  background-color: #f5f5f5;
  border-radius: 8px;
  margin-top: 10px;
}

.qr-code-image {
  max-width: 300px;
  width: 100%;
  height: auto;
  border: 2px solid #ddd;
  border-radius: 8px;
  background-color: white;
  padding: 10px;
}

.qr-code-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
  color: #666;
}

.qr-code-loading .loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

.qr-code-error {
  text-align: center;
  padding: 20px;
  color: #d32f2f;
}

/* Pairing Success Styles */
.pairing-success-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
  text-align: center;
}

.success-icon {
  width: 80px;
  height: 80px;
  background-color: #10b981;
  color: white;
  font-size: 48px;
  font-weight: bold;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: successPop 0.5s ease-out;
}

@keyframes successPop {
  0% {
    transform: scale(0);
    opacity: 0;
  }
  50% {
    transform: scale(1.1);
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

/* Circular Countdown */
.circular-countdown {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 20px;
}

.countdown-svg {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.countdown-circle {
  transition: stroke-dashoffset 1s linear;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Addon Modal Styles */
.url-container {
  padding: 15px;
  background: #f9fafb;
  border-radius: 8px;
}

.url-display-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

.registration-url {
  flex: 1;
  font-size: 0.85em;
  word-break: break-all;
  color: #1f2937;
  background: transparent;
}

.btn-copy {
  padding: 8px 12px;
  background: #6366f1;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  transition: background 0.2s;
}

.btn-copy:hover {
  background: #4f46e5;
}

.addon-install-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  text-decoration: none;
  color: #1f2937;
  font-weight: 500;
  transition: all 0.2s;
  width: 100%;
  justify-content: center;
}

.addon-install-link:hover {
  background: #e5e7eb;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  text-decoration: none;
}

/* Current browser - highlighted */
.addon-install-link.current-browser {
  background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
  color: white;
  border-color: #4f46e5;
  cursor: pointer;
  font-size: 1.05em;
  padding: 14px 20px;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.addon-install-link.current-browser:hover {
  background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.4);
  text-decoration: none;
}

/* Other browsers */
.addon-install-link.other-browser {
  cursor: pointer;
  opacity: 1;
  background: white;
  font-size: 0.95em;
}

.addon-install-link.other-browser:hover {
  background: #f9fafb;
  text-decoration: none;
}

/* Disabled state */
.addon-install-link.disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

/* Browser-specific colors */
.addon-install-link.firefox {
  border-color: #ff9500;
}

.addon-install-link.firefox:hover {
  border-color: #ff7700;
}

.addon-install-link.chrome {
  border-color: #4285f4;
}

.addon-install-link.chrome:hover {
  border-color: #1a73e8;
}

.connected-device-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  margin-bottom: 8px;
}

.device-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.device-icon {
  font-size: 1.5em;
}

.device-details strong {
  color: #1f2937;
}

.btn-revoke {
  padding: 6px 12px;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  transition: background 0.2s;
}

.btn-revoke:hover {
  background: #dc2626;
}

.btn-revoke-confirm {
  padding: 6px 12px;
  background: #10b981;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  font-weight: 600;
  transition: background 0.2s;
}

.btn-revoke-confirm:hover {
  background: #059669;
}

.btn-revoke-cancel {
  padding: 6px 12px;
  background: #6b7280;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  transition: background 0.2s;
}

.btn-revoke-cancel:hover {
  background: #4b5563;
}

/* Browser addon details/summary styling */
details summary {
  padding: 8px 12px;
  background: #f9fafb;
  border-radius: 6px;
  transition: background 0.2s;
}

details summary:hover {
  background: #f3f4f6;
}

details[open] summary {
  margin-bottom: 10px;
  background: #f3f4f6;
}
</style>
