<template>
  <div class="chat-modal-overlay" @click="handleCloseClick">
    <div class="chat-modal" @click.stop>
      <button class="modal-close-btn" @click="$emit('close')">✕</button>
      
      <div class="chat-header">
        <div class="header-left">
          <h2>🤖 AI Chat</h2>
        </div>
        <div class="header-right">
          <button 
            v-if="messages.length > 0"
            @click="requestClearHistory" 
            class="btn-clear-history"
            :disabled="isLoading"
            title="Clear chat history"
          >
            🗑️ Clear History
          </button>
          <div class="model-info-container">
            <span class="model-label">Model:</span>
            <span class="model-name">{{ modelDisplayName }}</span>
          </div>
        </div>
      </div>
      
      <!-- Clear History Confirmation Popup -->
      <div v-if="showClearHistoryConfirm" class="clear-history-popup">
        <div class="clear-history-content">
          <span class="clear-history-text">⚠️ Clear all chat history and AI versions?</span>
          <div class="clear-history-actions">
            <button @click="confirmClearHistory" class="clear-history-btn clear-history-yes">
              ✓ Clear All
            </button>
            <button @click="cancelClearHistory" class="clear-history-btn clear-history-no">
              ✕ Cancel
            </button>
          </div>
        </div>
      </div>
      
      <div class="chat-body">
        <!-- Left Panel: Image Preview -->
        <div class="image-panel">
          <div class="image-preview-container">
            <img 
              v-if="selectedImageVersion"
              :src="selectedImageVersion.url" 
              :alt="image.original_filename"
              class="preview-image"
              :key="imageRefreshKey"
            />
            <div v-if="imageHistory.length > 1" class="version-badge">
              Version {{ selectedVersionIndex + 1 }} of {{ imageHistory.length }}
            </div>
          </div>
          
          <!-- Image History Thumbnails -->
          <div v-if="imageHistory.length > 1" class="image-history">
            <div class="history-header">
              <span class="history-title">📸 AI Generated Versions</span>
              <span class="history-count">{{ imageHistory.length }} version{{ imageHistory.length > 1 ? 's' : '' }}</span>
            </div>
            <div class="thumbnails-grid">
              <div 
                v-for="(version, index) in imageHistory" 
                :key="version.id"
                class="thumbnail-card"
                :class="{ 'selected': selectedVersionIndex === index }"
              >
                <!-- Delete Confirmation Popup -->
                <div v-if="versionToDelete === index" class="delete-popup" @click.stop>
                  <div class="delete-popup-content">
                    <span class="delete-popup-text">Remove?</span>
                    <div class="delete-popup-actions">
                      <button @click="confirmRemoveVersion(index)" class="delete-popup-btn delete-popup-confirm">
                        ✓
                      </button>
                      <button @click="cancelRemoveVersion" class="delete-popup-btn delete-popup-cancel">
                        ✕
                      </button>
                    </div>
                  </div>
                </div>
                
                <button 
                  v-if="index > 0"
                  @click="requestRemoveVersion(index)" 
                  class="thumbnail-remove"
                  title="Remove this version"
                >
                  ✕
                </button>
                <button 
                  @click="selectVersion(index)" 
                  class="thumbnail-select"
                  :class="{ 'is-selected': selectedVersionIndex === index }"
                  :title="selectedVersionIndex === index ? 'Currently selected' : 'Click to select this version'"
                >
                  <div class="select-indicator">
                    {{ selectedVersionIndex === index ? '✓' : '' }}
                  </div>
                </button>
                <img 
                  :src="version.url" 
                  :alt="`Version ${index + 1}`"
                  class="thumbnail-image"
                  @click="selectVersion(index)"
                />
                <div class="thumbnail-label">
                  {{ index === 0 ? 'Original' : `AI ${index}` }}
                </div>
              </div>
            </div>
          </div>
          
          <!-- Save/Close Actions -->
          <div class="image-actions">
            <!-- Close Confirmation Popup -->
            <div v-if="showCloseConfirm" class="close-confirm-popup">
              <div class="close-confirm-content">
                <span class="close-confirm-text">⚠️ Discard all AI versions?</span>
                <div class="close-confirm-actions">
                  <button @click="confirmClose" class="close-confirm-btn close-confirm-yes">
                    ✓ Yes
                  </button>
                  <button @click="cancelClose" class="close-confirm-btn close-confirm-no">
                    ✕ No
                  </button>
                </div>
              </div>
            </div>
            
            <button 
              @click="handleSave" 
              class="btn-save"
              :disabled="isSaving || selectedVersionIndex === 0"
            >
              {{ isSaving ? '⏳ Saving...' : '💾 Save & Close' }}
            </button>
            <button 
              @click="handleClose" 
              class="btn-close"
              :disabled="isSaving"
            >
              {{ imageHistory.length > 1 ? '✕ Close (Discard All)' : '✕ Close' }}
            </button>
          </div>
        </div>
        
        <!-- Right Panel: Chat Messages -->
        <div class="chat-panel">
          <div class="chat-messages" ref="messagesContainer">
            <div v-if="messages.length === 0" class="welcome-message">
              <span class="welcome-icon">💬</span>
              <h3>AI Image Manipulation</h3>
              <p>Ask me to modify your image:</p>
              <div class="example-prompts">
                <span class="prompt-chip">"Blur the license plate"</span>
                <span class="prompt-chip">"Circle the plant"</span>
                <span class="prompt-chip">"Add text 'Welcome'"</span>
                <span class="prompt-chip">"Remove the background"</span>
              </div>
            </div>
            
            <div 
              v-for="(message, index) in messages" 
              :key="index"
              class="message"
              :class="{ 'user-message': message.role === 'user', 'assistant-message': message.role === 'assistant' }"
            >
              <div class="message-icon">
                {{ message.role === 'user' ? '👤' : '🤖' }}
              </div>
              <div class="message-content">
                <div class="message-text">{{ message.content }}</div>
                
                <!-- Retry Button for failed prompts after model switch -->
                <div v-if="message.showRetryButton && message.retryPrompt" class="retry-prompt-container">
                  <button @click="retryLastPrompt" class="btn-retry-prompt">
                    🔄 Retry: "{{ message.retryPrompt.substring(0, 50) }}{{ message.retryPrompt.length > 50 ? '...' : '' }}"
                  </button>
                </div>
                
                <!-- Model Recommendations -->
                <div v-if="message.model_recommendations && message.model_recommendations.length > 0" class="model-recommendations">
                  <h4 class="recommendations-title">💡 Recommended Models:</h4>
                  <div 
                    v-for="(rec, idx) in message.model_recommendations" 
                    :key="idx"
                    class="model-rec-card"
                  >
                    <div class="model-rec-header">
                      <div class="model-rec-main">
                        <span class="model-rec-name">{{ rec.model_name }}</span>
                        <span class="model-rec-reason">{{ rec.reason }}</span>
                      </div>
                      <span class="model-rec-cost">${{ rec.cost_prompt.toFixed(2) }}/${{ rec.cost_completion.toFixed(2) }}</span>
                    </div>
                    
                    <!-- Collapsible capabilities -->
                    <div v-if="expandedRecommendations.has(`${message.timestamp}-${idx}`)" class="model-rec-capabilities">
                      <span 
                        v-for="(cap, capIdx) in rec.capabilities" 
                        :key="capIdx"
                        class="capability-tag"
                      >
                        ✓ {{ cap }}
                      </span>
                    </div>
                    
                    <div class="model-rec-actions">
                      <button 
                        @click="switchToModel(rec.model_id)" 
                        class="btn-switch-model"
                      >
                        Switch
                      </button>
                      <button 
                        @click="toggleCapabilities(`${message.timestamp}-${idx}`)" 
                        class="btn-toggle-caps"
                      >
                        {{ expandedRecommendations.has(`${message.timestamp}-${idx}`) ? 'Less' : 'More' }}
                      </button>
                      <button 
                        @click="showModelDetails(rec.model_id)" 
                        class="btn-model-details"
                      >
                        Details
                      </button>
                    </div>
                  </div>
                </div>
                
                <div v-if="message.operations && message.operations.length > 0" class="operations-info">
                  <span class="operations-label">Preview operations:</span>
                  <span 
                    v-for="(op, idx) in message.operations" 
                    :key="idx"
                    class="operation-tag"
                  >
                    {{ op.type }}
                  </span>
                </div>
                <div v-if="message.timestamp" class="message-time">
                  {{ formatTime(message.timestamp) }}
                </div>
              </div>
            </div>
            
            <div v-if="isLoading" class="message assistant-message loading">
              <div class="message-icon">🤖</div>
              <div class="message-content">
                <div class="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>
          
          <div class="chat-input-container">
            <div v-if="error" class="error-message">
              {{ error }}
            </div>
            <form @submit.prevent="sendMessage" class="chat-input-form">
              <textarea 
                v-model="inputMessage"
                placeholder="Ask AI to modify the image..."
                class="chat-input"
                :disabled="isLoading || !isConnected"
                ref="messageInput"
                rows="1"
                @input="autoExpandTextarea"
                @keydown.enter.exact.prevent="sendMessage"
              ></textarea>
              <button 
                type="submit"
                class="send-button"
                :disabled="!inputMessage.trim() || isLoading || !isConnected"
              >
                <span v-if="!isLoading">Send</span>
                <span v-else class="thinking-text">⏳ Thinking...</span>
              </button>
            </form>
            <div v-if="!isConnected" class="connection-warning">
              <span>⚠️</span>
              <span>Connect to OpenRouter and select a model in AI Settings to use chat</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue';
