<template>
  <div class="chat-modal-overlay" @click="handleCloseClick">
    <div class="chat-modal" @click.stop>
      <button class="modal-close-btn" @click="$emit('close')">✕</button>
      
      <div class="chat-header">
        <div class="header-info">
          <h2>🤖 AI Chat</h2>
          <div class="header-meta">
            <p class="image-name">{{ image.original_filename }}</p>
            <p class="model-info">Model: {{ modelDisplayName }}</p>
          </div>
        </div>
      </div>
      
      <div class="chat-body">
        <!-- Left Panel: Image Preview -->
        <div class="image-panel">
          <div class="image-preview-container">
            <img 
              :src="currentImageUrl" 
              :alt="image.original_filename"
              class="preview-image"
              :key="imageRefreshKey"
            />
            <div v-if="hasUnsavedChanges" class="unsaved-badge">
              ⚠️ Modified (unsaved)
            </div>
          </div>
          <div class="image-info">
            <div class="info-row">
              <span class="label">Dimensions:</span>
              <span class="value">{{ image.width }} × {{ image.height }}</span>
            </div>
            <div class="info-row">
              <span class="label">Size:</span>
              <span class="value">{{ formatSize(image.current_size) }}</span>
            </div>
          </div>
          <div class="image-actions">
            <button 
              v-if="hasUnsavedChanges"
              @click="saveChanges" 
              class="btn-save"
              :disabled="isSaving"
            >
              {{ isSaving ? '⏳ Saving...' : '✓ Save Changes' }}
            </button>
            <button 
              v-if="hasUnsavedChanges"
              @click="discardChanges" 
              class="btn-discard"
              :disabled="isSaving"
            >
              ✕ Discard
            </button>
            <p v-if="!hasUnsavedChanges" class="no-changes-text">
              No unsaved changes
            </p>
          </div>
        </div>
        
        <!-- Right Panel: Chat Messages -->
        <div class="chat-panel">
          <div class="chat-messages" ref="messagesContainer">
            <div v-if="messages.length === 0" class="welcome-message">
              <span class="welcome-icon">💬</span>
              <h3>AI Image Manipulation</h3>
              <p>Ask me to modify your image! For example:</p>
              <ul>
                <li>"Make it brighter"</li>
                <li>"Add more contrast and saturation"</li>
                <li>"Rotate it 90 degrees"</li>
                <li>"Make it grayscale"</li>
              </ul>
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
              <input 
                v-model="inputMessage"
                type="text"
                placeholder="Ask AI to modify the image..."
                class="chat-input"
                :disabled="isLoading || !isConnected"
                ref="messageInput"
              />
              <button 
                type="submit"
                class="send-button"
                :disabled="!inputMessage.trim() || isLoading || !isConnected"
              >
                <span v-if="!isLoading">Send</span>
                <span v-else>...</span>
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

const emit = defineEmits(['close', 'operationsApplied']);

// State
const messages = ref([]);
const inputMessage = ref('');
const isLoading = ref(false);
const error = ref(null);
const messagesContainer = ref(null);
const messageInput = ref(null);
const conversationId = ref(null);
const imageRefreshKey = ref(Date.now());
const hasUnsavedChanges = ref(false);
const isSaving = ref(false);
const pendingOperations = ref([]);

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
  
  // Add user message to UI
  messages.value.push({
    role: 'user',
    content: userMessage,
    timestamp: new Date()
  });
  
  await scrollToBottom();
  isLoading.value = true;
  
  try {
    // Send to API
    const response = await chatService.sendMessage({
      message: userMessage,
      imageId: props.image.id,
      conversationId: conversationId.value,
      model: props.selectedModel
    });
    
    // Store conversation ID
    if (!conversationId.value) {
      conversationId.value = response.conversation_id;
    }
    
    // Add assistant response to UI
    messages.value.push({
      role: 'assistant',
      content: response.response,
      operations: response.operations || [],
      timestamp: new Date()
    });
    
    // If there are operations, mark as having unsaved changes
    if (response.operations && response.operations.length > 0) {
      hasUnsavedChanges.value = true;
      pendingOperations.value = response.operations;
      // Refresh the image preview to show the modifications
      imageRefreshKey.value = Date.now();
    }
    
    await scrollToBottom();
  } catch (err) {
    console.error('Failed to send message:', err);
    error.value = err.message || 'Failed to send message. Please try again.';
  } finally {
    isLoading.value = false;
  }
};