import { chatService } from '../services/chatService';

const props = defineProps({
  image: {
    type: Object,
    required: true
  },
  sessionId: {
    type: String,
    required: true
  },
  selectedModel: {
    type: String,
    default: null
  },
  isConnected: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['close', 'operationsApplied', 'switchModel', 'showModelDetails']);

// State
const messages = ref([]);
const inputMessage = ref('');
const isLoading = ref(false);
const error = ref(null);
const messagesContainer = ref(null);
const messageInput = ref(null);
const conversationId = ref(null);
const imageRefreshKey = ref(Date.now());
const isSaving = ref(false);
const pendingOperations = ref([]);
const expandedRecommendations = ref(new Set()); // Track which recommendations are expanded
const lastFailedPrompt = ref(null); // Track the last prompt that couldn't be executed

// Image History Management
const imageHistory = ref([]);
const selectedVersionIndex = ref(0);
const versionToDelete = ref(null); // Track which version is pending deletion
const showCloseConfirm = ref(false); // Show close confirmation popup
const showClearHistoryConfirm = ref(false); // Show clear history confirmation popup

// Session State Management - Save/Restore from localStorage
const getChatSessionKey = () => {
  return `chat_session_${props.image.id}`;
};

const saveChatSession = () => {
  try {
    const sessionData = {
      messages: messages.value,
      imageHistory: imageHistory.value,
      selectedVersionIndex: selectedVersionIndex.value,
      conversationId: conversationId.value,
      timestamp: Date.now()
    };
    localStorage.setItem(getChatSessionKey(), JSON.stringify(sessionData));
    console.log('💾 Chat session saved to localStorage');
  } catch (error) {
    console.error('Failed to save chat session:', error);
  }
};

const restoreChatSession = () => {
  try {
    const sessionKey = getChatSessionKey();
    const savedData = localStorage.getItem(sessionKey);
    
    if (savedData) {
      const sessionData = JSON.parse(savedData);
      
      // Check if session is recent (within last 24 hours)
      const sessionAge = Date.now() - sessionData.timestamp;
      const maxAge = 24 * 60 * 60 * 1000; // 24 hours
      
      if (sessionAge < maxAge) {
        messages.value = sessionData.messages || [];
        imageHistory.value = sessionData.imageHistory || [];
        selectedVersionIndex.value = sessionData.selectedVersionIndex || 0;
        conversationId.value = sessionData.conversationId || null;
        
        console.log('✅ Chat session restored from localStorage');
        console.log(`  - ${messages.value.length} messages restored`);
        console.log(`  - ${imageHistory.value.length} image versions restored`);
        return true;
      } else {
        // Session too old, clear it
        localStorage.removeItem(sessionKey);
        console.log('🗑️ Old chat session cleared');
      }
    }
  } catch (error) {
    console.error('Failed to restore chat session:', error);
  }
  return false;
};

const clearChatSession = () => {
  try {
    localStorage.removeItem(getChatSessionKey());
    console.log('🗑️ Chat session cleared from localStorage');
  } catch (error) {
    console.error('Failed to clear chat session:', error);
  }
};

// Initialize with the original image
const initializeImageHistory = () => {
  imageHistory.value = [{
    id: 'original',
    url: `${props.image.image_url}?t=${Date.now()}`,
    timestamp: new Date(),
    isOriginal: true
  }];
  selectedVersionIndex.value = 0;
};

// Get selected image version
const selectedImageVersion = computed(() => {
  if (imageHistory.value.length === 0) {
    // Fallback to props.image if history not initialized yet
    return {
      id: 'original',
      url: `${props.image.image_url}?t=${Date.now()}`,
      isOriginal: true
    };
  }
  return imageHistory.value[selectedVersionIndex.value] || imageHistory.value[0];
});

// Select a version from history
const selectVersion = (index) => {
  if (index >= 0 && index < imageHistory.value.length) {
    selectedVersionIndex.value = index;
    imageRefreshKey.value = Date.now();
  }
};

// Request to remove a version (shows confirmation)
const requestRemoveVersion = (index) => {
  if (index === 0) {
    // Cannot remove original - show message in chat
    messages.value.push({
      role: 'assistant',
      content: '⚠️ Cannot remove the original image.',
      timestamp: new Date()
    });
    return;
  }
  
  versionToDelete.value = index;
};

// Confirm version removal
const confirmRemoveVersion = (index) => {
  imageHistory.value.splice(index, 1);
  
  // Adjust selected index if needed
  if (selectedVersionIndex.value >= imageHistory.value.length) {
    selectedVersionIndex.value = imageHistory.value.length - 1;
  } else if (selectedVersionIndex.value >= index) {
    selectedVersionIndex.value = Math.max(0, selectedVersionIndex.value - 1);
  }
  
  versionToDelete.value = null;
  imageRefreshKey.value = Date.now();
  saveChatSession(); // Save after removing version
};

// Cancel version removal
const cancelRemoveVersion = () => {
  versionToDelete.value = null;
};

// Add a new version to history
const addImageVersion = (imageUrl, historySequence = null) => {
  const newVersion = {
    id: `version-${Date.now()}`,
    url: `${imageUrl}&t=${Date.now()}`,
    timestamp: new Date(),
    isOriginal: false,
    historySequence: historySequence  // Track the backend history sequence number
  };
  
  imageHistory.value.push(newVersion);
  selectedVersionIndex.value = imageHistory.value.length - 1; // Auto-select new version
  imageRefreshKey.value = Date.now();
  saveChatSession(); // Save after adding version
};

// Model display name
const modelDisplayName = computed(() => {
  if (!props.selectedModel) return 'No model selected';
  
  // Extract readable name from model ID
  // e.g., "google/gemini-2.0-flash-exp:free" -> "Gemini 2.0 Flash"
  const modelId = props.selectedModel;
  const parts = modelId.split('/');
  const modelName = parts.length > 1 ? parts[1] : modelId;
  const cleanName = modelName.split(':')[0]; // Remove :free suffix
  
  // Capitalize and format
  return cleanName
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
});

// Current image URL with cache busting
const currentImageUrl = computed(() => {
  return `${props.image.image_url}?t=${imageRefreshKey.value}`;
});

// Format file size
const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
};

// Format timestamp
const formatTime = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

// Send message
const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value || !props.isConnected) return;
  
  const userMessage = inputMessage.value.trim();
  inputMessage.value = '';
  error.value = null;
  
  // Reset textarea height after sending
  if (messageInput.value) {
    messageInput.value.style.height = 'auto';
    messageInput.value.rows = 1;
  }
  
  // Add user message to UI
  messages.value.push({
    role: 'user',
    content: userMessage,
    timestamp: new Date()
  });
  
  await scrollToBottom();
  isLoading.value = true;
  
  // Scroll again after loading indicator appears
  await nextTick();
  await scrollToBottom();
  
  try {
    // Debug logging for model switching
    console.log('🔍 ChatInterface.sendMessage() - Debug Info:');
    console.log('  - props.selectedModel:', props.selectedModel);
    console.log('  - conversationId:', conversationId.value);
    console.log('  - userMessage:', userMessage.substring(0, 50));
    
    // Send to API
    const response = await chatService.sendMessage({
      message: userMessage,
      imageId: props.image.id,
      conversationId: conversationId.value,
      model: props.selectedModel
    });
    
    console.log('  - Response received, conversation_id:', response.conversation_id);
    
    // Store conversation ID
    if (!conversationId.value) {
      conversationId.value = response.conversation_id;
    }
    
    // Add assistant response to UI
    messages.value.push({
      role: 'assistant',
      content: response.response,
      operations: response.operations || [],
      model_recommendations: response.model_recommendations || [],
      timestamp: new Date()
    });
    
    // If there are model recommendations, save the failed prompt for retry
    if (response.model_recommendations && response.model_recommendations.length > 0) {
      lastFailedPrompt.value = userMessage;
    }
    
    // Handle image updates
    if (response.image_updated) {
      // Add new version to history
      if (response.new_image_url) {
        addImageVersion(response.new_image_url, response.history_sequence);
      } else {
        // Fallback: just refresh current image
        imageRefreshKey.value = Date.now();
      }
      
      // If there are operations (JSON-based edits), mark as having unsaved changes
      if (response.operations && response.operations.length > 0) {
        pendingOperations.value = response.operations;
      }
    }
    
    await scrollToBottom();
    
    // Save session state after each message
    saveChatSession();
  } catch (err) {
    console.error('Failed to send message:', err);
    error.value = err.message || 'Failed to send message. Please try again.';
    await scrollToBottom(); // Scroll to show error
  } finally {
    isLoading.value = false;
    
    // Refocus input after response
    await nextTick();
    if (messageInput.value) {
      messageInput.value.focus();
    }
  }
};