// Save changes to the actual image
const saveChanges = async () => {
  isSaving.value = true;
  try {
    // The operations have already been applied by the backend
    // Just need to confirm them
    hasUnsavedChanges.value = false;
    emit('operationsApplied', pendingOperations.value);
    pendingOperations.value = [];
    
    // Show success message
    messages.value.push({
      role: 'assistant',
      content: '✓ Changes saved successfully!',
      timestamp: new Date()
    });
  } catch (err) {
    console.error('Failed to save changes:', err);
    error.value = 'Failed to save changes. Please try again.';
  } finally {
    isSaving.value = false;
  }
};

// Discard changes and revert to original
const discardChanges = async () => {
  // TODO: Implement backend API to revert changes
  // For now, just clear the flag and refresh
  hasUnsavedChanges.value = false;
  pendingOperations.value = [];
  imageRefreshKey.value = Date.now();
  
  messages.value.push({
    role: 'assistant',
    content: '✕ Changes discarded.',
    timestamp: new Date()
  });
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
  if (hasUnsavedChanges.value) {
    if (confirm('You have unsaved changes. Are you sure you want to close?')) {
      emit('close');
    }
  } else {
    emit('close');
  }
};

// Focus input on mount
onMounted(() => {
  if (messageInput.value) {
    messageInput.value.focus();
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
}

.modal-close-btn:hover {
  color: #333;
  background-color: #f5f5f5;
}

.chat-header {
  padding: 1.5rem 2rem;
  border-bottom: 1px solid #e0e0e0;
  background-color: #fafafa;
}

.header-info h2 {
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
  color: #333;
}

.header-meta {
  display: flex;
  gap: 1.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.image-name {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
  font-weight: 500;
}

.model-info {
  margin: 0;
  color: #9C27B0;
  font-size: 0.85rem;
  font-weight: 600;
  background-color: #f3e5f5;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
}

.chat-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

/* Left Panel - Image Preview */
.image-panel {
  width: 40%;
  min-width: 350px;
  max-width: 500px;
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
  padding: 2rem;
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

.image-info {
  padding: 1rem 2rem;
  border-bottom: 1px solid #e0e0e0;
  background-color: white;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 0.4rem 0;
  font-size: 0.9rem;
}

.info-row .label {
  color: #666;
  font-weight: 500;
}

.info-row .value {
  color: #333;
  font-weight: 600;
}

.image-actions {
  padding: 1.5rem 2rem;
  display: flex;
  gap: 1rem;
  background-color: white;
}

.btn-save,
.btn-discard {
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

.btn-discard {
  background-color: #f44336;
  color: white;
}

.btn-discard:hover:not(:disabled) {
  background-color: #da190b;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(244, 67, 54, 0.3);
}

.btn-discard:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.no-changes-text {
  margin: 0;
  color: #999;
  font-size: 0.9rem;
  text-align: center;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
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
  padding: 3rem 2rem;
  color: #666;
}

.welcome-icon {
  font-size: 3rem;
  display: block;
  margin-bottom: 1rem;
}

.welcome-message h3 {
  margin: 0 0 1rem 0;
  color: #333;
  font-size: 1.25rem;
}

.welcome-message p {
  margin: 0 0 1rem 0;
  font-size: 0.95rem;
}

.welcome-message ul {
  text-align: left;
  max-width: 400px;
  margin: 0 auto;
  padding-left: 1.5rem;
}

.welcome-message li {
  margin: 0.5rem 0;
  font-size: 0.9rem;
  color: #555;
}

.message {
  display: flex;
  gap: 0.75rem;
  animation: messageSlideIn 0.3s ease;
}

.message-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
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
  padding: 0.75rem 1rem;
  border-radius: 12px;
  font-size: 0.95rem;
  line-height: 1.5;
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
  gap: 0.5rem;
  align-items: center;
  font-size: 0.85rem;
}

.operations-label {
  color: #666;
  font-weight: 500;
}

.operation-tag {
  background-color: #9C27B0;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
}

.message-time {
  font-size: 0.75rem;
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
  padding: 0.75rem 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
  border-left: 3px solid #f44336;
}

.chat-input-form {
  display: flex;
  gap: 1rem;
}

.chat-input {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.2s ease;
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
  padding: 0.75rem 2rem;
  background-color: #9C27B0;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
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

.connection-warning {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background-color: #fff3e0;
  border-left: 3px solid #ff9800;
  border-radius: 6px;
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-size: 0.9rem;
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
    width: 35%;
    min-width: 280px;
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
  
  .header-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}
</style>