// Auto-expand textarea up to 5 lines
const autoExpandTextarea = () => {
  const textarea = messageInput.value;
  if (!textarea) return;
  
  // Reset height to auto to get the correct scrollHeight
  textarea.style.height = 'auto';
  
  // Calculate line height (approximately 24px per line with padding)
  const lineHeight = 24;
  const maxLines = 5;
  const maxHeight = lineHeight * maxLines;
  
  // Set height based on content, but cap at max lines
  const newHeight = Math.min(textarea.scrollHeight, maxHeight);
  textarea.style.height = newHeight + 'px';
};

// Handle Save: Apply selected version and close
const handleSave = async () => {
  if (selectedVersionIndex.value === 0) {
    // Original selected, just close
    clearChatSession(); // Clear session when closing
    emit('close');
    return;
  }
  
  isSaving.value = true;
  try {
    // Get the selected version
    const selectedVersion = imageHistory.value[selectedVersionIndex.value];
    
    // If the selected version has a historySequence, restore it
    if (selectedVersion.historySequence) {
      const response = await fetch(`/api/v1/history/${props.image.id}/restore`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sequence: selectedVersion.historySequence
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to restore selected version');
      }
      
      const data = await response.json();
      console.log('Restored to sequence:', data);
    }
    
    // Emit success for parent to refresh
    emit('operationsApplied', []);
    
    // Show success message
    messages.value.push({
      role: 'assistant',
      content: '✓ Image saved successfully!',
      timestamp: new Date()
    });
    
    await new Promise(resolve => setTimeout(resolve, 500)); // Brief delay to show message
    clearChatSession(); // Clear session after successful save
    emit('close');
  } catch (err) {
    console.error('Failed to save image:', err);
    error.value = 'Failed to save image. Please try again.';
  } finally {
    isSaving.value = false;
  }
};

// Handle Close: Confirm if there are AI-generated versions
const handleClose = () => {
  if (imageHistory.value.length > 1) {
    showCloseConfirm.value = true;
  } else {
    clearChatSession(); // Clear session when closing without changes
    emit('close');
  }
};

// Confirm close and discard all AI versions
const confirmClose = () => {
  showCloseConfirm.value = false;
  clearChatSession(); // Clear session when discarding changes
  emit('close');
};

// Cancel close
const cancelClose = () => {
  showCloseConfirm.value = false;
};

// Request to clear history (shows confirmation)
const requestClearHistory = () => {
  showClearHistoryConfirm.value = true;
};

// Confirm clear history
const confirmClearHistory = () => {
  // Clear messages
  messages.value = [];
  conversationId.value = null;
  lastFailedPrompt.value = null;
  error.value = null;
  
  // Reset image history to original only
  initializeImageHistory();
  
  // Clear session storage
  clearChatSession();
  
  // Close confirmation popup
  showClearHistoryConfirm.value = false;
  
  // Focus input
  nextTick(() => {
    if (messageInput.value) {
      messageInput.value.focus();
    }
  });
};

// Cancel clear history
const cancelClearHistory = () => {
  showClearHistoryConfirm.value = false;
};

// Scroll to bottom of messages
const scrollToBottom = async () => {
  await nextTick();
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

// Handle close click
const handleCloseClick = () => {
  handleClose();
};

// Switch to recommended model
const switchToModel = (modelId) => {
  emit('switchModel', modelId);
  // Don't add message here - the watch on selectedModel will handle it
};

// Retry the last failed prompt
const retryLastPrompt = async () => {
  if (!lastFailedPrompt.value) return;
  
  const promptToRetry = lastFailedPrompt.value;
  lastFailedPrompt.value = null; // Clear it so we don't retry again
  
  // Set the input and send the message
  inputMessage.value = promptToRetry;
  await sendMessage();
};

// Show model details
const showModelDetails = (modelId) => {
  emit('showModelDetails', modelId);
};

// Toggle capabilities display
const toggleCapabilities = (key) => {
  if (expandedRecommendations.value.has(key)) {
    expandedRecommendations.value.delete(key);
  } else {
    expandedRecommendations.value.add(key);
  }
};

// Focus input on mount and initialize image history
onMounted(() => {
  // Try to restore session first
  const restored = restoreChatSession();
  
  // If no session restored, initialize fresh
  if (!restored) {
    initializeImageHistory();
  }
  
  if (messageInput.value) {
    messageInput.value.focus();
  }
  
  // Scroll to bottom if messages were restored
  if (messages.value.length > 0) {
    nextTick(() => scrollToBottom());
  }
});

// Watch for selectedModel changes
watch(() => props.selectedModel, (newModel, oldModel) => {
  if (oldModel && newModel && newModel !== oldModel) {
    // Model changed - show notification in chat with retry option
    const baseMessage = `🔄 Model switched to ${modelDisplayName.value}. You can now use features specific to this model!`;
    
    if (lastFailedPrompt.value) {
      messages.value.push({
        role: 'assistant',
        content: baseMessage,
        timestamp: new Date(),
        showRetryButton: true,
        retryPrompt: lastFailedPrompt.value
      });
    } else {
      messages.value.push({
        role: 'assistant',
        content: baseMessage,
        timestamp: new Date()
      });
    }
    scrollToBottom();
  }
});

// Watch for new messages and scroll
watch(() => messages.value.length, () => {
  scrollToBottom();
});
</script>

<style scoped>
.chat-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  backdrop-filter: blur(3px);
  animation: fadeIn 0.2s ease;
}

.chat-modal {
  background-color: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  width: 90vw;
  max-width: 1400px;
  height: 85vh;
  max-height: 900px;
  display: flex;
  flex-direction: column;
  position: relative;
  animation: slideUp 0.3s ease;
}

.modal-close-btn {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: none;
  border: none;
  font-size: 1.75rem;
  color: #666;
  cursor: pointer;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.2s ease;
  z-index: 10;
  margin-left: 3rem;
}

.modal-close-btn:hover {
  color: #333;
  background-color: #f5f5f5;
}

.chat-header {
  padding: 0.65rem 1.5rem;
  border-bottom: 1px solid #e0e0e0;
  background-color: #fafafa;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left h2 {
  margin: 0;
  font-size: 1.1rem;
  color: #333;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding-right: 3rem;
}

.btn-clear-history {
  padding: 0.35rem 0.65rem;
  background-color: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  font-size: 0.7rem;
  font-weight: 600;
  color: #666;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.btn-clear-history:hover:not(:disabled) {
  background-color: #f44336;
  color: white;
  border-color: #f44336;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(244, 67, 54, 0.3);
}

.btn-clear-history:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Clear History Confirmation Popup */
.clear-history-popup {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 10001;
  animation: popupZoom 0.2s ease;
}

@keyframes popupZoom {
  from {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.9);
  }
  to {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}

.clear-history-content {
  background: white;
  border: 2px solid #ff9800;
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: center;
  min-width: 280px;
  max-width: 400px;
}

.clear-history-text {
  font-size: 0.95rem;
  font-weight: 600;
  color: #f57c00;
  text-align: center;
  line-height: 1.4;
}

.clear-history-actions {
  display: flex;
  gap: 0.75rem;
  width: 100%;
}

.clear-history-btn {
  flex: 1;
  padding: 0.6rem 1rem;
  border-radius: 6px;
  border: none;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.3rem;
}

.clear-history-yes {
  background-color: #f44336;
  color: white;
}

.clear-history-yes:hover {
  background-color: #d32f2f;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(244, 67, 54, 0.4);
}

.clear-history-no {
  background-color: #4CAF50;
  color: white;
}

.clear-history-no:hover {
  background-color: #45a049;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
}

.model-info-container {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  background-color: #f3e5f5;
  padding: 0.35rem 0.75rem;
  border-radius: 16px;
  border: 1.5px solid #e1bee7;
}

.model-label {
  font-size: 0.65rem;
  color: #7b1fa2;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.model-name {
  color: #9C27B0;
  font-size: 0.75rem;
  font-weight: 600;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Legacy class for backwards compatibility */
.model-info {
  margin: 0;
  color: #9C27B0;
  font-size: 0.85rem;
  font-weight: 600;
  background-color: #f3e5f5;
  padding: 0.5rem 1rem;
  border-radius: 20px;
}

.chat-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

/* Left Panel - Image Preview */
.image-panel {
  width: 50%;
  min-width: 400px;
  max-width: 650px;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  background-color: #fafafa;
}

.image-preview-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2.5rem;
  position: relative;
  overflow: hidden;
  background-color: #f5f5f5;
}

.preview-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.unsaved-badge {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background-color: #ff9800;
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(255, 152, 0, 0.3);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.image-actions {
  padding: 1.5rem 2rem;
  display: flex;
  gap: 1rem;
  background-color: white;
  border-top: 1px solid #e0e0e0;
  position: relative;
}

/* Close Confirmation Popup */
.close-confirm-popup {
  position: absolute;
  bottom: calc(100% + 0.5rem);
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  animation: popupSlideUp 0.2s ease;
}

@keyframes popupSlideUp {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(5px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

.close-confirm-content {
  background: white;
  border: 2px solid #ff9800;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  white-space: nowrap;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  align-items: center;
  min-width: 200px;
}

.close-confirm-text {
  font-size: 0.85rem;
  font-weight: 600;
  color: #f57c00;
  text-align: center;
}

.close-confirm-actions {
  display: flex;
  gap: 0.5rem;
  width: 100%;
}

.close-confirm-btn {
  flex: 1;
  padding: 0.4rem 0.75rem;
  border-radius: 4px;
  border: none;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
}

.close-confirm-yes {
  background-color: #f44336;
  color: white;
}

.close-confirm-yes:hover {
  background-color: #d32f2f;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(244, 67, 54, 0.3);
}

.close-confirm-no {
  background-color: #4CAF50;
  color: white;
}

.close-confirm-no:hover {
  background-color: #45a049;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
}

/* Image History Styles */
.image-history {
  padding: 1rem 1.5rem;
  background-color: white;
  border-top: 1px solid #e0e0e0;
  max-height: 200px;
  overflow-y: auto;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #e0e0e0;
}

.history-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: #333;
}

.history-count {
  font-size: 0.75rem;
  color: #666;
  background-color: #f5f5f5;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
}

.thumbnails-grid {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.thumbnail-card {
  position: relative;
  width: 80px;
  height: 80px;
  border-radius: 8px;
  overflow: visible; /* Changed from hidden to allow popup overflow */
  border: 2px solid #ddd;
  background-color: #f9f9f9;
  transition: all 0.2s ease;
  cursor: pointer;
}

.thumbnail-card.selected {
  border-color: #4CAF50;
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
}

.thumbnail-card:hover {
  border-color: #999;
  transform: scale(1.05);
}

/* Delete Confirmation Popup for Thumbnails */
.delete-popup {
  position: absolute;
  top: -45px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  animation: popupSlideDown 0.2s ease;
}

@keyframes popupSlideDown {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-5px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

.delete-popup-content {
  background: white;
  border: 2px solid #f44336;
  border-radius: 6px;
  padding: 0.4rem 0.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  white-space: nowrap;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  align-items: center;
}

.delete-popup-text {
  font-size: 0.7rem;
  font-weight: 600;
  color: #d32f2f;
}

.delete-popup-actions {
  display: flex;
  gap: 0.3rem;
}

.delete-popup-btn {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: none;
  font-size: 0.75rem;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.delete-popup-confirm {
  background-color: #f44336;
  color: white;
}

.delete-popup-confirm:hover {
  background-color: #d32f2f;
  transform: scale(1.05);
}

.delete-popup-cancel {
  background-color: #e0e0e0;
  color: #666;
}

.delete-popup-cancel:hover {
  background-color: #bdbdbd;
  transform: scale(1.05);
}

.thumbnail-remove {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: rgba(244, 67, 54, 0.9);
  color: white;
  border: none;
  font-size: 0.7rem;
  cursor: pointer;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  padding: 0;
  line-height: 1;
}

.thumbnail-remove:hover {
  background-color: #f44336;
  transform: scale(1.1);
}

.thumbnail-select {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.9);
  color: #666;
  border: 2px solid #ddd;
  font-size: 0.7rem;
  cursor: pointer;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  padding: 0;
}

.thumbnail-select.is-selected {
  background-color: #4CAF50;
  border-color: #4CAF50;
  color: white;
}

.thumbnail-select:hover {
  border-color: #4CAF50;
  transform: scale(1.1);
}

.select-indicator {
  font-weight: bold;
  font-size: 0.85rem;
}

.thumbnail-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.thumbnail-label {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  font-size: 0.65rem;
  padding: 0.25rem;
  text-align: center;
  font-weight: 500;
}

.version-badge {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background-color: rgba(76, 175, 80, 0.95);
  color: white;
  padding: 0.4rem 0.8rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
}

.btn-save,
.btn-close {
  flex: 1;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-save {
  background-color: #4CAF50;
  color: white;
}

.btn-save:hover:not(:disabled) {
  background-color: #45a049;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(76, 175, 80, 0.3);
}

.btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-close {
  background-color: #757575;
  color: white;
}

.btn-close:hover:not(:disabled) {
  background-color: #616161;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(97, 97, 97, 0.3);
}

.btn-close:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Right Panel - Chat */
.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.welcome-message {
  text-align: center;
  padding: 2rem 1.5rem;
  color: #666;
}

.welcome-icon {
  font-size: 2.5rem;
  display: block;
  margin-bottom: 0.75rem;
}

.welcome-message h3 {
  margin: 0 0 0.5rem 0;
  color: #333;
  font-size: 1.05rem;
}

.welcome-message p {
  margin: 0 0 1rem 0;
  font-size: 0.85rem;
}

.example-prompts {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: center;
  max-width: 500px;
  margin: 0 auto;
}

.prompt-chip {
  background-color: #f0f0f0;
  color: #555;
  padding: 0.35rem 0.8rem;
  border-radius: 16px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid #e0e0e0;
}

.message {
  display: flex;
  gap: 0.75rem;
  animation: messageSlideIn 0.3s ease;
}

.message-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  flex-shrink: 0;
}

.user-message .message-icon {
  background-color: #2196F3;
}

.assistant-message .message-icon {
  background-color: #9C27B0;
}

.message-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.message-text {
  padding: 0.5rem 0.75rem;
  border-radius: 10px;
  font-size: 0.8rem;
  line-height: 1.4;
  max-width: 85%;
}

.user-message .message-text {
  background-color: #e3f2fd;
  color: #1565c0;
  align-self: flex-end;
}

.assistant-message .message-text {
  background-color: #f5f5f5;
  color: #333;
}

.operations-info {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  align-items: center;
  font-size: 0.7rem;
}

.operations-label {
  color: #666;
  font-weight: 500;
  font-size: 0.7rem;
}

.operation-tag {
  background-color: #9C27B0;
  color: white;
  padding: 0.15rem 0.5rem;
  border-radius: 10px;
  font-size: 0.7rem;
  font-weight: 600;
}

/* Retry Prompt Styles */
.retry-prompt-container {
  margin-top: 0.5rem;
}

.btn-retry-prompt {
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #4caf50 0%, #66bb6a 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(76, 175, 80, 0.2);
}

.btn-retry-prompt:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(76, 175, 80, 0.3);
  background: linear-gradient(135deg, #45a049 0%, #5cb85c 100%);
}

/* Model Recommendations Styles */
.model-recommendations {
  margin-top: 0.75rem;
  padding: 0.75rem;
  background-color: #f8f9fa;
  border-radius: 6px;
  border-left: 3px solid #7b1fa2;
}

.recommendations-title {
  font-size: 0.8rem;
  font-weight: 600;
  color: #333;
  margin: 0 0 0.6rem 0;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.model-rec-card {
  background-color: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 0.65rem;
  margin-bottom: 0.5rem;
  transition: all 0.2s ease;
}

.model-rec-card:last-child {
  margin-bottom: 0;
}

.model-rec-card:hover {
  border-color: #7b1fa2;
  box-shadow: 0 1px 4px rgba(123, 31, 162, 0.1);
}

.model-rec-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.4rem;
  gap: 0.5rem;
}

.model-rec-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.model-rec-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: #7b1fa2;
  line-height: 1.2;
}

.model-rec-cost {
  font-size: 0.65rem;
  color: #666;
  background-color: #f5f5f5;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-family: monospace;
  white-space: nowrap;
  align-self: flex-start;
}

.model-rec-reason {
  font-size: 0.7rem;
  color: #555;
  font-style: italic;
  line-height: 1.3;
}

.model-rec-capabilities {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin: 0.5rem 0 0.4rem 0;
  padding-top: 0.5rem;
  border-top: 1px solid #f0f0f0;
}

.capability-tag {
  font-size: 0.65rem;
  color: #4caf50;
  background-color: #e8f5e9;
  padding: 0.2rem 0.45rem;
  border-radius: 10px;
  font-weight: 500;
  line-height: 1.2;
}

.model-rec-actions {
  display: flex;
  gap: 0.4rem;
  margin-top: 0.5rem;
}

.btn-switch-model {
  flex: 1;
  padding: 0.45rem 0.75rem;
  background: linear-gradient(135deg, #7b1fa2 0%, #9c27b0 100%);
  color: white;
  border: none;
  border-radius: 5px;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-switch-model:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(123, 31, 162, 0.3);
}

.btn-toggle-caps {
  padding: 0.45rem 0.65rem;
  background-color: white;
  color: #666;
  border: 1.5px solid #e0e0e0;
  border-radius: 5px;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 50px;
}

.btn-toggle-caps:hover {
  background-color: #f5f5f5;
  border-color: #ccc;
}

.btn-model-details {
  padding: 0.45rem 0.65rem;
  background-color: white;
  color: #7b1fa2;
  border: 1.5px solid #7b1fa2;
  border-radius: 5px;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 60px;
}

.btn-model-details:hover {
  background-color: #f3e5f5;
}

.message-time {
  font-size: 0.7rem;
  color: #999;
  margin-top: 0.25rem;
}

.typing-indicator {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background-color: #f5f5f5;
  border-radius: 12px;
  max-width: 80px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #999;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.7; }
  30% { transform: translateY(-10px); opacity: 1; }
}

.chat-input-container {
  border-top: 1px solid #e0e0e0;
  padding: 1.5rem;
  background-color: white;
}

.error-message {
  background-color: #ffebee;
  color: #c62828;
  padding: 0.65rem 0.9rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.85rem;
  border-left: 3px solid #f44336;
}

.chat-input-form {
  display: flex;
  gap: 1rem;
}

.chat-input {
  flex: 1;
  padding: 0.65rem 0.9rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 0.9rem;
  font-family: inherit;
  line-height: 1.5;
  resize: none;
  overflow-y: auto;
  min-height: 42px;
  max-height: 120px; /* 5 lines * 24px */
  transition: border-color 0.2s ease, height 0.1s ease;
}

.chat-input:focus {
  outline: none;
  border-color: #9C27B0;
}

.chat-input:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}

.send-button {
  padding: 0.65rem 1.75rem;
  background-color: #9C27B0;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.send-button:hover:not(:disabled) {
  background-color: #7B1FA2;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(156, 39, 176, 0.3);
}

.send-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.thinking-text {
  font-size: 0.85rem;
  animation: pulse 1.5s ease-in-out infinite;
}

.connection-warning {
  margin-top: 1rem;
  padding: 0.65rem 0.9rem;
  background-color: #fff3e0;
  border-left: 3px solid #ff9800;
  border-radius: 6px;
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-size: 0.85rem;
  color: #e65100;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes messageSlideIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* Responsive */
@media (max-width: 1024px) {
  .chat-modal {
    width: 95vw;
    height: 90vh;
  }
  
  .image-panel {
    width: 45%;
    min-width: 320px;
  }
}

@media (max-width: 768px) {
  .chat-body {
    flex-direction: column;
  }
  
  .image-panel {
    width: 100%;
    max-width: none;
    height: 40%;
    border-right: none;
    border-bottom: 1px solid #e0e0e0;
  }
  
  .image-preview-container {
    padding: 1rem;
  }
  
  .chat-panel {
    height: 60%;
  }
  
  .chat-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
  
  .header-right {
    width: 100%;
  }
  
  .model-info {
    font-size: 0.8rem;
    padding: 0.4rem 0.8rem;
  }
}
</style>
